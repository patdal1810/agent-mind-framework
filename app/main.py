import json
import time

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.agent_runtime import run_agent_runtime
from app.audit import create_trace_id, write_audit_log
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.dependencies import get_current_agent, get_db, require_permission
from app.memory_service import save_memory, search_memory
from app.models import Agent, AgentPermission, AgentTask, Tool
from app.rate_limit import check_rate_limit
from app.schemas import (
    AgentChatRequest,
    AgentCreate,
    AgentCreateResponse,
    AgentDelegateRequest,
    MemoryCreate,
    MemorySearch,
    ToolRunRequest,
)
from app.security import create_api_key, hash_api_key
from app.task_service import (
    create_task_record,
    mark_task_completed,
    mark_task_failed,
    mark_task_running,
    serialize_task,
)
from app.tool_registry import (
    get_tool_spec,
    run_registered_tool,
    seed_tools,
)



app = FastAPI(title=settings.APP_NAME)


@app.on_event("startup")
def startup():
    db = SessionLocal()
    try:
        seed_tools(db)
    finally:
        db.close()


@app.get("/")
def root():
    return {
        "name": settings.APP_NAME,
        "message": "Agent infrastructure API for memory, tools, identity, MCP, delegation, and task history.",
    }


@app.get("/.well-known/agent.json")
def agent_manifest():
    return {
        "name": "AgentMind",
        "description": "Memory, tool, runtime, and coordination infrastructure for AI agents.",
        "version": "1.0.0",
        "base_url": settings.PUBLIC_BASE_URL,
        "auth": {
            "type": "api_key",
            "header": "X-Agent-Key",
        },
        "capabilities": [
            "agent.identity",
            "agent.discovery",
            "agent.delegation",
            "agent.runtime",
            "memory.write",
            "memory.search",
            "tools.discover",
            "tools.run",
            "tool_schema_registry",
            "task.history",
            "audit.logs",
            "rate.limits",
            "mcp.compatible",
        ],
        "endpoints": {
            "register_agent": "/v1/agents/register",
            "current_agent": "/v1/agents/me",
            "discover_agents": "/v1/agents/discover",
            "delegate_agent": "/v1/agents/delegate",
            "save_memory": "/v1/memories",
            "search_memory": "/v1/memories/search",
            "list_tools": "/v1/tools",
            "get_tool_details": "/v1/tools/{tool_name}",
            "run_tool": "/v1/tools/{tool_name}/run",
            "agent_chat": "/v1/agent/chat",
            "list_tasks": "/v1/tasks",
            "get_task": "/v1/tasks/{task_id}",
        },
    }


@app.post("/v1/agents/register", response_model=AgentCreateResponse)
def register_agent(
    request: AgentCreate,
    db: Session = Depends(get_db),
):
    if request.invite_code != settings.REGISTRATION_INVITE_CODE:
        raise HTTPException(
            status_code=403,
            detail="Invalid invite code",
        )

    api_key = create_api_key()

    agent = Agent(
        name=request.name,
        purpose=request.purpose,
        capabilities=json.dumps(request.capabilities),
        api_key_hash=hash_api_key(api_key),
    )

    db.add(agent)
    db.commit()
    db.refresh(agent)

    permissions = request.permissions or [
        "memory:read",
        "memory:write",
        "tools:calculator:run",
        "tools:echo:run",
    ]

    for permission in permissions:
        db.add(
            AgentPermission(
                agent_id=agent.id,
                permission=permission,
            )
        )

    db.commit()

    return {
        "agent_id": agent.id,
        "api_key": api_key,
        "message": "Store this API key safely. It will not be shown again.",
    }


@app.get("/v1/agents/me")
def get_me(agent: Agent = Depends(get_current_agent)):
    return {
        "id": agent.id,
        "name": agent.name,
        "purpose": agent.purpose,
        "capabilities": json.loads(agent.capabilities or "[]"),
        "is_active": agent.is_active,
        "rate_limit_per_minute": agent.rate_limit_per_minute,
        "permissions": [p.permission for p in agent.permissions],
    }


