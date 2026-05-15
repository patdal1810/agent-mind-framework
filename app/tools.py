import numexpr as ne
from sympy import Eq, symbols, solve
import requests
from bs4 import BeautifulSoup

from app.agent_runtime import run_agent_runtime
from app.models import Agent

from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)

from app.memory_service import search_memory
from app.tool_validators import (
    validate_calculator_expression,
    validate_quadratic_equation,validate_url
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


def quadratic_solver_tool(input_data: dict):
    equation = input_data.get("equation")
    original_task = input_data.get("original_task", "")

    combined_input = f"{original_task} {equation}".lower()

    if "double power" in combined_input:
        raise ValueError(
            "Invalid quadratic input. The phrase 'double power' is ambiguous. "
            "Use clear format like: 2x^2 - 8x + 6 = 0."
        )

    if "raise to double" in combined_input:
        raise ValueError(
            "Invalid quadratic input. The phrase 'raise to double' is ambiguous. "
            "Use clear format like: 2x^2 - 8x + 6 = 0."
        )

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


def url_reader_tool(input_data: dict):
    url = input_data.get("url")
    max_chars = input_data.get("max_chars", 4000)

    validation = validate_url(url)

    if not validation.is_valid:
        raise ValueError(validation.error)

    try:
        response = requests.get(
            validation.cleaned_input,
            timeout=10,
            headers={
                "User-Agent": "AgentMindBot/0.1"
            }
        )
        response.raise_for_status()

    except requests.RequestException as error:
        raise ValueError(f"Could not fetch URL: {str(error)}")

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = " ".join(soup.get_text(separator=" ").split())

    if not text:
        raise ValueError("No readable text found at URL.")

    return {
        "url": validation.cleaned_input,
        "title": soup.title.string.strip() if soup.title and soup.title.string else None,
        "content": text[:max_chars],
        "truncated": len(text) > max_chars,
        "content_length": len(text),
    }