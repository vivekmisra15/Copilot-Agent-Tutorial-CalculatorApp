import ast
import math
import operator

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Scientific Calculator")
app.mount("/static", StaticFiles(directory="static"), name="static")


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

MEMORY_BANKS = {
    "M1": 0.0,
    "M2": 0.0,
    "M3": 0.0,
}


def evaluate_expression(expression: str, mode: str = "rad", variables: dict[str, float] | None = None):
    expression = expression.strip()
    if not expression:
        raise ValueError("Expression is empty")

    mode = _normalize_mode(mode)

    try:
        tree = ast.parse(expression.replace("^", "**"), mode="eval")
    except SyntaxError as exc:
        raise ValueError("Invalid expression") from exc

    return _eval_node(tree.body, mode=mode, variables=variables or {})


def evaluate_graph(expression: str, mode: str = "rad", x_min: float = -10, x_max: float = 10, samples: int = 300):
    mode = _normalize_mode(mode)
    expr = expression.strip()
    if not expr:
        raise ValueError("Expression is empty")
    if x_min >= x_max:
        raise ValueError("x_min must be less than x_max")
    if samples < 40 or samples > 2000:
        raise ValueError("samples must be between 40 and 2000")

    segments = []
    current_segment = []
    y_values = []

    for i in range(samples):
        x = x_min + (x_max - x_min) * i / (samples - 1)
        try:
            y = evaluate_expression(expr, mode=mode, variables={"x": x})
        except Exception:
            if current_segment:
                segments.append(current_segment)
                current_segment = []
            continue

        if not math.isfinite(y):
            if current_segment:
                segments.append(current_segment)
                current_segment = []
            continue

        if current_segment:
            prev_y = current_segment[-1][1]
            jump_threshold = max(80.0, abs(prev_y) * 4)
            sign_flip_with_high_magnitude = prev_y * y < 0 and max(abs(prev_y), abs(y)) > 20
            if abs(y - prev_y) > jump_threshold:
                segments.append(current_segment)
                current_segment = []
            elif sign_flip_with_high_magnitude:
                segments.append(current_segment)
                current_segment = []

        current_segment.append([x, y])
        y_values.append(y)

    if current_segment:
        segments.append(current_segment)

    if not y_values:
        raise ValueError("No plottable points in selected window")

    return {
        "segments": segments,
        "y_min": min(y_values),
        "y_max": max(y_values),
    }


def _normalize_mode(mode: str) -> str:
    normalized = mode.lower().strip()
    if normalized not in {"rad", "deg"}:
        raise ValueError("Mode must be 'rad' or 'deg'")
    return normalized


def _eval_node(node, mode: str = "rad", variables: dict[str, float] | None = None):
    variables = variables or {}

    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand, mode=mode, variables=variables)

    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Pow):
            return _eval_node(node.left, mode=mode, variables=variables) ** _eval_node(
                node.right, mode=mode, variables=variables
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


def apply_memory(operation: str, bank: str, value: float):
    op = operation.upper().strip()
    memory_bank = bank.upper().strip()
    if memory_bank not in MEMORY_BANKS:
        raise ValueError("bank must be one of M1, M2, M3")

    if op == "M+":
        MEMORY_BANKS[memory_bank] += value
    elif op == "M-":
        MEMORY_BANKS[memory_bank] -= value
    elif op == "MC":
        MEMORY_BANKS[memory_bank] = 0.0
    elif op != "MR":
        raise ValueError("operation must be one of M+, M-, MR, MC")

    return {
        "bank": memory_bank,
        "value": MEMORY_BANKS[memory_bank],
        "banks": MEMORY_BANKS,
        "persistence": "Memory is kept while the server process is running",
    }


@app.get("/")
def read_root():
    return FileResponse("static/index.html")


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


@app.get("/api/memory")
def get_memory():
    return {
        "banks": MEMORY_BANKS,
        "persistence": "Memory is kept while the server process is running",
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
