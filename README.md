# Maze Pathfinding Studio

Maze Pathfinding Studio is a Flask-based web application for visualizing and comparing pathfinding algorithms on a 2D grid maze. The project supports both detailed single-algorithm tracing and side-by-side algorithm comparison in the browser.

## Main Features

### Visualize mode

- Run one algorithm at a time on the active grid
- Pause, continue, step forward, and step backward
- Drag the start node, end node, and checkpoint directly on the canvas
- Generate a basic maze or a weighted terrain map
- Edit walls and terrain interactively
- View live statistics for nodes visited, path length, path cost, and runtime

### Race mode

- Select multiple algorithms and run them on the same maze
- View each runner in its own mini-maze panel
- Compare final results in a summary table
- Inspect additional charts for nodes, path length, cost, time, iterations, and peak memory

## Implemented Algorithms

- Breadth-First Search
- Depth-First Search
- Uniform Cost Search
- A* Search
- Iterative Deepening DFS
- Bidirectional BFS
- Beam Search
- IDA* Search

## Weighted Terrain

The application supports three weighted terrain types:

- Grass: cost x2
- Swamp: cost x5
- Water: cost x10

These costs affect algorithms that use path cost rather than plain path length.

## Tech Stack

- Backend: Python, Flask
- Frontend: HTML, CSS, vanilla JavaScript
- Rendering: HTML canvas
- Communication: HTTP polling with JSON APIs

The application is designed as a single-user demo app with one in-process runtime state.

## Project Structure

```text
CSAI/
|-- app.py
|-- algorithms/
|-- core/
|-- static/
|-- templates/
|-- tests/
|-- Architecture.md
|-- README.md
`-- requirements.txt
```

## Installation and Running

### Main way to run the project

If Python and Flask are already installed on your machine, you can run the app directly:

```powershell
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5000`.

### Optional: use a virtual environment

This project can also run inside an optional virtual environment (`.venv`).

To create it:

```bash
python -m venv .venv
```

Important:

- `.\.venv\Scripts\Activate.ps1` does not create `.venv`
- it only activates an existing virtual environment in the current PowerShell session
- if `.venv` does not exist yet, create it first with `python -m venv .venv`

### Windows PowerShell with `.venv`

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

You can also skip activation and run the virtual-environment interpreter directly:

```powershell
.venv\Scripts\python app.py
```

### macOS / Linux with `.venv`

```bash
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Activating `.venv` is recommended, but it is not strictly required.

- Use `.venv\Scripts\Activate.ps1` when you want `python` and `pip` in the current shell to point to the virtual environment automatically.
- If `python app.py` already works for you, that means the Python interpreter you are currently using already has Flask installed.
- If you want to avoid activation, run the app with `.venv\Scripts\python app.py` to guarantee that the project uses the virtual environment.

The app runs in normal mode by default. If debug auto-reload is needed:

```bash
MAZE_DEBUG=1 python app.py
```

PowerShell:

```powershell
$env:MAZE_DEBUG = "1"
python app.py
```

## Default Settings

- Default grid size: `20 x 30`
- Grid size range: rows `5..50`, cols `5..80`
- Speed range: `1..999`
- Frontend polling interval: `40 ms`

## API Endpoints

The frontend uses three endpoints:

- `GET /api/state`
- `GET /api/race`
- `POST /api/action`

## Verification

Run the Python checks:

```bash
python -m compileall app.py algorithms core
python -m unittest discover -s tests -v
```

Optional JavaScript syntax check if Node.js is available:

```bash
node --check static/js/app.js
node --check static/js/visualize.js
node --check static/js/race.js
```

## Additional Documentation

- [Architecture.md](./Architecture.md)
