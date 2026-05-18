from sqlalchemy.orm import Session
from app.tools import url_reader_tool

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
            "Valid example: 45 * 12.",
            "Invalid example: x^2 - 5x + 6 = 0.",
        ],
        "output_schema": {
            "type": "object",
            "properties": {
                "expression": "string",
                "answer": "string",
            },
        },
        "example_request": {
            "input": {
                "expression": "45 * 12"
            }
        },
        "example_response": {
            "expression": "45 * 12",
            "answer": "540"
        },
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
            "Only one variable is allowed: x.",
            "Ambiguous wording like 'raise to double power' is rejected.",
            "Use clear exponent format like x^2.",
            "Valid example: x^2 - 5x + 6 = 0.",
            "Invalid example: x raise to double power of 2 - 5x + 6 = 0.",
        ],
        "output_schema": {
            "type": "object",
            "properties": {
                "original_equation": "string",
                "normalized_equation": "string",
                "solutions": ["string"],
            },
        },
        "example_request": {
            "input": {
                "equation": "x^2 - 5x + 6 = 0"
            }
        },
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
                "query": {
                    "type": "string",
                    "description": "Search query for memory retrieval.",
                    "example": "answer style",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of memories to return.",
                    "example": 5,
                },
            },
        },
        "validation_rules": [
            "Query must not be empty.",
            "Agent ID is injected by AgentMind and should not be provided externally.",
            "Limit should be a small positive integer.",
        ],
        "output_schema": {
            "type": "object",
            "properties": {
                "memories": ["string"],
            },
        },
        "example_request": {
            "input": {
                "query": "answer style",
                "limit": 5,
            }
        },
        "example_response": {
            "memories": [
                "This agent prefers short technical answers."
            ]
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
                    "example": "hello agent world",
                }
            },
        },
        "validation_rules": [
            "Input should include a message field.",
        ],
        "output_schema": {
            "type": "object",
            "properties": {
                "echo": "object",
            },
        },
        "example_request": {
            "input": {
                "message": "hello agent world"
            }
        },
        "example_response": {
            "echo": {
                "message": "hello agent world"
            }
        },
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
                    "example": "https://example.com",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum characters of text to return.",
                    "example": 4000,
                },
            },
        },
        "validation_rules": [
            "URL must start with http:// or https://.",
            "URL must contain a valid domain.",
            "Private file paths are not allowed.",
            "If max_chars is provided, it should be a positive integer.",
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
            "content": "Example Domain This domain is for use in illustrative examples...",
            "truncated": False,
            "content_length": 120,
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
                "target_agent_id": {
                    "type": "integer",
                    "description": "ID of the target agent.",
                    "example": 2,
                },
                "task": {
                    "type": "string",
                    "description": "Task to send to the target agent.",
                    "example": "Solve x^2 - 5x + 6 = 0",
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for delegation.",
                    "example": "Math Agent has quadratic_solver capability.",
                },
            },
        },
        "validation_rules": [
            "Caller must have agents:delegate permission.",
            "Target agent must exist and be active.",
            "Task must not be empty.",
            "Target agent executes task using its own permissions and memory.",
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
                "reason": "Math Agent is better suited for calculations.",
            }
        },
        "example_response": {
            "target_agent_id": 2,
            "target_agent_name": "Math Agent",
            "response": "45 * 12 = 540.",
            "tool_calls": [
                {
                    "tool_name": "calculator",
                    "status": "success",
                }
            ],
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
                "url": {
                    "type": "string",
                    "description": "Website URL or direct RSS/Atom feed URL.",
                    "example": "https://example.com",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum feed entries to return.",
                    "example": 5,
                },
            },
        },
        "validation_rules": [
            "URL must start with http:// or https://.",
            "URL can be a website homepage or a direct RSS/Atom feed.",
            "Tool tries common feed paths automatically.",
            "If no feed exists, the tool returns a structured failure.",
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
                "limit": 5
            }
        },
        "example_response": {
            "source_url": "https://example.com",
            "feed_url": "https://example.com/feed/",
            "feed_title": "Example Feed",
            "entries": [
                {
                    "title": "Example title",
                    "link": "https://example.com/article",
                    "summary": "Example summary",
                    "published": "Example date"
                }
            ]
        },
    },
}


DEFAULT_TOOLS = [
    {
        "name": spec["name"],
        "description": spec["description"],
        "permission_required": spec["permission_required"],
    }
    for spec in TOOL_SPECS.values()
]


def seed_tools(db: Session):
    for tool_data in DEFAULT_TOOLS:
        existing_tool = (
            db.query(Tool)
            .filter(Tool.name == tool_data["name"])
            .first()
        )

        if not existing_tool:
            db.add(Tool(**tool_data))

    db.commit()


def get_tool_spec(tool_name: str):
    return TOOL_SPECS.get(tool_name)


def list_tool_specs():
    return list(TOOL_SPECS.values())


def run_registered_tool(tool_name: str, input_data: dict):
    tool = TOOL_FUNCTIONS.get(tool_name)

    if not tool:
        raise ValueError("Tool not found")

    return tool(input_data)