@app.get("/v1/agents/discover")
def discover_agents(
    capability: str | None = None,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    check_rate_limit(agent.id, agent.rate_limit_per_minute)

    agents = db.query(Agent).filter(Agent.is_active == True).all()

    result = []

    for available_agent in agents:
        capabilities = json.loads(available_agent.capabilities or "[]")

        if capability and capability not in capabilities:
            continue

        result.append(
            {
                "id": available_agent.id,
                "name": available_agent.name,
                "purpose": available_agent.purpose,
                "capabilities": capabilities,
            }
        )

    return {
        "success": True,
        "result": result,
    }


@app.post("/v1/agents/delegate")
def delegate_to_agent(
    request: AgentDelegateRequest,
    db: Session = Depends(get_db),
    caller_agent: Agent = Depends(require_permission("agents:delegate")),
):
    start = time.time()
    trace_id = create_trace_id()

    check_rate_limit(
        caller_agent.id,
        caller_agent.rate_limit_per_minute,
    )

    target_agent = (
        db.query(Agent)
        .filter(
            Agent.id == request.target_agent_id,
            Agent.is_active == True,
        )
        .first()
    )

    if not target_agent:
        raise HTTPException(
            status_code=404,
            detail="Target agent not found",
        )

    task_record = create_task_record(
        db=db,
        task=request.task,
        assigned_agent_id=target_agent.id,
        caller_agent_id=caller_agent.id,
        trace_id=trace_id,
    )

    mark_task_running(db=db, task_record=task_record)

    try:
        result = run_agent_runtime(
            db=db,
            agent=target_agent,
            task=request.task,
            memory_search_limit=request.memory_search_limit,
            save_result_to_memory=request.save_result_to_memory,
        )

        mark_task_completed(
            db=db,
            task_record=task_record,
            response=result["response"],
            tool_calls=result["tool_calls"],
        )

        output = {
            "task_id": task_record.id,
            "caller_agent_id": caller_agent.id,
            "target_agent_id": target_agent.id,
            "target_agent_name": target_agent.name,
            "task": request.task,
            "response": result["response"],
            "memories_used": result["memories_used"],
            "tool_calls": result["tool_calls"],
        }

        write_audit_log(
            db=db,
            agent_id=caller_agent.id,
            action="agent.delegate",
            input_data=request.model_dump(),
            output_data=output,
            status="success",
            trace_id=trace_id,
        )

        return {
            "success": True,
            "result": output,
            "error": None,
            "trace_id": trace_id,
            "latency_ms": int((time.time() - start) * 1000),
        }

    except Exception as error:
        mark_task_failed(
            db=db,
            task_record=task_record,
            error=str(error),
        )

        write_audit_log(
            db=db,
            agent_id=caller_agent.id,
            action="agent.delegate",
            input_data=request.model_dump(),
            output_data={"error": str(error)},
            status="error",
            trace_id=trace_id,
        )

        raise HTTPException(status_code=500, detail=str(error))


@app.post("/v1/memories")
def create_memory(
    request: MemoryCreate,
    db: Session = Depends(get_db),
    agent: Agent = Depends(require_permission("memory:write")),
):
    start = time.time()
    trace_id = create_trace_id()

    check_rate_limit(agent.id, agent.rate_limit_per_minute)

    try:
        memory = save_memory(
            db=db,
            agent_id=agent.id,
            content=request.content,
        )

        result = {
            "memory_id": memory.id,
            "content": memory.content,
        }

        write_audit_log(
            db=db,
            agent_id=agent.id,
            action="memory.write",
            input_data=request.model_dump(),
            output_data=result,
            status="success",
            trace_id=trace_id,
        )

        return {
            "success": True,
            "result": result,
            "error": None,
            "trace_id": trace_id,
            "latency_ms": int((time.time() - start) * 1000),
        }

    except Exception as error:
        write_audit_log(
            db=db,
            agent_id=agent.id,
            action="memory.write",
            input_data=request.model_dump(),
            output_data={"error": str(error)},
            status="error",
            trace_id=trace_id,
        )

        raise HTTPException(status_code=500, detail=str(error))


@app.post("/v1/memories/search")
def search_memories(
    request: MemorySearch,
    agent: Agent = Depends(require_permission("memory:read")),
):
    start = time.time()
    trace_id = create_trace_id()

    check_rate_limit(agent.id, agent.rate_limit_per_minute)

    memories = search_memory(
        agent_id=agent.id,
        query=request.query,
        limit=request.limit,
    )

    return {
        "success": True,
        "result": {
            "memories": memories,
        },
        "error": None,
        "trace_id": trace_id,
        "latency_ms": int((time.time() - start) * 1000),
    }


@app.get("/v1/tools")
def list_tools(
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    check_rate_limit(agent.id, agent.rate_limit_per_minute)

    db_tools = db.query(Tool).filter(Tool.is_active == True).all()
    agent_permissions = [p.permission for p in agent.permissions]

    result = []

    for tool in db_tools:
        spec = get_tool_spec(tool.name)

        if not spec:
            continue

        result.append(
            {
                **spec,
                "agent_has_permission": tool.permission_required in agent_permissions,
            }
        )

    return {
        "success": True,
        "result": result,
    }


@app.get("/v1/tools/{tool_name}")
def get_tool_details(
    tool_name: str,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    check_rate_limit(agent.id, agent.rate_limit_per_minute)

    tool = (
        db.query(Tool)
        .filter(
            Tool.name == tool_name,
            Tool.is_active == True,
        )
        .first()
    )

    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    spec = get_tool_spec(tool.name)

    if not spec:
        raise HTTPException(status_code=404, detail="Tool spec not found")

    agent_permissions = [p.permission for p in agent.permissions]

    return {
        "success": True,
        "result": {
            **spec,
            "agent_has_permission": tool.permission_required in agent_permissions,
        },
    }


@app.post("/v1/tools/{tool_name}/run")
def run_tool(
    tool_name: str,
    request: ToolRunRequest,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    start = time.time()
    trace_id = create_trace_id()

    check_rate_limit(agent.id, agent.rate_limit_per_minute)

    tool = (
        db.query(Tool)
        .filter(
            Tool.name == tool_name,
            Tool.is_active == True,
        )
        .first()
    )

    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    permissions = [p.permission for p in agent.permissions]

    if tool.permission_required not in permissions:
        raise HTTPException(
            status_code=403,
            detail=f"Missing permission: {tool.permission_required}",
        )

    try:
        input_data = dict(request.input)

        if tool_name == "memory_search":
            input_data["agent_id"] = agent.id

        result = run_registered_tool(
            tool_name=tool_name,
            input_data=input_data,
        )

        write_audit_log(
            db=db,
            agent_id=agent.id,
            action=f"tool.run.{tool_name}",
            input_data=input_data,
            output_data=result,
            status="success",
            trace_id=trace_id,
        )

        return {
            "success": True,
            "result": result,
            "error": None,
            "trace_id": trace_id,
            "latency_ms": int((time.time() - start) * 1000),
        }

    except Exception as error:
        write_audit_log(
            db=db,
            agent_id=agent.id,
            action=f"tool.run.{tool_name}",
            input_data=request.input,
            output_data={"error": str(error)},
            status="error",
            trace_id=trace_id,
        )

        raise HTTPException(status_code=500, detail=str(error))


@app.post("/v1/agent/chat")
def agent_chat(
    request: AgentChatRequest,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    start = time.time()
    trace_id = create_trace_id()

    check_rate_limit(agent.id, agent.rate_limit_per_minute)

    task_record = create_task_record(
        db=db,
        task=request.task,
        assigned_agent_id=agent.id,
        caller_agent_id=None,
        trace_id=trace_id,
    )

    mark_task_running(db=db, task_record=task_record)

    try:
        result = run_agent_runtime(
            db=db,
            agent=agent,
            task=request.task,
            memory_search_limit=request.memory_search_limit,
            save_result_to_memory=request.save_result_to_memory,
        )

        mark_task_completed(
            db=db,
            task_record=task_record,
            response=result["response"],
            tool_calls=result["tool_calls"],
        )

        write_audit_log(
            db=db,
            agent_id=agent.id,
            action="agent.chat",
            input_data=request.model_dump(),
            output_data=result,
            status="success",
            trace_id=trace_id,
        )

        return {
            "success": True,
            "task_id": task_record.id,
            "task": request.task,
            "response": result["response"],
            "memories_used": result["memories_used"],
            "tool_calls": result["tool_calls"],
            "error": None,
            "trace_id": trace_id,
            "latency_ms": int((time.time() - start) * 1000),
        }

    except Exception as error:
        mark_task_failed(
            db=db,
            task_record=task_record,
            error=str(error),
        )

        write_audit_log(
            db=db,
            agent_id=agent.id,
            action="agent.chat",
            input_data=request.model_dump(),
            output_data={"error": str(error)},
            status="error",
            trace_id=trace_id,
        )

        raise HTTPException(status_code=500, detail=str(error))


@app.get("/v1/tasks")
def list_tasks(
    status: str | None = None,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    check_rate_limit(agent.id, agent.rate_limit_per_minute)

    query = db.query(AgentTask).filter(
        (AgentTask.assigned_agent_id == agent.id)
        | (AgentTask.caller_agent_id == agent.id)
    )

    if status:
        query = query.filter(AgentTask.status == status)

    tasks = query.order_by(AgentTask.created_at.desc()).limit(50).all()

    return {
        "success": True,
        "result": [serialize_task(task) for task in tasks],
    }


@app.get("/v1/tasks/{task_id}")
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    check_rate_limit(agent.id, agent.rate_limit_per_minute)

    task = db.query(AgentTask).filter(AgentTask.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.assigned_agent_id != agent.id and task.caller_agent_id != agent.id:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this task",
        )

    return {
        "success": True,
        "result": serialize_task(task),
    }