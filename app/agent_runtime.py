import json
from typing import Any

from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.memory_service import save_memory, search_memory
from app.models import Agent, AgentWorkflow, Tool
from app.tool_registry import run_registered_tool
from app.workflow_service import (
    get_workflow_context,
    update_workflow_context,
)


def get_openai_client() -> OpenAI:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured")

    return OpenAI(api_key=settings.OPENAI_API_KEY)


def build_runtime_tools(db: Session, agent: Agent) -> list[dict[str, Any]]:
    db_tools = db.query(Tool).filter(Tool.is_active == True).all()
    agent_permissions = [p.permission for p in agent.permissions]

    runtime_tools = []

    for tool in db_tools:
        if tool.permission_required not in agent_permissions:
            continue

        if tool.name == "calculator":
            runtime_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "calculator",
                        "description": (
                            "Use this only for pure numeric arithmetic. "
                            "Do not use for equations, variables, roots, algebra, "
                            "or expressions containing x or '='."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "expression": {
                                    "type": "string",
                                    "description": "Pure numeric arithmetic expression.",
                                }
                            },
                            "required": ["expression"],
                            "additionalProperties": False,
                        },
                    },
                }
            )

        elif tool.name == "quadratic_solver":
            runtime_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "quadratic_solver",
                        "description": (
                            "Use this only for regular quadratic equations in x. "
                            "Required format: ax^2 + bx + c = 0."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "equation": {
                                    "type": "string",
                                    "description": "Example: x^2 - 5x + 6 = 0",
                                }
                            },
                            "required": ["equation"],
                            "additionalProperties": False,
                        },
                    },
                }
            )

        elif tool.name == "memory_search":
            runtime_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "memory_search",
                        "description": "Search this agent's stored memories.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Search query.",
                                },
                                "limit": {
                                    "type": "integer",
                                    "description": "Maximum memories to return.",
                                },
                            },
                            "required": ["query"],
                            "additionalProperties": False,
                        },
                    },
                }
            )

        elif tool.name == "url_reader":
            runtime_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "url_reader",
                        "description": (
                            "Fetch and read text content from a public webpage URL."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "A public URL starting with http:// or https://.",
                                },
                                "max_chars": {
                                    "type": "integer",
                                    "description": "Maximum text characters to return.",
                                },
                            },
                            "required": ["url"],
                            "additionalProperties": False,
                        },
                    },
                }
            )

        elif tool.name == "echo":
            runtime_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "echo",
                        "description": "Echoes back provided input for testing.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "message": {
                                    "type": "string",
                                    "description": "Message to echo.",
                                }
                            },
                            "required": ["message"],
                            "additionalProperties": False,
                        },
                    },
                }
            )

        elif tool.name == "delegate_task":
            runtime_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "delegate_task",
                        "description": (
                            "Delegate a task to another specialized agent when that "
                            "agent has a better capability for the task."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "target_agent_id": {
                                    "type": "integer",
                                    "description": "ID of the target agent.",
                                },
                                "task": {
                                    "type": "string",
                                    "description": "Task to delegate.",
                                },
                                "reason": {
                                    "type": "string",
                                    "description": "Why delegation is useful.",
                                },
                            },
                            "required": ["target_agent_id", "task", "reason"],
                            "additionalProperties": False,
                        },
                    },
                }
            )

    return runtime_tools


