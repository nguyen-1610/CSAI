# Architecture

## Tổng quan

Project hiện tại là một web app Flask để visualize và so sánh các thuật toán tìm đường trên grid.

Ứng dụng có 2 mode chính:

- `Visualize`: chạy 1 thuật toán, hỗ trợ pause, continue, step, step-back, checkpoint, weighted terrain.
- `Race`: chạy nhiều thuật toán song song để so sánh kết quả.

Lưu ý quan trọng:

- Tree view không còn nằm trong code hiện tại.
- Tab `Visualize` luôn auto-fit grid, không còn zoom/pan bằng chuột.
- App là singleton runtime trong một process, phù hợp demo local hoặc deploy nhẹ.

## Cấu trúc thư mục hiện tại

```text
lab01/
├── app.py
├── core/
│   ├── __init__.py
│   ├── action_handlers.py
│   ├── constants.py
│   ├── grid.py
│   ├── runner.py
│   └── state.py
├── algorithms/
│   ├── __init__.py
│   ├── _contract.py
│   ├── astar.py
│   ├── beam.py
│   ├── bfs.py
│   ├── bidirectional.py
│   ├── dfs.py
│   ├── idastar.py
│   ├── iddfs.py
│   └── ucs.py
├── static/
│   ├── css/
│   │   ├── race.css
│   │   ├── style.css
│   │   └── visualize.css
│   └── js/
│       ├── app.js
│       ├── race.js
│       └── visualize.js
├── templates/
│   └── index.html
├── tests/
│   ├── test_algorithm_contract.py
│   └── test_api_baseline.py
├── AGENTS.md
├── Architecture.md
└── README.md
```

## Dependency graph

```text
core/constants.py
  └── chỉ chứa constants / limits

core/state.py
  └── runtime singleton state

core/grid.py
  └── import core.constants, core.state

algorithms/*.py
  └── import core.state, core.grid

core/action_handlers.py
  └── parse payload, validate action, mutate state

core/runner.py
  └── orchestration cho visualize/race, thread loop, state serialization

app.py
  └── import core.runner, algorithms

templates/index.html
  └── load static JS/CSS

static/js/app.js
  └── shell chung, tab switching, helper act()/fitCanvas()

static/js/visualize.js
  └── dùng GET /api/state + POST /api/action

static/js/race.js
  └── dùng GET /api/race + POST /api/action
```

## Backend

### `app.py`

File Flask entrypoint, khá mỏng:

- render `index.html`
- expose đúng 3 endpoint:
  - `GET /api/state`
  - `GET /api/race`
  - `POST /api/action`
- bật auto-reload trong local dev qua `MAZE_DEBUG`

### `core/constants.py`

Chỉ giữ constants:

- default rows/cols
- directions
- speed limits
- grid size limits

Không giữ runtime state.

### `core/state.py`

Chứa singleton runtime state `state`.

Các nhóm dữ liệu chính:

- grid state: `rows`, `cols`, `walls`, `terrain`
- markers: `start_cell`, `end_cell`, `checkpoint_cell`
- search state: `vis_cells`, `front_cells`, `path_cells`, `came_from`
- execution state: `running`, `paused`, `finished`, `alg_gen`, `speed`
- step state: `step_history`, `step_ptr`, `step_history_gen_base`
- race state: `state.race`
- snapshot state khi đổi tab: `viz_snapshot`

Toàn bộ runtime state đang nằm trong một singleton process-wide.

### `core/grid.py`

Chứa:

- helper grid: `in_bounds`, `get_neighbors`, `heuristic`, `reconstruct_path`, `next_id`
- terrain cost helpers: `get_terrain_cost`, `path_cost`
- encode grid cho frontend: `build_grid_array`
- maze / terrain generation

### `core/action_handlers.py`

Đây là nơi parse và validate payload từ `POST /api/action`.

Vai trò chính:

- chia action theo nhóm `visualize`, `race`, `system`
- chuẩn hóa error response
- validate kiểu dữ liệu và giới hạn
- gom action strings ở một chỗ

### `core/runner.py`

Đây là orchestration layer chính.

Chứa:

- state serializer cho `/api/state` và `/api/race`
- background loop cho `Visualize`
- background loop cho `Race`
- checkpoint wrapper
- race checkpoint wrapper
- helper reset runtime cho test

