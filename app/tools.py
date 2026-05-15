import numexpr as ne

from app.memory_service import search_memory

from sympy import Eq, symbols, solve
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)
from app.memory_service import search_memory
from app.tool_validators import (
    validate_calculator_expression,
    validate_quadratic_equation,
)


x = symbols("x")

TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
)


def calculator_tool(input_data: dict):
    expression = input_data.get("expression")

    validation = validate_calculator_expression(expression)

    if not validation.is_valid:
        raise ValueError(validation.error)

    result = ne.evaluate(validation.cleaned_input)

    return {
        "expression": validation.cleaned_input,
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


def quadratic_solver_tool(input_data: dict):
    equation = input_data.get("equation")

    validation = validate_quadratic_equation(equation)

    if not validation.is_valid:
        raise ValueError(validation.error)

    expr = parse_expr(
        validation.cleaned_input,
        transformations=TRANSFORMATIONS,
    )

    result = solve(Eq(expr, 0), x)

    return {
        "original_equation": equation,
        "normalized_equation": validation.cleaned_input,
        "solutions": [str(r) for r in result],
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