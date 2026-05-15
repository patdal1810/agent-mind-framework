import re
from dataclasses import dataclass
from urllib.parse import urlparse

from sympy import Poly, symbols
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)


x = symbols("x")

TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
)


@dataclass
class ValidationResult:
    is_valid: bool
    cleaned_input: str | None = None
    error: str | None = None


def normalize_math_text(value: str) -> str:
    """
    Converts common messy symbols into safer math syntax.
    """

    cleaned = value.strip().lower()

    cleaned = cleaned.replace("“", "").replace("”", "")
    cleaned = cleaned.replace("‘", "").replace("’", "")
    cleaned = cleaned.replace("−", "-")
    cleaned = cleaned.replace("—", "-")
    cleaned = cleaned.replace("^", "**")
    cleaned = cleaned.replace("²", "**2")

    cleaned = cleaned.replace("x squared", "x**2")
    cleaned = cleaned.replace("x square", "x**2")
    cleaned = cleaned.replace("raised to the power of", "**")
    cleaned = cleaned.replace("raise to the power of", "**")

    return cleaned.strip()


def validate_calculator_expression(expression: str) -> ValidationResult:
    """
    Calculator should only accept numeric arithmetic.

    It should reject:
    - variables like x
    - equations with =
    - algebraic expressions
    - natural language
    """

    if not expression or not expression.strip():
        return ValidationResult(False, error="Calculator input is empty.")

    cleaned = normalize_math_text(expression)

    if "=" in cleaned:
        return ValidationResult(
            False,
            error="Calculator only accepts numeric expressions, not equations with '='.",
        )

    if re.search(r"[a-zA-Z]", cleaned):
        return ValidationResult(
            False,
            error="Calculator only accepts numeric arithmetic. Variables or words are not allowed.",
        )

    allowed_pattern = r"^[0-9\s\.\+\-\*\/\%\(\)]+$"

    if not re.match(allowed_pattern, cleaned):
        return ValidationResult(
            False,
            error="Calculator input contains unsupported characters.",
        )

    return ValidationResult(True, cleaned_input=cleaned)


def validate_quadratic_equation(equation: str) -> ValidationResult:
    """
    Quadratic solver should only accept clean quadratic equations.

    Required shape:
    ax^2 + bx + c = 0

    Rules:
    - Must contain x
    - Must contain =
    - Must be degree 2
    - Must only use variable x
    - Right side should simplify safely
    - Reject natural language or ambiguous wording
    """

    if not equation or not equation.strip():
        return ValidationResult(False, error="Equation input is empty.")

    cleaned = normalize_math_text(equation)

    # Remove common task wording if OpenAI passes it through
    prefixes = [
        "solve this quadratic equation:",
        "solve quadratic equation:",
        "find the roots of:",
        "find roots of:",
        "solve:",
    ]

    for prefix in prefixes:
        cleaned = cleaned.replace(prefix, "")

    cleaned = cleaned.strip()

    if "double power" in cleaned:
        return ValidationResult(
            False,
            error="Ambiguous exponent wording: 'double power' is not valid math syntax. Use x^2.",
        )

    if "raise" in cleaned or "power" in cleaned:
        return ValidationResult(
            False,
            error="Ambiguous exponent wording detected. Use clear syntax like x^2.",
        )

    if "x" not in cleaned:
        return ValidationResult(
            False,
            error="Quadratic equation must contain the variable x.",
        )

    if "=" not in cleaned:
        return ValidationResult(
            False,
            error="Quadratic equation must include '='. Example: x^2 - 5x + 6 = 0.",
        )

    if cleaned.count("=") != 1:
        return ValidationResult(
            False,
            error="Equation must contain exactly one '=' sign.",
        )

    left_side, right_side = cleaned.split("=", 1)

    if not left_side.strip() or not right_side.strip():
        return ValidationResult(
            False,
            error="Both sides of the equation must be present.",
        )

    try:
        expr = parse_expr(
            f"({left_side}) - ({right_side})",
            transformations=TRANSFORMATIONS,
        )

        free_symbols = expr.free_symbols

        if free_symbols != {x}:
            return ValidationResult(
                False,
                error="Quadratic solver only supports equations with one variable: x.",
            )

        poly = Poly(expr, x)

        if poly.degree() != 2:
            return ValidationResult(
                False,
                error=f"Equation must be quadratic with degree 2. Detected degree {poly.degree()}.",
            )

        cleaned_equation = f"({left_side}) - ({right_side})"

        return ValidationResult(True, cleaned_input=cleaned_equation)

    except Exception as error:
        return ValidationResult(
            False,
            error=(
                "Equation is not a valid regular quadratic equation. "
                "Use a clear format like: x^2 - 5x + 6 = 0. "
                f"Parser error: {str(error)}"
            ),
        )
    
def validate_url(value: str) -> ValidationResult:
    if not value or not value.strip():
        return ValidationResult(False, error="URL is required.")

    parsed = urlparse(value.strip())

    if parsed.scheme not in ["http", "https"]:
        return ValidationResult(
            False,
            error="URL must start with http:// or https://."
        )

    if not parsed.netloc:
        return ValidationResult(
            False,
            error="URL must include a valid domain."
        )

    return ValidationResult(True, cleaned_input=value.strip())