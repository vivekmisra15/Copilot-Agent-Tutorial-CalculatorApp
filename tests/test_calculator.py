import math

import pytest
from fastapi.testclient import TestClient

from calculator import MEMORY_BANKS, app, evaluate_expression, evaluate_graph

client = TestClient(app)


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
    assert evaluate_expression("pow10(3)") == 1000
    assert evaluate_expression("inv(4)") == 0.25
    assert round(evaluate_expression("asin(1)", mode="deg"), 6) == 90


def test_invalid_expression():
    with pytest.raises(ValueError):
        evaluate_expression("2 +")


def test_graph_discontinuity_generates_segments():
    graph_data = evaluate_graph("1/x", x_min=-5, x_max=5, samples=300)
    assert len(graph_data["segments"]) >= 2


def test_graph_invalid_window():
    with pytest.raises(ValueError):
        evaluate_graph("x", x_min=5, x_max=5)


def test_calc_api_backward_compatible():
    response = client.post("/api/calc", json={"expression": "2+3*4", "mode": "rad"})
    assert response.status_code == 200
    assert response.json()["result"] == 14


def test_graph_api_response_shape():
    response = client.post(
        "/api/graph",
        json={"expression": "sin(x)", "mode": "rad", "x_min": -6, "x_max": 6, "samples": 300},
    )
    payload = response.json()
    assert response.status_code == 200
    assert "segments" in payload
    assert "y_min" in payload
    assert "y_max" in payload


def test_memory_api_flow():
    for bank in ["M1", "M2", "M3"]:
        client.post("/api/memory", json={"operation": "MC", "bank": bank})

    mplus = client.post("/api/memory", json={"operation": "M+", "bank": "M1", "value": 10})
    assert mplus.status_code == 200
    assert mplus.json()["value"] == 10

    mminus = client.post("/api/memory", json={"operation": "M-", "bank": "M1", "value": 3})
    assert mminus.status_code == 200
    assert mminus.json()["value"] == 7

    mr = client.post("/api/memory", json={"operation": "MR", "bank": "M1"})
    assert mr.status_code == 200
    assert mr.json()["value"] == 7

    mc = client.post("/api/memory", json={"operation": "MC", "bank": "M1"})
    assert mc.status_code == 200
    assert mc.json()["value"] == 0

    assert MEMORY_BANKS["M1"] == 0
