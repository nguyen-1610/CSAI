# Architecture

## Overview

Maze Pathfinding Studio is a browser-based pathfinding visualizer built with Flask and vanilla JavaScript. It supports two operating modes:

- `Visualize`: inspect one algorithm step by step on the main grid
- `Race`: run multiple algorithms on the same grid and compare their outcomes

The application is intentionally implemented as a single-user, single-process demo. Runtime state is stored in memory and shared by the Flask process.

## Technology Stack

- Python + Flask
- HTML + CSS + vanilla JavaScript
- Canvas-based rendering for the main grid, mini-grids, and charts
- Polling-based frontend/backend communication

There is no frontend build step and no websocket layer.

## Directory Layout

```text
CSAI/
|-- app.py
|-- algorithms/
|   |-- __init__.py
|   |-- _contract.py
|   |-- astar.py
|   |-- beam.py
|   |-- bfs.py
|   |-- bidirectional.py
|   |-- dfs.py
|   |-- idastar.py
|   |-- iddfs.py
|   `-- ucs.py
|-- core/
|   |-- __init__.py
|   |-- action_handlers.py
|   |-- constants.py
|   |-- grid.py
|   |-- runner.py
|   `-- state.py
|-- static/
|   |-- css/
|   |-- js/
|-- templates/
|   `-- index.html
|-- tests/
|   |-- test_algorithm_contract.py
|   `-- test_api_baseline.py
|-- Architecture.md
|-- README.md
`-- requirements.txt
```

## High-Level Runtime Design

### `app.py`

`app.py` is the Flask entry point. It:

- serves `templates/index.html`
- exposes three HTTP endpoints
- starts the app on port `5000`
- runs in non-debug mode by default

Debug auto-reload can be enabled explicitly with `MAZE_DEBUG=1`.

### `core/state.py`

`core/state.py` defines the singleton runtime object `state`. It stores:

- grid dimensions
- walls and weighted terrain
- start, end, and checkpoint cells
- visualization progress
- statistics and reconstructed paths
- race mode state
- thread references and synchronization primitives

This file is the main source of mutable runtime state.

### `core/constants.py`

This module stores configuration values such as:

- default grid size: `20 x 30`
- default speed: `20`
- speed limit: `1..999`
- grid bounds: rows `5..50`, cols `5..80`
- loop timing and history limits

### `core/grid.py`

This module provides:

- neighbor lookup
- Manhattan heuristic
- path reconstruction
- terrain cost helpers
- grid encoding for the frontend
- maze generation
- weighted terrain generation

Terrain encoding and costs are:

- `8`: water, cost `10`
- `9`: swamp, cost `5`
- `10`: grass, cost `2`

Cells with no terrain have cost `1`.

### `core/action_handlers.py`

This module validates and dispatches all `POST /api/action` requests. It handles:

- algorithm selection
- run, pause, continue, step, and step-back actions
- wall and terrain editing
- checkpoint placement and removal
- grid resizing
- race selection and race control
- tab switching

It is the primary contract layer between the frontend and the runtime.

### `core/runner.py`

This module coordinates execution. It is responsible for:

- serializing `/api/state` and `/api/race`
- starting visualize-mode background threads
- starting race-mode background threads
- maintaining step history
- handling checkpoint wrappers
- building race result summaries
- resetting runtime state for tests

## Algorithms

The algorithm registry is defined in `algorithms/__init__.py`. The project currently includes:

- Breadth-First Search
- Depth-First Search
- Uniform Cost Search
- A* Search
- Iterative Deepening DFS
- Bidirectional BFS
- Beam Search
- IDA* Search

Each algorithm is implemented as a generator and yields `(visited, frontier)` while it runs.

When an algorithm finishes, it updates:

- `state.path_cells`
- `state.stats`
- `state.came_from`
- `state.finished`

This contract is used by both the UI and the automated tests.

## Frontend Structure

### `templates/index.html`

The frontend uses one HTML page with two tabs:

- `Visualize`
- `Race`

### `static/js/app.js`

Shared frontend bootstrap:

- stores shared UI state
- posts actions to the backend
- manages tab switching
- configures polling timing

Default polling interval is `40 ms`.

### `static/js/visualize.js`

Controls the single-algorithm mode:

- canvas rendering for the main maze
- drag interactions for start, end, checkpoint, walls, and terrain
- algorithm selection
- speed and grid controls
- step-by-step execution
- live polling from `/api/state`

### `static/js/race.js`

Controls the comparison mode:

- algorithm selection for the race
- mini-maze rendering for each runner
- race execution controls
- result table generation
- chart rendering
- live polling from `/api/race`

## Visualize Mode Behavior

Key behavior in the final implementation:

- the main grid always auto-fits its container
- there is no mouse-based zoom or pan
- start, end, and checkpoint markers can be dragged directly
- walls can be painted with left drag and erased with right drag
- weighted terrain can be painted on valid cells
- unfinished visualize sessions are cleared when switching to `Race`
- finished visualize sessions are preserved when switching tabs

## Race Mode Behavior

Race mode allows up to `8` algorithms at the same time.

Each race runner uses the same grid, walls, terrain, and checkpoint configuration. When the race finishes, the UI shows:

- per-runner mini-grid playback
- a summary result matrix
- charts for nodes, path length, cost, time, iterations, and peak memory

## API Contract

### `GET /api/state`

Returns the visualize-mode state:

```json
{
  "rows": 20,
  "cols": 30,
  "grid": [],
  "running": false,
  "finished": false,
  "paused": false,
  "step_ptr": -1,
  "path_cells": [],
  "cur_alg": 0,
  "speed": 20,
  "set_mode": null,
  "stats": {
    "nodes": 0,
    "path": 0,
    "cost": 0,
    "time": 0.0,
    "found": null,
    "iterations": 1,
    "peak_memory": 0
  },
  "checkpoint": null
}
```

### `GET /api/race`

Returns the race-mode state:

```json
{
  "rows": 20,
  "cols": 30,
  "speed": 20,
  "order": [],
  "running": false,
  "paused": false,
  "done": false,
  "step_ptr": -1,
  "runners": {},
  "results": null
}
```

### `POST /api/action`

Supported action strings:

- `select_algo`
- `run`
- `step`
- `step_back`
- `cancel_algo`
- `clear`
- `reset`
- `maze`
- `weighted_maze`
- `set_start`
- `set_end`
- `set_checkpoint`
- `remove_checkpoint`
- `grid_cell`
- `set_terrain`
- `clear_terrain`
- `speed`
- `set_mode`
- `change_grid`
- `set_grid`
- `race_toggle`
- `race_start`
- `race_cancel`
- `race_step`
- `race_step_back`
- `race_stop`
- `switch_tab`

## Grid Encoding Used by the Frontend

The flat grid array sent to the frontend uses these integer codes:

- `0`: empty
- `1`: wall
- `2`: start
- `3`: end
- `4`: visited
- `5`: frontier
- `6`: final path
- `7`: checkpoint
- `8`: water
- `9`: swamp
- `10`: grass

## Testing

The repository includes two test files:

- `tests/test_api_baseline.py`
- `tests/test_algorithm_contract.py`

These tests validate:

- API response shapes
- action validation behavior
- visualize and race execution flow
- algorithm contract compliance
- checkpoint wrapper behavior
