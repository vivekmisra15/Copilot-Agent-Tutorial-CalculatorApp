import ast
import json
import math
import operator
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Scientific Calculator")
app.mount("/static", StaticFiles(directory="static"), name="static")

STATE_FILE = Path(__file__).with_name("calculator_state.json")
FUNCTION_SLOTS = ["Y1", "Y2", "Y3", "Y4", "Y5", "Y6"]
MEMORY_SLOT_NAMES = ["M1", "M2", "M3"]
DEFAULT_FUNCTION_COLORS = ["#1f4f93", "#b33f62", "#2c8c5b", "#9a6700", "#5e3eb3", "#0f766e"]


class CalcRequest(BaseModel):
    expression: str
    mode: str = "rad"


class GraphRequest(CalcRequest):
    x_min: float = -10.0
    x_max: float = 10.0
    samples: int = 300


class CalcResponse(BaseModel):
    expression: str
    result: float | int | None


class MemoryRequest(BaseModel):
    operation: str
    bank: str = "M1"
    value: float | None = None
    expression: str | None = None
    mode: str = "rad"


class GraphFunctionState(BaseModel):
    slot: str
    expression: str = ""
    enabled: bool = False
    color: str | None = None


class GraphWindowState(BaseModel):
    x_min: float = -10.0
    x_max: float = 10.0
    samples: int = 300


class CalculatorStateUpdate(BaseModel):
    mode: str | None = None
    active_bank: str | None = None
    graph_functions: list[GraphFunctionState] | None = None
    graph_window: GraphWindowState | None = None


class GraphSetRequest(BaseModel):
    mode: str | None = None
    graph_functions: list[GraphFunctionState] | None = None
    x_min: float | None = None
    x_max: float | None = None
    samples: int | None = None


OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
}

FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "log": math.log10,
    "ln": math.log,
    "abs": abs,
    "exp": math.exp,
    "pow10": lambda value: 10**value,
    "inv": lambda value: 1 / value,
    "floor": math.floor,
    "ceil": math.ceil,
}

CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}

TRIG_INPUT_FUNCTIONS = {"sin", "cos", "tan"}
TRIG_OUTPUT_FUNCTIONS = {"asin", "acos", "atan"}


def _default_graph_functions() -> list[dict[str, str | bool]]:
    return [
        {
            "slot": slot,
            "expression": "",
            "enabled": False,
            "color": DEFAULT_FUNCTION_COLORS[index],
        }
        for index, slot in enumerate(FUNCTION_SLOTS)
    ]


def _default_state() -> dict[str, Any]:
    return {
        "mode": "rad",
        "active_bank": "M1",
        "memory_banks": {bank: 0.0 for bank in MEMORY_SLOT_NAMES},
        "graph_window": {"x_min": -10.0, "x_max": 10.0, "samples": 300},
        "graph_functions": _default_graph_functions(),
    }


def _normalize_mode(mode: str) -> str:
    normalized = mode.lower().strip()
    if normalized not in {"rad", "deg"}:
        raise ValueError("Mode must be 'rad' or 'deg'")
    return normalized


def _normalize_bank(bank: str) -> str:
    normalized = bank.upper().strip()
    if normalized not in MEMORY_SLOT_NAMES:
        raise ValueError("bank must be one of M1, M2, M3")
    return normalized


def _normalize_slot(slot: str) -> str:
    normalized = slot.upper().strip()
    if normalized not in FUNCTION_SLOTS:
        raise ValueError("slot must be one of Y1, Y2, Y3, Y4, Y5, Y6")
    return normalized


def _normalize_window(x_min: float, x_max: float, samples: int) -> dict[str, float | int]:
    if x_min >= x_max:
        raise ValueError("x_min must be less than x_max")
    if samples < 40 or samples > 2000:
        raise ValueError("samples must be between 40 and 2000")
    return {"x_min": float(x_min), "x_max": float(x_max), "samples": int(samples)}


def _sanitize_graph_functions(raw_functions: list[dict[str, Any]] | None) -> list[dict[str, str | bool]]:
    defaults_by_slot = {item["slot"]: item for item in _default_graph_functions()}
    normalized_by_slot = {slot: dict(defaults_by_slot[slot]) for slot in FUNCTION_SLOTS}

    for item in raw_functions or []:
        slot = _normalize_slot(str(item.get("slot", "")))
        normalized_by_slot[slot] = {
            "slot": slot,
            "expression": str(item.get("expression", "")).strip(),
            "enabled": bool(item.get("enabled", False)),
            "color": str(item.get("color") or defaults_by_slot[slot]["color"]),
        }

    return [normalized_by_slot[slot] for slot in FUNCTION_SLOTS]


