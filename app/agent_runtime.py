import json
import re
from typing import Any

from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.memory_service import save_memory, search_memory
from app.message_service import create_agent_message
from app.models import Agent, AgentWorkflow, Tool
from app.tool_registry import run_registered_tool
from app.workflow_service import (
    get_workflow_context,
    update_workflow_context,
)


def task_contains_url(task: str) -> bool:
    return bool(re.search(r"https?://[^\s]+", task))


def get_openai_client(
    llm_config: dict[str, Any],
) -> tuple[OpenAI, str]:
    provider = llm_config.get("provider", "openai")
    api_key = llm_config.get("api_key")
    model = llm_config.get("model", settings.OPENAI_MODEL)

    if provider != "openai":
        raise ValueError(
            f"Unsupported LLM provider for now: {provider}"
        )

    if not api_key:
        raise ValueError(
            "Developer OpenAI API key is required in llm_config.api_key."
        )

    return OpenAI(api_key=api_key), model


def get_workflow(
    db: Session,
    workflow_id: int | None,
) -> AgentWorkflow | None:
    if not workflow_id:
        return None

    return (
        db.query(AgentWorkflow)
        .filter(AgentWorkflow.id == workflow_id)
        .first()
    )


def set_workflow_status(
    db: Session,
    workflow_id: int | None,
    status: str,
) -> None:
    workflow = get_workflow(db, workflow_id)

    if not workflow:
        return

    workflow.status = status
    db.commit()


def add_workflow_event(
    db: Session,
    workflow_id: int | None,
    event: dict[str, Any],
    completed: bool = False,
) -> None:
    workflow = get_workflow(db, workflow_id)

    if not workflow:
        return

    context_data = get_workflow_context(workflow)

    context_data.setdefault("messages", []).append(event)

    if completed:
        context_data.setdefault("completed_steps", []).append(event)

    update_workflow_context(
        db=db,
        workflow=workflow,
        context_data=context_data,
    )


def build_runtime_tools(db: Session, agent: Agent) -> list[dict[str, Any]]:
    agent_permissions = [
        permission.permission
        for permission in agent.permissions
    ]

    runtime_tools = []

    if "agents:delegate" in agent_permissions:
        runtime_tools.append(
            {
                "type": "function",
                "function": {
                    "name": "delegate_task",
                    "description": (
                        "Delegate a task to another registered specialist agent "
                        "when that agent is better suited for the work."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_agent_id": {
                                "type": "integer",
                                "description": "The ID of the agent to delegate the task to.",
                            },
                            "task": {
                                "type": "string",
                                "description": "The exact task to assign to the target agent.",
                            },
                            "reason": {
                                "type": "string",
                                "description": "Why this target agent is best suited for the task.",
                            },
                        },
                        "required": [
                            "target_agent_id",
                            "task",
                            "reason",
                        ],
                    },
                },
            }
        )

    db_tools = (
        db.query(Tool)
        .filter(Tool.is_active == True)
        .all()
    )

    for tool in db_tools:
        if tool.permission_required not in agent_permissions:
            continue

        runtime_tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                },
            }
        )

    return runtime_tools


def get_agent_directory(
    db: Session,
    current_agent: Agent,
) -> list[dict[str, Any]]:
    agents = (
        db.query(Agent)
        .filter(Agent.is_active == True)
        .all()
    )

    directory = []

    for agent in agents:
        if agent.id == current_agent.id:
            continue

        try:
            capabilities = json.loads(agent.capabilities or "[]")
        except Exception:
            capabilities = []

        directory.append(
            {
                "id": agent.id,
                "name": agent.name,
                "purpose": agent.purpose,
                "capabilities": capabilities,
            }
        )

    return directory


