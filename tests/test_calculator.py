import math

import pytest

from calculator import evaluate_expression


def test_basic_arithmetic():
    assert evaluate_expression("2 + 3 * 4") == 14


def test_scientific_functions():
    assert evaluate_expression("sqrt(16)") == 4.0
    assert evaluate_expression("2^3") == 8.0
    assert math.isclose(evaluate_expression("sin(pi/2)"), 1.0, abs_tol=1e-9)
    assert math.isclose(evaluate_expression("ln(e)"), 1.0, abs_tol=1e-9)
    assert evaluate_expression("abs(-5)") == 5
    assert evaluate_expression("factorial(5)") == 120
    assert math.isclose(evaluate_expression("sin(90)", mode="deg"), 1.0, abs_tol=1e-9)


def test_invalid_expression():
    with pytest.raises(ValueError):
        evaluate_expression("2 +")