def _load_state() -> dict[str, Any]:
    state = _default_state()
    if not STATE_FILE.exists():
        return state

    try:
        payload = json.loads(STATE_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return state

    try:
        state["mode"] = _normalize_mode(str(payload.get("mode", state["mode"])))
    except ValueError:
        pass

    try:
        state["active_bank"] = _normalize_bank(str(payload.get("active_bank", state["active_bank"])))
    except ValueError:
        pass

    memory_banks = payload.get("memory_banks", {})
    for bank in MEMORY_SLOT_NAMES:
        try:
            state["memory_banks"][bank] = float(memory_banks.get(bank, state["memory_banks"][bank]))
        except (TypeError, ValueError):
            continue

    graph_window = payload.get("graph_window", {})
    try:
        state["graph_window"] = _normalize_window(
            float(graph_window.get("x_min", state["graph_window"]["x_min"])),
            float(graph_window.get("x_max", state["graph_window"]["x_max"])),
            int(graph_window.get("samples", state["graph_window"]["samples"])),
        )
    except (TypeError, ValueError):
        pass

    try:
        state["graph_functions"] = _sanitize_graph_functions(payload.get("graph_functions"))
    except ValueError:
        pass

    return state


APP_STATE = _load_state()
MEMORY_BANKS = APP_STATE["memory_banks"]
GRAPH_FUNCTIONS = APP_STATE["graph_functions"]
GRAPH_WINDOW = APP_STATE["graph_window"]


def save_state() -> None:
    STATE_FILE.write_text(json.dumps(APP_STATE, indent=2))


def reset_calculator_state(remove_persisted: bool = False) -> None:
    defaults = _default_state()
    APP_STATE.clear()
    APP_STATE.update(defaults)

    MEMORY_BANKS.clear()
    MEMORY_BANKS.update(APP_STATE["memory_banks"])

    GRAPH_FUNCTIONS.clear()
    GRAPH_FUNCTIONS.extend(APP_STATE["graph_functions"])

    GRAPH_WINDOW.clear()
    GRAPH_WINDOW.update(APP_STATE["graph_window"])

    if remove_persisted and STATE_FILE.exists():
        STATE_FILE.unlink()


class CompiledExpression:
    def __init__(self, source: str, tree: ast.Expression, identifiers: set[str]):
        self.source = source
        self.tree = tree
        self.identifiers = identifiers


def compile_expression(expression: str) -> CompiledExpression:
    stripped_expression = expression.strip()
    if not stripped_expression:
        raise ValueError("Expression is empty")

    try:
        tree = ast.parse(stripped_expression.replace("^", "**"), mode="eval")
    except SyntaxError as exc:
        raise ValueError("Invalid expression") from exc

    identifiers = _collect_identifiers(tree.body)
    return CompiledExpression(source=stripped_expression, tree=tree, identifiers=identifiers)


def _collect_identifiers(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return set()

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return _collect_identifiers(node.operand)

    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Pow) or type(node.op) in OPERATORS:
            return _collect_identifiers(node.left) | _collect_identifiers(node.right)
        raise ValueError("Unsupported expression")

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        func_name = node.func.id
        if func_name == "factorial":
            if len(node.args) != 1:
                raise ValueError("factorial expects exactly one argument")
            return _collect_identifiers(node.args[0])
        if func_name not in FUNCTIONS:
            raise ValueError(f"Unsupported function: {func_name}")
        if len(node.args) != 1:
            raise ValueError(f"{func_name} expects exactly one argument")
        return _collect_identifiers(node.args[0])

    if isinstance(node, ast.Name):
        if node.id in CONSTANTS:
            return set()
        return {node.id}

    raise ValueError("Unsupported expression")


def evaluate_compiled_expression(
    compiled_expression: CompiledExpression,
    mode: str = "rad",
    variables: dict[str, float] | None = None,
):
    return _eval_node(compiled_expression.tree.body, mode=_normalize_mode(mode), variables=variables or {})


def evaluate_expression(expression: str, mode: str = "rad", variables: dict[str, float] | None = None):
    compiled_expression = compile_expression(expression)
    return evaluate_compiled_expression(compiled_expression, mode=mode, variables=variables)


def _sample_graph_expression(
    compiled_expression: CompiledExpression,
    mode: str,
    x_min: float,
    x_max: float,
    samples: int,
) -> dict[str, Any]:
    segments = []
    current_segment = []
    y_values = []

    for index in range(samples):
        x_value = x_min + (x_max - x_min) * index / (samples - 1)
        try:
            y_value = evaluate_compiled_expression(compiled_expression, mode=mode, variables={"x": x_value})
        except Exception:
            if current_segment:
                segments.append(current_segment)
                current_segment = []
            continue

        if not math.isfinite(y_value):
            if current_segment:
                segments.append(current_segment)
                current_segment = []
            continue

        if current_segment:
            previous_y = current_segment[-1][1]
            # Split lines at likely asymptotes to avoid drawing false vertical connectors.
            jump_threshold = max(80.0, abs(previous_y) * 4)
            sign_flip_with_high_magnitude = previous_y * y_value < 0 and max(abs(previous_y), abs(y_value)) > 20
            if abs(y_value - previous_y) > jump_threshold or sign_flip_with_high_magnitude:
                segments.append(current_segment)
                current_segment = []

        current_segment.append([x_value, y_value])
        y_values.append(y_value)

    if current_segment:
        segments.append(current_segment)

    if not y_values:
        raise ValueError("No plottable points in selected window")

    return {
        "segments": segments,
        "y_min": min(y_values),
        "y_max": max(y_values),
    }


def evaluate_graph(expression: str, mode: str = "rad", x_min: float = -10, x_max: float = 10, samples: int = 300):
    normalized_window = _normalize_window(x_min, x_max, samples)
    compiled_expression = compile_expression(expression)
    return _sample_graph_expression(
        compiled_expression,
        mode=_normalize_mode(mode),
        x_min=normalized_window["x_min"],
        x_max=normalized_window["x_max"],
        samples=normalized_window["samples"],
    )


def evaluate_graph_set(
    graph_functions: list[dict[str, str | bool]],
    mode: str = "rad",
    x_min: float = -10,
    x_max: float = 10,
    samples: int = 300,
) -> dict[str, Any]:
    normalized_mode = _normalize_mode(mode)
    normalized_window = _normalize_window(x_min, x_max, samples)
    normalized_functions = _sanitize_graph_functions(graph_functions)

    plotted_functions = []
    y_min_values = []
    y_max_values = []

    for function_state in normalized_functions:
        expression = str(function_state["expression"]).strip()
        if not function_state["enabled"] or not expression:
            continue

        compiled_expression = compile_expression(expression)
        graph_data = _sample_graph_expression(
            compiled_expression,
            mode=normalized_mode,
            x_min=normalized_window["x_min"],
            x_max=normalized_window["x_max"],
            samples=normalized_window["samples"],
        )
        plotted_functions.append(
            {
                "slot": function_state["slot"],
                "expression": expression,
                "color": function_state["color"],
                "segments": graph_data["segments"],
                "y_min": graph_data["y_min"],
                "y_max": graph_data["y_max"],
            }
        )
        y_min_values.append(graph_data["y_min"])
        y_max_values.append(graph_data["y_max"])

    if not plotted_functions:
        raise ValueError("No enabled graph functions to plot")

    return {
        "mode": normalized_mode,
        "x_min": normalized_window["x_min"],
        "x_max": normalized_window["x_max"],
        "samples": normalized_window["samples"],
        "functions": plotted_functions,
        "y_min": min(y_min_values),
        "y_max": max(y_max_values),
    }


def _eval_node(node: ast.AST, mode: str = "rad", variables: dict[str, float] | None = None) -> float | int:
    variables = variables or {}

    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand, mode=mode, variables=variables)

    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Pow):
            return _eval_node(node.left, mode=mode, variables=variables) ** _eval_node(
                node.right,
                mode=mode,
                variables=variables,
            )
        if type(node.op) in OPERATORS:
            left = _eval_node(node.left, mode=mode, variables=variables)
            right = _eval_node(node.right, mode=mode, variables=variables)
            return OPERATORS[type(node.op)](left, right)

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        func_name = node.func.id
        if func_name == "factorial":
            if len(node.args) != 1:
                raise ValueError("factorial expects exactly one argument")
            factorial_value = _eval_node(node.args[0], mode=mode, variables=variables)
            if not float(factorial_value).is_integer() or factorial_value < 0:
                raise ValueError("factorial expects a non-negative integer")
            return math.factorial(int(factorial_value))

        if func_name not in FUNCTIONS:
            raise ValueError(f"Unsupported function: {func_name}")
        if len(node.args) != 1:
            raise ValueError(f"{func_name} expects exactly one argument")
        value = _eval_node(node.args[0], mode=mode, variables=variables)
        if func_name in TRIG_INPUT_FUNCTIONS and mode == "deg":
            value = math.radians(value)
        result = FUNCTIONS[func_name](value)
        if func_name in TRIG_OUTPUT_FUNCTIONS and mode == "deg":
            return math.degrees(result)
        return result

    if isinstance(node, ast.Name):
        if node.id in variables:
            return variables[node.id]
        if node.id in CONSTANTS:
            return CONSTANTS[node.id]
        raise ValueError(f"Unknown identifier: {node.id}")

    raise ValueError("Unsupported expression")


