import json
from typing import Any

from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.memory_service import save_memory, search_memory
from app.models import Agent, Tool
from app.tool_registry import run_registered_tool


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
                            "or expressions containing x or '='. "
                            "Valid examples: 45 * 12, 6/7 + 5, (20 + 5) / 2."
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
                                    "description": "Search query for memory retrieval.",
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

        elif tool.name == "echo":
            runtime_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "echo",
                        "description": "Echoes back the provided input for testing.",
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

        elif tool.name == "quadratic_solver":
            runtime_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "quadratic_solver",
                        "description": (
                            "Use this only for regular quadratic equations in x. "
                            "The equation must look like ax^2 + bx + c = 0. "
                            "Do not use this for ambiguous natural language, malformed equations, "
                            "or non-quadratic expressions."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "equation": {
                                    "type": "string",
                                    "description": (
                                        "A clean quadratic equation in x. "
                                        "Valid example: x^2 - 5x + 6 = 0. "
                                        "Invalid example: x raise to double power of 2."
                                    ),
                                }
                            },
                            "required": ["equation"],
                            "additionalProperties": False,
                        },
                    },
                }
            )

    return runtime_tools


def run_agent_runtime(
    db: Session,
    agent: Agent,
    task: str,
    memory_search_limit: int = 5,
    save_result_to_memory: bool = False,
) -> dict[str, Any]:
    client = get_openai_client()

    memories = search_memory(
        agent_id=agent.id,
        query=task,
        limit=memory_search_limit,
    )

    tools = build_runtime_tools(db=db, agent=agent)

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
- Do not silently rewrite malformed math input into valid input.
- If input is malformed or ambiguous, allow the tool validator to reject it.
- If a math expression contains variables or '=', do not use calculator.
"""

    memory_block = "\n".join([f"- {memory}" for memory in memories]) or "No relevant memories found."

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

Relevant memories already retrieved:
{memory_block}
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
                        }
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
                                "Explain the validation failure clearly. "
                                "Do not solve malformed input. "
                                "Suggest one corrected input format."
                            ),
                        }
                    ),
                }
            )

    messages.append(
        {
            "role": "system",
            "content": """
When responding after tool execution:

- If a tool succeeded, summarize the result clearly.
- If a tool failed validation, clearly explain the validation rule that failed.
- Do not try to solve malformed input.
- Do not say "I will proceed" unless another tool was actually called.
- Give one corrected example format when helpful.
- Keep the response useful for another AI agent or developer system.

For calculator:
- It only accepts pure numeric arithmetic.
- It rejects variables, equations, words, and '='.

For quadratic_solver:
- It only accepts regular quadratic equations in x.
- Required format: ax^2 + bx + c = 0.
- It rejects ambiguous wording like "raise to double power".
- It should not silently correct malformed equations.
"""
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