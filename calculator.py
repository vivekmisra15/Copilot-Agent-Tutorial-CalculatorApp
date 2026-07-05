from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import ast
import operator

app = FastAPI(title="Modern Calculator")
app.mount("/static", StaticFiles(directory="static"), name="static")


class CalcRequest(BaseModel):
    expression: str


class CalcResponse(BaseModel):
    expression: str
    result: float | int | None


OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}


def evaluate_expression(expression: str):
    expression = expression.strip()
    if not expression:
        raise ValueError("Expression is empty")

    tree = ast.parse(expression, mode="eval")
    return _eval_node(tree.body)


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand)

    if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return OPERATORS[type(node.op)](left, right)

    raise ValueError("Unsupported expression")


@app.get("/")
def read_root():
    return FileResponse("static/index.html")


@app.post("/api/calc", response_model=CalcResponse)
def calculate(payload: CalcRequest):
    try:
        result = evaluate_expression(payload.expression)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CalcResponse(expression=payload.expression, result=result)
