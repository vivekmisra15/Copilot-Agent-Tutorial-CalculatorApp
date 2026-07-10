# TI-84 Plus Replica Graphing Calculator

A browser-based graphing calculator built with FastAPI and a TI-84 Plus-inspired frontend. The UI closely replicates the physical device — complete with the green LCD screen, dark slate shell, color-coded keypad rows, and secondary/ALPHA key legends printed above each key.

## Project Description

This is an interactive graphing calculator web app that authentically mimics the TI-84 Plus experience in the browser. It evaluates scientific expressions with a safe AST-based engine, plots up to six simultaneous functions on a live canvas, manages persistent calculator state, and supports memory operations across three named banks.

## Highlights

- **Authentic TI-84 Plus shell** — slate-gray device body, green phosphor LCD bezel, branded top-case strip reading "Graphing Calculator" with a "2nd labels mimic device functions" note
- **Accurate function-key bar** — five blue tab buttons (Y=, WINDOW, ZOOM, TRACE, GRAPH) with gold `2nd` labels (Stat Plot, TblSet, Format, Calc, Table) matching real TI-84 row ordering
- **11-key utility strip** — 2nd, MODE, DEL, ALPHA, X,T,θ,n, STAT, MATH, APPS, PRGM, VARS, CLEAR with gold/blue secondary legends
- **Full 5×7 main keypad** — gray scientific-function keys (SIN, COS, TAN, LOG, LN, x², x⁻¹), black navigation/operator keys, orange arithmetic keys (÷, ×, −, +), and a tall double-height ENTER button
- **Dedicated right-side auxiliary grid** — Y=, WINDOW, ZOOM, GRAPH, QUIT, π, e, ABS, FLOOR, CEIL, ASIN, ACOS, ATAN, 10ˣ, eˣ, ENTER, SAVE, ZOOM STD, DRAW, FACT
- **Four screen views**: Home (expression entry), Y= editor (up to Y1–Y6), WINDOW settings, GRAPH canvas
- **Multi-function graphing** — plot up to six color-coded functions simultaneously with discontinuity-aware segmented rendering
- **Configurable graph window** — xMin, xMax, sample count (40–2000); ZOOM STD resets to standard window
- **Three memory banks** — M1, M2, M3 with M+, M−, MR, MC operations; values persist to disk across server restarts
- **Calculator state persistence** — active mode, active bank, graph window, and function slots are saved to `calculator_state.json` and reloaded on startup
- **RAD/DEG angle mode** — toggle from the keypad; status shown live in the screen header
- **Calculation history** — last evaluated expressions are listed below the device shell
- **Safe expression engine** — AST-based evaluator; no `eval()` or arbitrary code execution
- **Automated test suite** — covers core math, graphing, memory, state, and multi-function graph APIs

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Expression engine | AST-based evaluator (no `eval`) |
| Frontend | Vanilla HTML, CSS, JavaScript |
| Persistence | JSON file (`calculator_state.json`) |
| Testing | pytest, FastAPI TestClient, httpx |

## Project Structure

```
.
├── calculator.py            # FastAPI app, expression engine, graphing logic, all API endpoints
├── calculator_state.json    # Persisted calculator state (auto-created on first save)
├── requirements.txt         # Python dependencies
├── static/
│   └── index.html           # TI-84-style frontend: shell, screen, keypad, canvas, JS logic
└── tests/
    └── test_calculator.py   # Unit and API tests
```

## API Endpoints

### `GET /`
Serves the calculator web UI.

---

### `POST /api/calc`
Evaluate a mathematical expression.

**Request body:**
```json
{ "expression": "sin(pi/2)", "mode": "rad" }
```

**Response:**
```json
{ "expression": "sin(pi/2)", "result": 1.0 }
```

---

### `POST /api/graph`
Generate graph data for a single `y = f(x)` expression.

**Request body:**
```json
{
  "expression": "sin(x)",
  "mode": "rad",
  "x_min": -6.28,
  "x_max": 6.28,
  "samples": 300
}
```

**Response:**
```json
{
  "expression": "sin(x)",
  "x_min": -6.28,
  "x_max": 6.28,
  "segments": [[[x1, y1], [x2, y2], ...]],
  "y_min": -1.0,
  "y_max": 1.0
}
```

`segments` is an array of polyline arrays; gaps represent discontinuities (e.g. `1/x` near zero, `tan(x)` near asymptotes).

---

### `POST /api/graph-set`
Plot up to six enabled function slots simultaneously and return combined bounds.

**Request body:**
```json
{
  "mode": "rad",
  "x_min": -10,
  "x_max": 10,
  "samples": 300,
  "graph_functions": [
    { "slot": "Y1", "expression": "sin(x)", "enabled": true },
    { "slot": "Y2", "expression": "x^2/10", "enabled": true }
  ]
}
```