Nói ngắn gọn:

- `core/action_handlers.py` quyết định action hợp lệ hay không
- `core/runner.py` điều phối việc chạy thật

## Algorithms

Mỗi file trong `algorithms/` là một generator algorithm.

Contract hiện tại:

- đọc input từ `state.start_cell`, `state.end_cell`, `state.walls`, `state.terrain`
- mỗi bước `yield (visited, frontier)`
- khi thành công phải cập nhật:
  - `state.path_cells`
  - `state.stats`
  - `state.came_from`
  - `state.finished = True`
- khi thất bại vẫn phải cập nhật:
  - `state.stats`
  - `state.came_from`
  - `state.finished = True`

Helper finalize chung hiện nằm trong `algorithms/_contract.py`.

## Frontend

### `templates/index.html`

Một page duy nhất, gồm 2 tab:

- `Visualize`
- `Race`

Layout `Visualize` hiện tại:

- header ribbon chỉ chứa controls chính
- khu làm việc chính chỉ còn `grid-area`
- sidebar phải chứa:
  - statistics
  - options
  - legend

### `static/js/app.js`

Shell chung:

- lưu `App.state`
- helper DOM / API
- tab switching
- bootstrap frontend

Frontend dùng command/query split:

- query qua `GET /api/state` và `GET /api/race`
- command qua `POST /api/action`

### `static/js/visualize.js`

Chứa toàn bộ logic của tab `Visualize`:

- dropdown algorithm
- buttons: run, step, clear, maze, reset, speed, grid size, checkpoint, terrain
- polling `/api/state`
- render grid canvas
- drag start/end/checkpoint
- path animation

Behavior UI quan trọng hiện tại:

- grid luôn auto-fit
- không còn zoom/pan bằng chuột
- khi finished vẫn giữ layout hiện tại, chỉ đổi status và stats

### `static/js/race.js`

Chứa logic của tab `Race`:

- chọn algorithm để race
- polling `/api/race`
- render mini mazes
- render charts

## API contract

### `GET /api/state`

Trả về state của tab `Visualize` với shape hiện tại:

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

Trả về state của tab `Race` với shape hiện tại:

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

Khi race đã khởi tạo, mỗi runner có dạng:

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

Frontend gửi action string vào đây.

Các action đang tồn tại trong code:

- visualize
  - `select_algo`
  - `run`, `step`, `step_back`, `cancel_algo`
  - `clear`, `reset`, `maze`, `weighted_maze`
  - `set_start`, `set_end`, `set_checkpoint`, `remove_checkpoint`
  - `grid_cell`, `set_terrain`, `clear_terrain`
  - `speed`, `set_mode`, `change_grid`, `set_grid`
- race
  - `race_toggle`, `race_start`, `race_cancel`
  - `race_step`, `race_step_back`, `race_stop`
- system
  - `switch_tab`

Không còn:

- `GET /api/tree`
- `toggle_tree`
- `show_tree`
- `has_tree`

## Polling model

Frontend hiện poll dữ liệu thay vì giữ websocket/session sync:

- `visualize.js` poll `/api/state` mỗi `40ms`
- `race.js` poll `/api/race` mỗi `40ms`
- action mutation luôn đi qua `POST /api/action`

Vì app là single-user demo, mô hình này đủ đơn giản và dễ maintain.

## Cách chạy

### macOS / Linux

```bash
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Hoặc:

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Hoặc:

```powershell
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python app.py
```

## Verify nhanh sau khi sửa

### Python

```bash
source .venv/bin/activate
python -m compileall app.py algorithms core
python -m unittest discover -s tests -v
```

### JavaScript

```bash
node --check static/js/app.js
node --check static/js/visualize.js
node --check static/js/race.js
```

### Smoke test tay

- `Visualize`
  - `Run`
  - `Pause` / `Continue`
  - `Step` / `Step Back`
  - kéo thả start/end/checkpoint
  - `Basic Maze` và `Weighted Maze`
- `Race`
  - chọn ít nhất 2 thuật toán
  - `Race`
  - `Pause` / `Continue`
  - `Step` / `Step Back`
  - xem panel và chart
