import numexpr as ne

from app.memory_service import search_memory

from sympy import Eq, symbols, solve
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)


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

    cleaned = equation.lower()

    cleaned = cleaned.replace("“", "").replace("”", "")
    cleaned = cleaned.replace("−", "-")
    cleaned = cleaned.replace("^", "**")
    cleaned = cleaned.replace("raise to the power of", "**")
    cleaned = cleaned.replace("raised to the power of", "**")
    cleaned = cleaned.replace("x squared", "x**2")
    cleaned = cleaned.replace("x square", "x**2")

    cleaned = cleaned.replace("solve this quadratic equation:", "")
    cleaned = cleaned.replace("solve quadratic equation:", "")
    cleaned = cleaned.replace("solve:", "")
    cleaned = cleaned.strip()

    if "=" in cleaned:
        left_side, right_side = cleaned.split("=", 1)
        cleaned = f"({left_side}) - ({right_side})"

    transformations = standard_transformations + (
        implicit_multiplication_application,
    )

    try:
        expr = parse_expr(
            cleaned,
            transformations=transformations,
        )

        result = solve(Eq(expr, 0), x)

        return {
            "original_equation": equation,
            "cleaned_equation": cleaned,
            "solutions": [str(r) for r in result],
        }

    except Exception as error:
        raise ValueError(
            f"Could not parse equation. Original: {equation}. Cleaned: {cleaned}. Error: {str(error)}"
        )