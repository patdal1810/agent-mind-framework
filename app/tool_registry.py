from sqlalchemy.orm import Session
from app.models import Tool
from app.tools import calculator_tool, echo_tool, memory_search_tool, quadratic_solver_tool

TOOL_FUNCTIONS = {
    "calculator": calculator_tool,
    "memory_search": memory_search_tool,
    "echo": echo_tool,
    "quadratic_solver": quadratic_solver_tool,
}


DEFAULT_TOOLS = [
    {
        "name": "calculator",
        "description": "Safely evaluates basic math expressions.",
        "permission_required": "tools:calculator:run",
    },
    {
        "name": "memory_search",
        "description": "Searches stored memories for the current agent.",
        "permission_required": "memory:read",
    },
    {
        "name": "echo",
        "description": "Returns the same input. Useful for testing.",
        "permission_required": "tools:echo:run",
    },
    {
        "name": "quadratic_solver",
        "description": "Solves quadratic equations symbolically.",
        "permission_required": "tools:quadratic_solver:run",
    },
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


def run_registered_tool(tool_name: str, input_data: dict):
    tool = TOOL_FUNCTIONS.get(tool_name)

    if not tool:
        raise ValueError("Tool not found")

    return tool(input_data)