**Response:**
```json
{
  "mode": "rad",
  "x_min": -10,
  "x_max": 10,
  "samples": 300,
  "functions": [
    { "slot": "Y1", "expression": "sin(x)", "color": "#1f4f93", "segments": [...], "y_min": -1.0, "y_max": 1.0 },
    { "slot": "Y2", "expression": "x^2/10", "color": "#b33f62", "segments": [...], "y_min": 0.0, "y_max": 10.0 }
  ],
  "y_min": -1.0,
  "y_max": 10.0
}
```

---

### `GET /api/memory`
Returns current memory bank values.

**Response:**
```json
{
  "banks": { "M1": 0.0, "M2": 0.0, "M3": 0.0 },
  "active_bank": "M1",
  "persistence": "Memory and calculator state are saved on disk"
}
```

---

### `POST /api/memory`
Perform a memory operation on a named bank.

**Request body:**
```json
{ "operation": "M+", "bank": "M1", "value": 42.0, "mode": "rad" }
```

Operations: `M+` (add to bank), `M-` (subtract from bank), `MR` (read bank), `MC` (clear bank to zero).  
`value` is optional — if omitted, `expression` is evaluated instead.

**Response:**
```json
{
  "bank": "M1",
  "value": 42.0,
  "banks": { "M1": 42.0, "M2": 0.0, "M3": 0.0 },
  "persistence": "Memory and calculator state are saved on disk"
}
```

---

### `GET /api/state`
Return the full persisted calculator state.

**Response:**
```json
{
  "mode": "rad",
  "active_bank": "M1",
  "graph_window": { "x_min": -10.0, "x_max": 10.0, "samples": 300 },
  "graph_functions": [
    { "slot": "Y1", "expression": "sin(x)", "enabled": true, "color": "#1f4f93" },
    ...
  ]
}
```

---

### `POST /api/state`
Update and persist the calculator state (mode, active bank, graph window, function slots).

**Request body** (all fields optional):
```json
{
  "mode": "deg",
  "active_bank": "M2",
  "graph_window": { "x_min": -8, "x_max": 8, "samples": 240 },
  "graph_functions": [
    { "slot": "Y1", "expression": "cos(x)", "enabled": true }
  ]
}
```

---

## Supported Functions and Operators

| Expression | Description |
|------------|-------------|
| `+  -  *  /` | Arithmetic |
| `^` | Exponentiation (`2^3` → 8) |
| `sin(x)`, `cos(x)`, `tan(x)` | Trigonometry (RAD or DEG) |
| `asin(x)`, `acos(x)`, `atan(x)` | Inverse trig (output in active mode) |
| `sqrt(x)` | Square root |
| `log(x)` | Base-10 logarithm |
| `ln(x)` | Natural logarithm |
| `exp(x)` | eˣ |
| `pow10(x)` | 10ˣ |
| `abs(x)` | Absolute value |
| `floor(x)`, `ceil(x)` | Floor / ceiling |
| `factorial(n)` | Factorial (`factorial(5)` → 120) |
| `inv(x)` | Reciprocal (1/x) |
| `pi`, `e` | Mathematical constants |
| `x` | Variable (used in graph expressions) |

## Getting Started

### 1. Create and activate a virtual environment

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the app

```bash
.venv/bin/python -m uvicorn calculator:app --host 127.0.0.1 --port 8000
```

### 4. Open in browser

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000 | Calculator app |
| http://127.0.0.1:8000/docs | Interactive API docs (Swagger UI) |
| http://127.0.0.1:8000/redoc | API docs (ReDoc) |

## Run Tests

```bash
.venv/bin/python -m pytest -q
```

## Example Expressions

```
2 + 3 * 4          → 14
sin(pi/2)          → 1.0
cos(0)             → 1.0
ln(e)              → 1.0
log(1000)          → 3.0
sqrt(16)           → 4.0
2^10               → 1024.0
factorial(5)       → 120.0
pow10(3)           → 1000.0
inv(4)             → 0.25
abs(-7)            → 7.0
sin(90)  [DEG]     → 1.0
asin(1)  [DEG]     → 90.0
```

**Graph expressions** (use `x` as the variable):
```
x
x^2
sin(x)
cos(x)
tan(x)
1/x          ← discontinuity at x=0 rendered as a gap
x^3 - 3*x
sqrt(abs(x))
```

## Notes

- **Security**: Expression evaluation uses Python's `ast` module to parse and walk the syntax tree — no `eval()` is used. Only whitelisted operators, functions, and constants are permitted.
- **State persistence**: Calculator state (mode, memory banks, graph window, function slots) is written to `calculator_state.json` and reloaded on server restart. Memory bank values are included in the persisted state.
- **Discontinuity handling**: The graph engine detects large vertical jumps and sign flips with high magnitude, splitting the plot into separate segments to avoid drawing phantom lines across asymptotes.
- **Multi-function graphing**: Up to six color-coded functions (Y1–Y6) can be plotted simultaneously. Each slot has an assigned color; the canvas auto-scales to the combined y-range.
- **Responsive layout**: The device shell scales from desktop (706 px wide) down to mobile, with the side panel and keypad reflowing to fit smaller screens.

## License

Use this project as a learning and demo starter. Add a formal license file if you plan to distribute it.