def apply_memory(operation: str, bank: str, value: float) -> dict[str, Any]:
    op = operation.upper().strip()
    memory_bank = _normalize_bank(bank)

    if op == "M+":
        MEMORY_BANKS[memory_bank] += value
    elif op == "M-":
        MEMORY_BANKS[memory_bank] -= value
    elif op == "MC":
        MEMORY_BANKS[memory_bank] = 0.0
    elif op != "MR":
        raise ValueError("operation must be one of M+, M-, MR, MC")

    APP_STATE["memory_banks"] = MEMORY_BANKS
    APP_STATE["active_bank"] = memory_bank
    save_state()

    return {
        "bank": memory_bank,
        "value": MEMORY_BANKS[memory_bank],
        "banks": MEMORY_BANKS,
        "persistence": "Memory and calculator state are saved on disk",
    }


def _state_payload() -> dict[str, Any]:
    return {
        "mode": APP_STATE["mode"],
        "active_bank": APP_STATE["active_bank"],
        "memory_banks": MEMORY_BANKS,
        "graph_window": GRAPH_WINDOW,
        "graph_functions": GRAPH_FUNCTIONS,
        "persistence": "Calculator state is saved on disk",
    }


@app.get("/")
def read_root():
    return FileResponse("static/index.html", headers={"Cache-Control": "no-store"})


