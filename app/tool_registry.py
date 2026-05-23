import requests
from sqlalchemy.orm import Session

from app.models import Tool
from app.tools import (
    calculator_tool,
    echo_tool,
    memory_search_tool,
    quadratic_solver_tool,
    url_reader_tool,
    rss_reader_tool,
)


TOOL_FUNCTIONS = {
    "calculator": calculator_tool,
    "memory_search": memory_search_tool,
    "echo": echo_tool,
    "quadratic_solver": quadratic_solver_tool,
    "url_reader": url_reader_tool,
    "rss_reader": rss_reader_tool,
}


TOOL_SPECS = {
    "calculator": {
        "name": "calculator",
        "description": "Performs pure numeric arithmetic only.",
        "permission_required": "tools:calculator:run",
        "input_schema": {
            "type": "object",
            "required": ["expression"],
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A numeric arithmetic expression.",
                    "example": "45 * 12",
                }
            },
        },
        "validation_rules": [
            "Input must be numeric arithmetic only.",
            "Variables like x, y, or z are not allowed.",
            "Equations with '=' are not allowed.",
            "Natural language text is not allowed.",
        ],
        "output_schema": {
            "type": "object",
            "properties": {
                "expression": "string",
                "answer": "string",
            },
        },
        "example_request": {"input": {"expression": "45 * 12"}},
        "example_response": {"expression": "45 * 12", "answer": "540"},
    },
    "quadratic_solver": {
        "name": "quadratic_solver",
        "description": "Solves regular quadratic equations in x.",
        "permission_required": "tools:quadratic_solver:run",
        "input_schema": {
            "type": "object",
            "required": ["equation"],
            "properties": {
                "equation": {
                    "type": "string",
                    "description": "A clean quadratic equation in x.",
                    "example": "x^2 - 5x + 6 = 0",
                }
            },
        },
        "validation_rules": [
            "Equation must contain variable x.",
            "Equation must contain exactly one '=' sign.",
            "Equation must be degree 2.",
        ],
        "output_schema": {
            "type": "object",
            "properties": {
                "original_equation": "string",
                "normalized_equation": "string",
                "solutions": ["string"],
            },
        },
        "example_request": {"input": {"equation": "x^2 - 5x + 6 = 0"}},
        "example_response": {
            "original_equation": "x^2 - 5x + 6 = 0",
            "normalized_equation": "(x**2 - 5x + 6) - (0)",
            "solutions": ["2", "3"],
        },
    },
    "memory_search": {
        "name": "memory_search",
        "description": "Searches stored memories for the current agent.",
        "permission_required": "memory:read",
        "input_schema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
        "validation_rules": [
            "Query must not be empty.",
            "Agent ID is injected by AgentMind.",
        ],
        "output_schema": {
            "type": "object",
            "properties": {"memories": ["string"]},
        },
        "example_request": {
            "input": {
                "query": "answer style",
                "limit": 5,
            }
        },
        "example_response": {
            "memories": ["This agent prefers short technical answers."]
        },
    },
    "echo": {
        "name": "echo",
        "description": "Returns the same input. Useful for testing agents.",
        "permission_required": "tools:echo:run",
        "input_schema": {
            "type": "object",
            "required": ["message"],
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Message to echo back.",
                }
            },
        },
        "validation_rules": ["Input should include a message field."],
        "output_schema": {
            "type": "object",
            "properties": {"echo": "object"},
        },
        "example_request": {"input": {"message": "hello agent world"}},
        "example_response": {"echo": {"message": "hello agent world"}},
    },
    "url_reader": {
        "name": "url_reader",
        "description": "Fetches a webpage and extracts readable text content.",
        "permission_required": "tools:url_reader:run",
        "input_schema": {
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The webpage URL to read.",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum characters of text to return.",
                },
            },
        },
        "validation_rules": [
            "URL must start with http:// or https://.",
            "URL must contain a valid domain.",
        ],
        "output_schema": {
            "type": "object",
            "properties": {
                "url": "string",
                "title": "string | null",
                "content": "string",
                "truncated": "boolean",
                "content_length": "integer",
            },
        },
        "example_request": {
            "input": {
                "url": "https://example.com",
                "max_chars": 4000,
            }
        },
        "example_response": {
            "url": "https://example.com",
            "title": "Example Domain",
            "content": "Example Domain...",
            "truncated": False,
            "content_length": 120,
        },
    },
    "rss_reader": {
        "name": "rss_reader",
        "description": "Discovers and reads RSS/Atom feeds from websites that support feeds.",
        "permission_required": "tools:rss_reader:run",
        "input_schema": {
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
        "validation_rules": [
            "URL must start with http:// or https://.",
            "Tool tries common feed paths automatically.",
        ],
        "output_schema": {
            "type": "object",
            "properties": {
                "source_url": "string",
                "feed_url": "string",
                "feed_title": "string",
                "entries": ["object"],
            },
        },
        "example_request": {
            "input": {
                "url": "https://example.com",
                "limit": 5,
            }
        },
        "example_response": {
            "source_url": "https://example.com",
            "feed_url": "https://example.com/feed/",
            "feed_title": "Example Feed",
            "entries": [],
        },
    },
    "delegate_task": {
        "name": "delegate_task",
        "description": "Delegates a task to another registered agent.",
        "permission_required": "agents:delegate",
        "input_schema": {
            "type": "object",
            "required": ["target_agent_id", "task", "reason"],
            "properties": {
                "target_agent_id": {"type": "integer"},
                "task": {"type": "string"},
                "reason": {"type": "string"},
            },
        },
        "validation_rules": [
            "Caller must have agents:delegate permission.",
            "Target agent must exist and be active.",
            "Task must not be empty.",
        ],
        "output_schema": {
            "type": "object",
            "properties": {
                "target_agent_id": "integer",
                "target_agent_name": "string",
                "response": "string",
                "tool_calls": ["object"],
            },
        },
        "example_request": {
            "input": {
                "target_agent_id": 2,
                "task": "What is 45 * 12?",
                "reason": "Math Agent is better suited.",
            }
        },
        "example_response": {
            "target_agent_id": 2,
            "target_agent_name": "Math Agent",
            "response": "45 * 12 = 540.",
            "tool_calls": [],
        },
    },
}


