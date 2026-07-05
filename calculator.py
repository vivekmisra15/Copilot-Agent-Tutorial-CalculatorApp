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


class CalcResponse(BaseModel):
    expression: str
    result: float | int | None


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
    "log": math.log10,
    "ln": math.log,
    "abs": abs,
}

CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


def evaluate_expression(expression: str, mode: str = "rad"):
    expression = expression.strip()
    if not expression:
        raise ValueError("Expression is empty")

    if mode not in {"rad", "deg"}:
        raise ValueError("Mode must be 'rad' or 'deg'")

    try:
        tree = ast.parse(expression.replace("^", "**"), mode="eval")
    except SyntaxError as exc:
        raise ValueError("Invalid expression") from exc

    return _eval_node(tree.body, mode=mode)


def _eval_node(node, mode: str = "rad"):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand, mode=mode)

    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Pow):
            return _eval_node(node.left, mode=mode) ** _eval_node(node.right, mode=mode)
        if type(node.op) in OPERATORS:
            left = _eval_node(node.left, mode=mode)
            right = _eval_node(node.right, mode=mode)
            return OPERATORS[type(node.op)](left, right)

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        func_name = node.func.id
        if func_name == "factorial":
            if len(node.args) != 1:
                raise ValueError("factorial expects exactly one argument")
            return math.factorial(int(_eval_node(node.args[0], mode=mode)))
        if func_name not in FUNCTIONS:
            raise ValueError(f"Unsupported function: {func_name}")
        if len(node.args) != 1:
            raise ValueError(f"{func_name} expects exactly one argument")
        value = _eval_node(node.args[0], mode=mode)
        if func_name in {"sin", "cos", "tan"} and mode == "deg":
            value = math.radians(value)
        return FUNCTIONS[func_name](value)

    if isinstance(node, ast.Name):
        if node.id in CONSTANTS:
            return CONSTANTS[node.id]
        raise ValueError(f"Unknown identifier: {node.id}")

    raise ValueError("Unsupported expression")


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
