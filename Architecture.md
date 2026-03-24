# Architecture

## Tong quan

Project hien tai la mot web app Flask de visualize va so sanh cac thuat toan tim duong tren grid.

Ung dung co 2 mode chinh:

- `Visualize`: chay 1 thuat toan, ho tro pause, continue, step, step-back, checkpoint, weighted terrain
- `Race`: chay nhieu thuat toan song song de so sanh ket qua

Luu y:

- tree view da bi loai bo khoi code hien tai
- tab `Visualize` luon auto-fit grid, khong con zoom/pan bang chuot
- app la singleton runtime trong mot process, phu hop demo single-user
- frontend hien tai van la HTML/CSS/JavaScript thuan, khong co React/Vite/build step

## Stack

- Python + Flask
- HTML + CSS + JavaScript thuan
- Canvas API thuan cho grid va chart render custom
- polling thay vi websocket

## Cau truc thu muc

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
|   |   |-- race.css
|   |   |-- style.css
|   |   `-- visualize.css
|   `-- js/
|       |-- app.js
|       |-- race.js
|       `-- visualize.js
|-- templates/
|   `-- index.html
|-- tests/
|   |-- test_algorithm_contract.py
|   `-- test_api_baseline.py
`-- requirements.txt
```

## Backend

### `app.py`

Flask entrypoint rat mong:

- render `templates/index.html`
- expose 3 endpoint:
  - `GET /api/state`
  - `GET /api/race`
  - `POST /api/action`
- bat/tat auto-reload bang `MAZE_DEBUG`

### `core/state.py`

Chua singleton runtime state `state`.

Nhom du lieu chinh:

- grid state: `rows`, `cols`, `walls`, `terrain`
- markers: `start_cell`, `end_cell`, `checkpoint_cell`
- search state: `vis_cells`, `front_cells`, `path_cells`, `came_from`
- execution state: `running`, `paused`, `finished`, `alg_gen`, `speed`
- step state: `step_history`, `step_ptr`
- race state: `state.race`

### `core/grid.py`

Chua:

- helper grid
- terrain cost helpers
- encode grid cho frontend bang `build_grid_array()`
- maze generation

### `core/action_handlers.py`

Day la noi parse va validate payload tu `POST /api/action`.

Vai tro:

- chia action theo nhom `visualize`, `race`, `system`
- chuan hoa validate input
- chuan hoa error response
- giu registry action string

### `core/runner.py`

Day la orchestration layer chinh.

No chua:

- state serializer cho `/api/state` va `/api/race`
- background loop cho `Visualize`
- background loop cho `Race`
- checkpoint wrappers
- reset helper cho test

## Algorithms

Moi file trong `algorithms/` la mot generator.

Contract hien tai:

- doc input tu `state.start_cell`, `state.end_cell`, `state.walls`, `state.terrain`
- moi buoc `yield (visited, frontier)`
- khi thanh cong phai cap nhat:
  - `state.path_cells`
  - `state.stats`
  - `state.came_from`
  - `state.finished = True`
- khi that bai van phai cap nhat:
  - `state.stats`
  - `state.came_from`
  - `state.finished = True`

## Frontend

### `templates/index.html`

Mot page duy nhat, gom 2 tab:

- `Visualize`
- `Race`

### `static/js/app.js`

Shell dung chung:

- giu `App.state`
- helper DOM va API
- tab switching
- bootstrap frontend

### `static/js/visualize.js`

Logic cua tab `Visualize`:

- algorithm dropdown
- run/step/speed/grid controls
- polling `/api/state`
- render main canvas
- drag start/end/checkpoint
- animate visited/frontier/path

### `static/js/race.js`

Logic cua tab `Race`:

- chon algorithms de race
- polling `/api/race`
- render mini mazes
- render comparison charts

## API contract

### `GET /api/state`

Shape chinh:

```json
{
  "rows": 30,
  "cols": 40,
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

Shape chinh:

```json
{
  "rows": 30,
  "cols": 40,
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

Khi race da khoi tao, moi runner co du lieu theo huong:

```json
{
  "name": "Breadth-First Search",
  "done": false,
  "grid": [],
  "path": [],
  "stats": null
}
```

### `POST /api/action`

Action strings hien co:

- visualize
  - `select_algo`
  - `run`, `step`, `step_back`, `cancel_algo`
  - `clear`, `reset`, `maze`, `weighted_maze`
  - `set_start`, `set_end`, `set_checkpoint`, `remove_checkpoint`
  - `grid_cell`, `set_terrain`, `clear_terrain`
  - `speed`, `set_mode`, `change_grid`, `set_grid`
- race
  - `race_toggle`, `race_start`, `race_cancel`, `race_step`, `race_step_back`, `race_stop`
- system
  - `switch_tab`

Khong con:

- `GET /api/tree`
- `toggle_tree`
- `show_tree`
- `has_tree`

## Runtime model

- frontend poll `/api/state` va `/api/race` khoang moi `40ms`
- moi mutation deu di qua `POST /api/action`
- `Visualize` va `Race` cung doc/ghi tren shared singleton state
- app duoc thiet ke cho demo single-user, khong phai multi-user server

## Dev notes

- `.venv/` la local virtual environment, khong duoc commit
- neu repo moi clone chua co `.venv`, tao bang `python -m venv .venv`
- frontend hien tai khong can `npm install` hay build step