def get_agent_directory(
    db: Session,
    current_agent: Agent,
) -> list[dict[str, Any]]:
    agents = db.query(Agent).filter(Agent.is_active == True).all()

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
    max_delegation_depth: int = 2,
) -> dict[str, Any]:
    caller_permissions = [p.permission for p in caller_agent.permissions]

    if "agents:delegate" not in caller_permissions:
        raise ValueError("Caller agent does not have agents:delegate permission.")

    if delegation_depth >= max_delegation_depth:
        raise ValueError("Maximum delegation depth reached.")

    if not task or not task.strip():
        raise ValueError("Delegated task cannot be empty.")

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

    result = run_agent_runtime(
        db=db,
        agent=target_agent,
        task=task,
        memory_search_limit=5,
        save_result_to_memory=False,
        workflow_id=workflow_id,
        delegation_depth=delegation_depth + 1,
        max_delegation_depth=max_delegation_depth,
    )

    if workflow_id:
        workflow = (
            db.query(AgentWorkflow)
            .filter(AgentWorkflow.id == workflow_id)
            .first()
        )

        if workflow:
            context_data = get_workflow_context(workflow)

            context_data.setdefault("messages", []).append(
                {
                    "from": caller_agent.name,
                    "to": target_agent.name,
                    "task": task,
                    "reason": reason,
                    "response": result["response"],
                }
            )

            context_data.setdefault("completed_steps", []).append(
                {
                    "agent": target_agent.name,
                    "task": task,
                    "response": result["response"],
                }
            )

            update_workflow_context(
                db=db,
                workflow=workflow,
                context_data=context_data,
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
    max_delegation_depth: int = 2,
) -> dict[str, Any]:
    client = get_openai_client()

    memories = search_memory(
        agent_id=agent.id,
        query=task,
        limit=memory_search_limit,
    )

    tools = build_runtime_tools(db=db, agent=agent)
    agent_directory = get_agent_directory(db=db, current_agent=agent)

    workflow_context = {}

    if workflow_id:
        workflow = (
            db.query(AgentWorkflow)
            .filter(AgentWorkflow.id == workflow_id)
            .first()
        )

        if workflow:
            workflow_context = get_workflow_context(workflow)

    memory_block = (
        "\n".join([f"- {memory}" for memory in memories])
        or "No relevant memories found."
    )

    system_prompt = f"""
You are AgentMind Runtime.

You are not a human-facing chatbot.
You are a machine-facing reasoning runtime for autonomous AI agents.

Current agent:
- agent_id: {agent.id}
- name: {agent.name}
- purpose: {agent.purpose}

Rules:
- Use available tools only when useful.
- Use memories only when relevant.
- Return clear, concise, machine-usable answers.
- Do not pretend a tool was used if it was not used.
- For pure numeric arithmetic, use calculator.
- For regular quadratic equations in x, use quadratic_solver.
- If a task contains a URL and asks to read or summarize it, use url_reader.
- If another available agent has a better capability for the task, use delegate_task.
- Do not delegate to yourself.
- Do not silently rewrite malformed math input into valid input.
- If input is malformed or ambiguous, allow the tool validator to reject it.
- Current delegation depth: {delegation_depth}
- Maximum delegation depth: {max_delegation_depth}
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

Available agents for delegation:
{json.dumps(agent_directory, indent=2)}

Workflow ID:
{workflow_id}

Shared workflow context:
{json.dumps(workflow_context, indent=2)}
""",
        },
    ]

    first_response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )

    assistant_message = first_response.choices[0].message
    tool_calls_log = []

    if not assistant_message.tool_calls:
        final_text = assistant_message.content or ""

        if save_result_to_memory and final_text:
            save_memory(
                db=db,
                agent_id=agent.id,
                content=f"Task: {task}\nResult: {final_text}",
            )

        return {
            "response": final_text,
            "memories_used": memories,
            "tool_calls": tool_calls_log,
        }

    messages.append(assistant_message)

    for tool_call in assistant_message.tool_calls:
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments or "{}")

        if tool_name == "memory_search":
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
                    reason=tool_args["reason"],
                    workflow_id=workflow_id,
                    delegation_depth=delegation_depth,
                    max_delegation_depth=max_delegation_depth,
                )
            else:
                tool_result = run_registered_tool(
                    tool_name=tool_name,
                    input_data=tool_args,
                )

            tool_calls_log.append(
                {
                    "tool_name": tool_name,
                    "arguments": tool_args,
                    "status": "success",
                    "result": tool_result,
                    "error": None,
                }
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
                    "tool_name": tool_name,
                    "arguments": tool_args,
                    "status": "failed",
                    "result": None,
                    "error": error_message,
                }
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
                                "Explain the validation or runtime failure clearly. "
                                "Do not pretend the tool succeeded."
                            ),
                        },
                        default=str,
                    ),
                }
            )

    messages.append(
        {
            "role": "system",
            "content": """
When responding after tool execution:
- If a tool succeeded, summarize the result clearly.
- If a tool failed, explain the failure clearly.
- If delegation happened, explain which agent handled the task.
- If workflow context exists, mention only relevant workflow progress.
- Do not say "I will proceed" unless another tool was actually called.
- Keep the response useful for another AI agent or developer system.
""",
        }
    )

    final_response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
    )

    final_text = final_response.choices[0].message.content or ""

    if save_result_to_memory and final_text:
        save_memory(
            db=db,
            agent_id=agent.id,
            content=f"Task: {task}\nResult: {final_text}",
        )

    return {
        "response": final_text,
        "memories_used": memories,
        "tool_calls": tool_calls_log,
    }