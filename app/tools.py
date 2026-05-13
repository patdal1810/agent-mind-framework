import numexpr as ne

from app.memory_service import search_memory


def calculator_tool(input_data: dict):
    expression = input_data.get("expression")

    if not expression:
        raise ValueError("Missing expression")

    result = ne.evaluate(expression)

    return {
        "answer": str(result),
    }


def memory_search_tool(input_data: dict):
    agent_id = input_data.get("agent_id")
    query = input_data.get("query")
    limit = input_data.get("limit", 5)

    if not agent_id:
        raise ValueError("Missing agent_id")

    if not query:
        raise ValueError("Missing query")

    memories = search_memory(
        agent_id=agent_id,
        query=query,
        limit=limit,
    )

    return {
        "memories": memories,
    }


def echo_tool(input_data: dict):
    return {
        "echo": input_data,
    }