def run_delegate_task(
    db: Session,
    caller_agent: Agent,
    target_agent_id: int,
    task: str,
    reason: str,
    workflow_id: int | None = None,
    delegation_depth: int = 0,
    max_delegation_depth: int = 3,
    llm_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    caller_permissions = [
        permission.permission
        for permission in caller_agent.permissions
    ]

    if "agents:delegate" not in caller_permissions:
        raise ValueError(
            "Caller agent does not have agents:delegate permission."
        )

    if delegation_depth >= max_delegation_depth:
        raise ValueError("Maximum delegation depth reached.")

    target_agent = (
        db.query(Agent)
        .filter(
            Agent.id == target_agent_id,
            Agent.is_active == True,
        )
        .first()
    )

    if not target_agent:
        raise ValueError("Target agent not found or inactive.")

    if workflow_id:
        create_agent_message(
            db=db,
            sender_agent_id=caller_agent.id,
            receiver_agent_id=target_agent.id,
            content=task,
            trace_id=f"workflow_{workflow_id}",
            message_type="task",
            task_id=None,
        )

    result = run_agent_runtime(
        db=db,
        agent=target_agent,
        task=task,
        memory_search_limit=5,
        save_result_to_memory=False,
        workflow_id=workflow_id,
        delegation_depth=delegation_depth + 1,
        max_delegation_depth=max_delegation_depth,
        llm_config=llm_config,
    )

    if workflow_id:
        create_agent_message(
            db=db,
            sender_agent_id=target_agent.id,
            receiver_agent_id=caller_agent.id,
            content=result["response"],
            trace_id=f"workflow_{workflow_id}",
            message_type="result",
            task_id=None,
        )

        add_workflow_event(
            db=db,
            workflow_id=workflow_id,
            event={
                "from": caller_agent.name,
                "to": target_agent.name,
                "action": "delegate_task",
                "reason": reason,
                "response_summary": str(result["response"])[:300],
            },
            completed=True,
        )

    return {
        "target_agent_id": target_agent.id,
        "target_agent_name": target_agent.name,
        "delegation_reason": reason,
        "task": task,
        "response": result["response"],
        "memories_used": result["memories_used"],
        "tool_calls": result["tool_calls"],
        "workflow_id": workflow_id,
    }


def run_agent_runtime(
    db: Session,
    agent: Agent,
    task: str,
    memory_search_limit: int = 5,
    save_result_to_memory: bool = False,
    workflow_id: int | None = None,
    delegation_depth: int = 0,
    max_delegation_depth: int = 3,
    llm_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if llm_config is None:
        raise ValueError("llm_config is required.")

    client, model = get_openai_client(llm_config)

    set_workflow_status(
        db=db,
        workflow_id=workflow_id,
        status="running",
    )

    memories = search_memory(
        agent_id=agent.id,
        query=task,
        limit=memory_search_limit,
    )

    tools = build_runtime_tools(
        db=db,
        agent=agent,
    )

    agent_directory = get_agent_directory(
        db=db,
        current_agent=agent,
    )

    workflow_context = {}

    workflow = get_workflow(
        db=db,
        workflow_id=workflow_id,
    )

    if workflow:
        workflow_context = get_workflow_context(workflow)

    memory_block = (
        "\n".join([f"- {memory}" for memory in memories])
        or "No relevant memories found."
    )

    system_prompt = f"""
You are AgentMind Runtime.

You are an autonomous multi-agent reasoning runtime.

Current agent:
- agent_id: {agent.id}
- name: {agent.name}
- purpose: {agent.purpose}

Autonomous execution rules:
- You may call multiple tools across multiple rounds.
- After each tool result, inspect the result carefully.
- Decide the next best action dynamically.
- Continue reasoning until the task is complete.
- If another agent is more specialized, delegate to them.
- You may delegate multiple times when useful.
- If the task already contains enough structured data, answer from the task data.
- Do not use memory_search just because it is available.
- If memory_search returns no useful result once, do not call memory_search again for the same task.
- Never spend all tool rounds searching empty memory.
- When enough information is gathered, stop calling tools and answer.
- Never pretend a tool succeeded if it failed.
- Agents should only call tools that match their role, capabilities, and permissions.
- Coordinator agents should prefer delegation when another agent is more specialized.
- Never invent tool results.
- Do not delegate to yourself.
- Do not infinitely loop tools.
- Current delegation depth: {delegation_depth}
- Maximum delegation depth: {max_delegation_depth}

Tool behavior:
- Use calculator for pure arithmetic only.
- Use quadratic_solver for quadratic equations.
- If task contains a URL and asks to read/research/summarize, use url_reader first.
- If url_reader fails and rss_reader exists, use rss_reader.
- Prefer rss_reader for latest news/posts/blogs.
"""

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": f"""
Task:
{task}

Relevant memories:
{memory_block}

Available agents:
{json.dumps(agent_directory, indent=2)}

Workflow ID:
{workflow_id}

Workflow context:
{json.dumps(workflow_context, indent=2)}
""",
        },
    ]

    tool_choice = "auto"

    if task_contains_url(task):
        tool_names = [
            tool["function"]["name"]
            for tool in tools
            if tool.get("type") == "function"
        ]

        if "url_reader" in tool_names:
            tool_choice = {
                "type": "function",
                "function": {
                    "name": "url_reader",
                },
            }

    tool_calls_log = []
    memory_search_count = 0
    max_tool_rounds = 5

    try:
        for round_number in range(max_tool_rounds):
            request_kwargs = {
                "model": model,
                "messages": messages,
            }

            if tools:
                request_kwargs["tools"] = tools
                request_kwargs["tool_choice"] = (
                    tool_choice if round_number == 0 else "auto"
                )

            response = client.chat.completions.create(**request_kwargs)
            assistant_message = response.choices[0].message

            if not assistant_message.tool_calls:
                final_text = assistant_message.content or ""

                if save_result_to_memory and final_text:
                    save_memory(
                        db=db,
                        agent_id=agent.id,
                        content=f"Task: {task}\nResult: {final_text}",
                    )

                set_workflow_status(
                    db=db,
                    workflow_id=workflow_id,
                    status="completed",
                )

                return {
                    "response": final_text,
                    "memories_used": memories,
                    "tool_calls": tool_calls_log,
                }

            messages.append(assistant_message)

            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name

                try:
                    tool_args = json.loads(
                        tool_call.function.arguments or "{}"
                    )
                except Exception:
                    tool_args = {}

                if tool_name == "memory_search":
                    memory_search_count += 1

                    if memory_search_count > 1:
                        tool_error = (
                            "memory_search was already tried. "
                            "Use the structured task data instead."
                        )

                        tool_calls_log.append(
                            {
                                "round": round_number + 1,
                                "tool_name": tool_name,
                                "arguments": tool_args,
                                "status": "failed",
                                "result": None,
                                "error": tool_error,
                            }
                        )

                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps(
                                    {
                                        "status": "failed",
                                        "error": tool_error,
                                    }
                                ),
                            }
                        )

                        continue

                    tool_args["agent_id"] = agent.id

                if tool_name == "quadratic_solver":
                    tool_args["original_task"] = task

                try:
                    if tool_name == "delegate_task":
                        tool_result = run_delegate_task(
                            db=db,
                            caller_agent=agent,
                            target_agent_id=tool_args["target_agent_id"],
                            task=tool_args["task"],
                            reason=tool_args.get(
                                "reason",
                                "Delegated by autonomous AgentMind runtime.",
                            ),
                            workflow_id=workflow_id,
                            delegation_depth=delegation_depth,
                            max_delegation_depth=max_delegation_depth,
                            llm_config=llm_config
                        )
                    else:
                        tool_result = run_registered_tool(
                            db=db,
                            tool_name=tool_name,
                            input_data=tool_args,
                        )

                    tool_calls_log.append(
                        {
                            "round": round_number + 1,
                            "tool_name": tool_name,
                            "arguments": tool_args,
                            "status": "success",
                            "result": tool_result,
                            "error": None,
                        }
                    )

                    add_workflow_event(
                        db=db,
                        workflow_id=workflow_id,
                        event={
                            "round": round_number + 1,
                            "agent": agent.name,
                            "action": tool_name,
                            "status": "success",
                            "result_summary": str(tool_result)[:300],
                        },
                        completed=True,
                    )

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(
                                {
                                    "status": "success",
                                    "result": tool_result,
                                },
                                default=str,
                            ),
                        }
                    )

                except Exception as error:
                    error_message = str(error)

                    tool_calls_log.append(
                        {
                            "round": round_number + 1,
                            "tool_name": tool_name,
                            "arguments": tool_args,
                            "status": "failed",
                            "result": None,
                            "error": error_message,
                        }
                    )

                    add_workflow_event(
                        db=db,
                        workflow_id=workflow_id,
                        event={
                            "round": round_number + 1,
                            "agent": agent.name,
                            "action": tool_name,
                            "status": "failed",
                            "error": error_message,
                        },
                        completed=False,
                    )

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(
                                {
                                    "status": "failed",
                                    "error": error_message,
                                    "retry_hint": (
                                        "Try another valid tool or explain failure."
                                    ),
                                },
                                default=str,
                            ),
                        }
                    )

        set_workflow_status(
            db=db,
            workflow_id=workflow_id,
            status="failed",
        )

        return {
            "response": (
                "Autonomous execution stopped because the maximum "
                "tool rounds were reached."
            ),
            "memories_used": memories,
            "tool_calls": tool_calls_log,
        }

    except Exception:
        set_workflow_status(
            db=db,
            workflow_id=workflow_id,
            status="failed",
        )
        raise