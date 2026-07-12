import math

import pytest
from fastapi.testclient import TestClient

from calculator import (
    MEMORY_BANKS,
    app,
    compile_expression,
    evaluate_compiled_expression,
    evaluate_expression,
    evaluate_graph,
    reset_calculator_state,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    reset_calculator_state(remove_persisted=True)
    yield
    reset_calculator_state(remove_persisted=True)


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


def test_compiled_expression_reuses_parsed_tree():
    compiled = compile_expression("x^2 + 2*x + 1")

    assert evaluate_compiled_expression(compiled, variables={"x": 2}) == 9
    assert evaluate_compiled_expression(compiled, variables={"x": -3}) == 4


def test_invalid_expression():
    with pytest.raises(ValueError):
        evaluate_expression("2 +")


def test_invalid_mode_rejected():
    with pytest.raises(ValueError):
        evaluate_expression("2+2", mode="grad")


def test_factorial_requires_non_negative_integer():
    with pytest.raises(ValueError):
        evaluate_expression("factorial(-1)")

    with pytest.raises(ValueError):
        evaluate_expression("factorial(2.5)")


def test_math_domain_errors_surface():
    with pytest.raises(ValueError):
        evaluate_expression("ln(-1)")

    with pytest.raises(ValueError):
        evaluate_expression("sqrt(-1)")


def test_graph_discontinuity_generates_segments():
    graph_data = evaluate_graph("1/x", x_min=-5, x_max=5, samples=300)
    assert len(graph_data["segments"]) >= 2


def test_graph_invalid_window():
    with pytest.raises(ValueError):
        evaluate_graph("x", x_min=5, x_max=5)


def test_graph_samples_bounds_enforced():
    with pytest.raises(ValueError):
        evaluate_graph("x", samples=39)

    with pytest.raises(ValueError):
        evaluate_graph("x", samples=2001)


def test_calc_api_backward_compatible():
    response = client.post("/api/calc", json={"expression": "2+3*4", "mode": "rad"})
    assert response.status_code == 200
    assert response.json()["result"] == 14


def test_calc_api_rejects_unknown_identifier():
    response = client.post("/api/calc", json={"expression": "unknown_var + 1", "mode": "rad"})
    assert response.status_code == 400
    assert "Unknown identifier" in response.json()["detail"]


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


def test_memory_api_rejects_invalid_bank():
    response = client.post("/api/memory", json={"operation": "MR", "bank": "M9"})
    assert response.status_code == 400
    assert "bank must be one of" in response.json()["detail"]


def test_state_api_persists_graph_slots_and_window():
    response = client.post(
        "/api/state",
        json={
            "mode": "deg",
            "active_bank": "M2",
            "graph_window": {"x_min": -8, "x_max": 8, "samples": 240},
            "graph_functions": [
                {"slot": "Y1", "expression": "sin(x)", "enabled": True},
                {"slot": "Y2", "expression": "x^2", "enabled": True},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "deg"
    assert payload["active_bank"] == "M2"
    assert payload["graph_window"]["samples"] == 240
    assert payload["graph_functions"][0]["expression"] == "sin(x)"
    assert payload["graph_functions"][1]["expression"] == "x^2"

    fetched_state = client.get("/api/state")
    assert fetched_state.status_code == 200
    assert fetched_state.json()["graph_functions"][0]["enabled"] is True


def test_state_api_partial_update_preserves_existing_window():
    response = client.post(
        "/api/state",
        json={
            "graph_window": {"x_min": -4, "x_max": 4, "samples": 180},
            "mode": "rad",
        },
    )
    assert response.status_code == 200

    mode_only_update = client.post("/api/state", json={"mode": "deg"})
    assert mode_only_update.status_code == 200
    payload = mode_only_update.json()
    assert payload["mode"] == "deg"
    assert payload["graph_window"] == {"x_min": -4.0, "x_max": 4.0, "samples": 180}


def test_graph_set_api_returns_multiple_functions():
    response = client.post(
        "/api/graph-set",
        json={
            "mode": "rad",
            "x_min": -6,
            "x_max": 6,
            "samples": 280,
            "graph_functions": [
                {"slot": "Y1", "expression": "sin(x)", "enabled": True},
                {"slot": "Y2", "expression": "x/2", "enabled": True},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["functions"]) == 2
    assert payload["functions"][0]["slot"] == "Y1"
    assert payload["functions"][1]["slot"] == "Y2"
    assert payload["y_min"] <= payload["y_max"]


def test_graph_set_api_rejects_no_enabled_functions():
    response = client.post(
        "/api/graph-set",
        json={
            "mode": "rad",
            "graph_functions": [
                {"slot": "Y1", "expression": "sin(x)", "enabled": False},
                {"slot": "Y2", "expression": "", "enabled": True},
            ],
        },
    )

    assert response.status_code == 400
    assert "No enabled graph functions" in response.json()["detail"]