def seed_tools(db: Session):
    for spec in TOOL_SPECS.values():
        existing_tool = (
            db.query(Tool)
            .filter(Tool.name == spec["name"])
            .first()
        )

        if existing_tool:
            existing_tool.description = spec["description"]
            existing_tool.permission_required = spec["permission_required"]
            existing_tool.input_schema = spec["input_schema"]
            existing_tool.validation_rules = spec.get("validation_rules")
            existing_tool.output_schema = spec.get("output_schema")
            existing_tool.example_request = spec.get("example_request")
            existing_tool.example_response = spec.get("example_response")
            existing_tool.is_active = True
            continue

        db.add(
            Tool(
                name=spec["name"],
                description=spec["description"],
                permission_required=spec["permission_required"],
                input_schema=spec["input_schema"],
                validation_rules=spec.get("validation_rules"),
                output_schema=spec.get("output_schema"),
                example_request=spec.get("example_request"),
                example_response=spec.get("example_response"),
                is_active=True,
                is_webhook=False,
            )
        )

    db.commit()


def get_tool_spec(tool_name: str):
    return TOOL_SPECS.get(tool_name)


def list_tool_specs():
    return list(TOOL_SPECS.values())


def run_webhook_tool(tool: Tool, input_data: dict):
    if not tool.webhook_url:
        raise ValueError(f"Webhook URL is missing for tool '{tool.name}'.")

    method = (tool.webhook_method or "POST").upper()
    headers = tool.webhook_headers or {}
    timeout = tool.webhook_timeout_seconds or 30

    if method == "POST":
        response = requests.post(
            tool.webhook_url,
            json=input_data,
            headers=headers,
            timeout=timeout,
        )
    elif method == "GET":
        response = requests.get(
            tool.webhook_url,
            params=input_data,
            headers=headers,
            timeout=timeout,
        )
    else:
        raise ValueError(f"Unsupported webhook method: {method}")

    response.raise_for_status()

    try:
        return response.json()
    except Exception:
        return {"raw_response": response.text}


def run_registered_tool(
    db: Session,
    tool_name: str,
    input_data: dict,
):
    tool = (
        db.query(Tool)
        .filter(
            Tool.name == tool_name,
            Tool.is_active == True,
        )
        .first()
    )

    if not tool:
        raise ValueError(f"Tool '{tool_name}' not found.")

    if tool.is_webhook:
        return run_webhook_tool(
            tool=tool,
            input_data=input_data,
        )

    tool_function = TOOL_FUNCTIONS.get(tool_name)

    if not tool_function:
        raise ValueError(f"Internal tool '{tool_name}' is not registered.")

    return tool_function(input_data)