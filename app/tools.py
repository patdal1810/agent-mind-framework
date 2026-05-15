import numexpr as ne

from app.memory_service import search_memory

from sympy import Eq, symbols, solve
from sympy.parsing.sympy_parser import parse_expr


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

def quadratic_solver_tool(input_data: dict):
    equation = input_data.get("equation")

    if not equation:
        raise ValueError("Missing equation")
    
    x = symbols("x")

    cleaned_equation = (
        equation.replace("^", "**")
        .replace("=0", "")
        .strip()
    )

    expr = parse_expr(cleaned_equation)

    result = solve(Eq(expr, 0), x)

    return {
        "equation": equation,
        "solution": [str(r) for r in result]
    }