@app.get("/sw.js")
def service_worker():
    return FileResponse(
        "static/sw.js",
        media_type="application/javascript",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/state")
def get_state():
    return _state_payload()


@app.post("/api/state")
def update_state(payload: CalculatorStateUpdate):
    try:
        if payload.mode is not None:
            APP_STATE["mode"] = _normalize_mode(payload.mode)

        if payload.active_bank is not None:
            APP_STATE["active_bank"] = _normalize_bank(payload.active_bank)

        if payload.graph_window is not None:
            normalized_window = _normalize_window(
                payload.graph_window.x_min,
                payload.graph_window.x_max,
                payload.graph_window.samples,
            )
            GRAPH_WINDOW.clear()
            GRAPH_WINDOW.update(normalized_window)
            APP_STATE["graph_window"] = GRAPH_WINDOW

        if payload.graph_functions is not None:
            normalized_functions = _sanitize_graph_functions([item.model_dump() for item in payload.graph_functions])
            GRAPH_FUNCTIONS.clear()
            GRAPH_FUNCTIONS.extend(normalized_functions)
            APP_STATE["graph_functions"] = GRAPH_FUNCTIONS

        save_state()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _state_payload()


@app.post("/api/calc", response_model=CalcResponse)
def calculate(payload: CalcRequest):
    try:
        result = evaluate_expression(payload.expression, mode=payload.mode)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CalcResponse(expression=payload.expression, result=result)


@app.post("/api/graph")
def graph(payload: GraphRequest):
    try:
        graph_data = evaluate_graph(
            payload.expression,
            mode=payload.mode,
            x_min=payload.x_min,
            x_max=payload.x_max,
            samples=payload.samples,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "expression": payload.expression,
        "x_min": payload.x_min,
        "x_max": payload.x_max,
        "segments": graph_data["segments"],
        "y_min": graph_data["y_min"],
        "y_max": graph_data["y_max"],
    }


@app.post("/api/graph-set")
def graph_set(payload: GraphSetRequest):
    graph_functions = payload.graph_functions or [GraphFunctionState(**item) for item in GRAPH_FUNCTIONS]
    x_min = payload.x_min if payload.x_min is not None else GRAPH_WINDOW["x_min"]
    x_max = payload.x_max if payload.x_max is not None else GRAPH_WINDOW["x_max"]
    samples = payload.samples if payload.samples is not None else GRAPH_WINDOW["samples"]
    mode = payload.mode or APP_STATE["mode"]

    try:
        graph_payload = evaluate_graph_set(
            [item.model_dump() for item in graph_functions],
            mode=mode,
            x_min=x_min,
            x_max=x_max,
            samples=samples,
        )

        APP_STATE["mode"] = _normalize_mode(mode)
        GRAPH_WINDOW.clear()
        GRAPH_WINDOW.update(_normalize_window(x_min, x_max, samples))
        APP_STATE["graph_window"] = GRAPH_WINDOW
        normalized_functions = _sanitize_graph_functions([item.model_dump() for item in graph_functions])
        GRAPH_FUNCTIONS.clear()
        GRAPH_FUNCTIONS.extend(normalized_functions)
        APP_STATE["graph_functions"] = GRAPH_FUNCTIONS
        save_state()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return graph_payload


@app.get("/api/memory")
def get_memory():
    return {
        "banks": MEMORY_BANKS,
        "active_bank": APP_STATE["active_bank"],
        "persistence": "Memory and calculator state are saved on disk",
    }


@app.post("/api/memory")
def memory(payload: MemoryRequest):
    try:
        input_value = payload.value
        if input_value is None and payload.expression:
            input_value = float(evaluate_expression(payload.expression, mode=payload.mode))
        if input_value is None:
            input_value = 0.0
        memory_result = apply_memory(payload.operation, payload.bank, input_value)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return memory_result
