import time

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.audit import create_trace_id, write_audit_log
from app.config import settings
from app.database import Base, engine, SessionLocal
from app.dependencies import get_current_agent, get_db, require_permission
from app.memory_service import save_memory, search_memory
from app.models import Agent, AgentPermission, Tool
from app.rate_limit import check_rate_limit
from app.schemas import (
    AgentCreate,
    AgentCreateResponse,
    MemoryCreate,
    MemorySearch,
    ToolRunRequest,
)
from app.security import create_api_key, hash_api_key
from app.tool_registry import run_registered_tool, seed_tools


Base.metadata.create_all(bind=engine)

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
        "message": "Agent infrastructure API for memory, tools, identity, and MCP.",
    }


@app.get("/.well-known/agent.json")
def agent_manifest():
    return {
        "name": "AgentMind",
        "description": "Memory and tool infrastructure for AI agents.",
        "version": "1.0.0",
        "base_url": settings.PUBLIC_BASE_URL,
        "auth": {
            "type": "api_key",
            "header": "X-Agent-Key",
        },
        "capabilities": [
            "agent.identity",
            "memory.write",
            "memory.search",
            "tools.discover",
            "tools.run",
            "audit.logs",
            "rate.limits",
            "mcp.compatible",
        ],
        "endpoints": {
            "register_agent": "/v1/agents/register",
            "current_agent": "/v1/agents/me",
            "save_memory": "/v1/memories",
            "search_memory": "/v1/memories/search",
            "list_tools": "/v1/tools",
            "run_tool": "/v1/tools/{tool_name}/run",
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
        "is_active": agent.is_active,
        "rate_limit_per_minute": agent.rate_limit_per_minute,
        "permissions": [p.permission for p in agent.permissions],
    }


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

    tools = db.query(Tool).filter(Tool.is_active == True).all()

    return {
        "success": True,
        "result": [
            {
                "name": tool.name,
                "description": tool.description,
                "permission_required": tool.permission_required,
            }
            for tool in tools
        ],
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