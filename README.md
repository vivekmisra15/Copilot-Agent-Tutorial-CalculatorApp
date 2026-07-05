# Graphing Calculator (FastAPI + TI-84 Inspired UI)

A browser-based graphing calculator built with FastAPI and a custom frontend that mimics a TI-84-style workflow.

It supports scientific expressions, graph plotting, angle mode switching (RAD/DEG), memory banks, and calculation history.

## Project Description

Interactive graphing calculator web app with a TI-84-inspired interface, built using FastAPI. It evaluates scientific expressions, plots functions over configurable windows, and supports memory operations across multiple banks.

## Highlights

- TI-84-inspired calculator layout with graph screen on top and keypad below
- Scientific expression parser with safe AST-based evaluation
- Graph plotting API with discontinuity-aware segmented output
- RAD/DEG support for trigonometric functions
- Memory operations: M+, M-, MR, MC
- Memory banks: M1, M2, M3
- Calculation and action history in UI
- Automated tests for core math, graphing, and memory APIs

## Tech Stack

- Backend: FastAPI
- Frontend: HTML, CSS, JavaScript (vanilla)
- Testing: pytest + FastAPI TestClient

## Project Structure

- calculator.py: FastAPI app, expression engine, graphing logic, memory endpoints
- static/index.html: TI-84-style frontend UI and graph canvas rendering
- tests/test_calculator.py: unit/API tests
- requirements.txt: Python dependencies

## API Endpoints

- GET /
  - Serves the calculator web UI

- POST /api/calc
  - Evaluate expression
  - Request:
    - expression: string
    - mode: rad | deg
  - Response:
    - expression
    - result

- POST /api/graph
  - Generate graph data for y = f(x)
  - Request:
    - expression: string (use x as variable)
    - mode: rad | deg
    - x_min: float
    - x_max: float
    - samples: int (40 to 2000)
  - Response:
    - expression
    - x_min
    - x_max
    - segments: array of point arrays for discontinuity-safe plotting
    - y_min
    - y_max

- GET /api/memory
  - Returns current memory banks and persistence note

- POST /api/memory
  - Memory operations
  - Request:
    - operation: M+ | M- | MR | MC
    - bank: M1 | M2 | M3
    - value: optional float
    - expression: optional expression string (used when value is omitted)
    - mode: rad | deg
  - Response:
    - bank
    - value
    - banks
    - persistence

## Getting Started

1. Create and activate virtual environment (if needed)

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app

```bash
.venv/bin/python -m uvicorn calculator:app --host 127.0.0.1 --port 8000
```

4. Open in browser

- App: http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs

## Run Tests

```bash
.venv/bin/python -m pytest -q
```

## Example Expressions

- 2 + 3 * 4
- sin(pi/2)
- ln(e)
- factorial(5)
- pow10(3)
- inv(4)
- sin(90) (with mode=deg)
- Graph examples: x, x^2, sin(x), 1/x, tan(x)

## Notes

- Expression evaluation is AST-based and restricted to supported operations/functions.
- Memory is process-scoped (resets when server restarts).
- Graph output uses segmented lines to avoid drawing across vertical discontinuities.

## License

Use this project as a learning/demo starter. Add a formal license file if you plan to distribute it.
