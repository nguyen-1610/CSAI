# Architecture

## Tổng quan

Project hiện tại là một web app Flask để visualize và so sánh các thuật toán tìm đường trên grid.

Ứng dụng có 2 chế độ chính:

- `Visualize`: chạy một thuật toán, hỗ trợ pause, continue, step, step-back, checkpoint, weighted terrain, tree view.
- `Race`: chạy nhiều thuật toán song song để so sánh nodes/path/cost/time.

## Cấu trúc thư mục hiện tại

```text
lab01/
├── app.py
├── core/
│   ├── __init__.py
│   ├── constants.py
│   ├── state.py
│   ├── grid.py
│   ├── runner.py
│   └── tree.py
├── algorithms/
│   ├── __init__.py
│   ├── bfs.py
│   ├── dfs.py
│   ├── ucs.py
│   ├── astar.py
│   ├── iddfs.py
│   ├── bidirectional.py
│   ├── beam.py
│   └── idastar.py
├── templates/
│   └── index.html
├── static/
│   ├── css/
│   │   ├── style.css
│   │   ├── visualize.css
│   │   └── race.css
│   └── js/
│       ├── app.js
│       ├── visualize.js
│       └── race.js
├── AGENTS.md
└── Architecture.md
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

core/tree.py
  └── import core.state

core/runner.py
  └── import core.constants, core.state, core.grid, algorithms

app.py
  └── import core.runner, core.tree, algorithms

templates/index.html
  └── load static JS/CSS

static/js/app.js
  └── shell chung cho frontend

static/js/visualize.js
  └── dùng /api/state, /api/tree

static/js/race.js
  └── dùng /api/race
```

## Backend

### `app.py`

File Flask entrypoint, hiện khá mỏng:

- render `index.html`
- expose:
  - `GET /api/state`
  - `GET /api/race`
  - `GET /api/tree`
  - `POST /api/action`
- bật auto-reload trong local dev qua `MAZE_DEBUG`

### `core/constants.py`

Chỉ giữ constants:

- default rows/cols
- directions
- speed limits
- grid size limits

Không giữ runtime state nữa.

### `core/state.py`

Chứa singleton runtime state `state`.

Các nhóm dữ liệu chính:

- grid state: `rows`, `cols`, `walls`, `terrain`
- markers: `start_cell`, `end_cell`, `checkpoint_cell`
- search state: `vis_cells`, `front_cells`, `path_cells`, `came_from`
- execution state: `running`, `paused`, `finished`, `alg_gen`, `speed`
- step state: `step_history`, `step_ptr`

### `core/grid.py`

Chứa:

- helper grid: `in_bounds`, `get_neighbors`, `heuristic`, `reconstruct_path`, `next_id`
- terrain cost helpers: `get_terrain_cost`, `path_cost`
- encode grid cho frontend: `build_grid_array`
- maze / terrain generation

### `core/tree.py`

Chuyển `state.came_from` + `state.path_cells` thành dữ liệu tree để frontend vẽ.

Output chính:

- `positions`
- `edges`
- `bounds`
- `start`, `end`
- `shown`, `total`
- `algo`

### `core/runner.py`

Đây là orchestration layer chính.

Chứa:

- `handle_action()` cho toàn bộ action từ frontend
- action của visualize mode
- action của race mode
- checkpoint wrapper
- algorithm thread
- race thread
- các hàm serialize state cho `/api/state` và `/api/race`

Nói ngắn gọn: nếu frontend bấm nút gì, gần như cuối cùng sẽ đi qua `core/runner.py`.

## Algorithms

Mỗi file trong `algorithms/` là một generator algorithm.

Contract hiện tại:

- đọc input từ `state`
- mỗi bước `yield (visited, frontier)`
- khi kết thúc phải cập nhật:
  - `state.path_cells`
  - `state.stats`
  - `state.came_from`
  - `state.finished = True`

Registry nằm trong `algorithms/__init__.py`.

## Frontend

### `templates/index.html`

Một page duy nhất, gồm 2 tab:

- `Visualize`
- `Race`

Layout `Visualize` hiện tại:

- header ribbon cho controls
- vùng làm việc chính cho grid/tree
- sidebar bên phải cho:
  - statistics
  - nút `Show Tree`
  - legend

### `static/js/app.js`

Shell chung:

- lưu `App.state`
- helper DOM / API
- tab switching
- bootstrap frontend

### `static/js/visualize.js`

Chứa toàn bộ logic của tab `Visualize`:

- dropdown algorithm
- buttons: run, step, clear, maze, reset, speed, grid size, checkpoint, terrain
- polling `/api/state`
- polling `/api/tree`
- render grid canvas
- render tree canvas
- drag start/end/checkpoint
- path animation

Behavior UI quan trọng hiện tại:

- grid luôn auto-fit, không còn zoom/pan bằng chuột
- khi mở tree, sidebar phải tự ẩn để giao diện thoáng hơn
- khi mở tree, view tự focus vào root trước

### `static/js/race.js`

Chứa logic của tab `Race`:

- chọn algorithm để race
- polling `/api/race`
- render mini mazes
- render charts

### CSS

- `style.css`: base styles dùng chung
- `visualize.css`: layout/styling riêng cho `Visualize`
- `race.css`: layout/styling riêng cho `Race`

## API contract

### `GET /api/state`

Trả về state của tab `Visualize`, gồm các field chính:

- `rows`, `cols`, `grid`
- `running`, `paused`, `finished`
- `step_ptr`
- `path_cells`
- `cur_alg`
- `speed`
- `stats`
- `has_tree`, `show_tree`
- `checkpoint`

### `GET /api/race`

Trả về state của tab `Race`, gồm:

- `order`
- `running`, `paused`, `done`
- `step_ptr`
- `runners`
- `results`

### `GET /api/tree`

Trả về dữ liệu tree để render khi `show_tree = true`.

### `POST /api/action`

Frontend gửi action string vào đây. Một số action chính:

- visualize:
  - `run`, `step`, `step_back`, `cancel_algo`
  - `clear`, `reset`, `maze`, `weighted_maze`
  - `set_start`, `set_end`, `set_checkpoint`, `remove_checkpoint`
  - `grid_cell`, `set_terrain`
  - `speed`, `change_grid`, `set_grid`
  - `toggle_tree`
- race:
  - `race_toggle`, `race_start`, `race_cancel`
  - `race_step`, `race_step_back`, `race_stop`

## Cách chạy

### Development

```bash
pip install -r requirements.txt
python3 app.py
```

Mặc định local dev đang bật auto-reload.

Nếu muốn tắt:

```bash
MAZE_DEBUG=0 python3 app.py
```

### URL

```text
http://localhost:5000
```

## Verify nhanh sau khi sửa

### Python syntax

```bash
python3 -m py_compile app.py core/*.py algorithms/*.py
```

### JS syntax

```bash
node --check static/js/app.js
node --check static/js/visualize.js
node --check static/js/race.js
```

### Manual smoke test

- Visualize:
  - chọn thuật toán và `Run`
  - `Pause` / `Continue`
  - `Step` / `Step Back`
  - kéo start/end/checkpoint
  - `Generate Maze`
  - `Weighted Maze`
  - `Show Tree`
- Race:
  - chọn ít nhất 2 thuật toán
  - `Race`
  - xem panel + chart

## Ghi chú bảo trì

- Nếu đổi `id` trong `index.html`, phải kiểm tra lại JS bind tương ứng.
- Nếu đổi mapping cell type trong backend, phải sửa đồng bộ frontend.
- Nếu đổi format `/api/state`, `/api/race`, `/api/tree`, phải cập nhật frontend.
- `core/runner.py` là file nhạy cảm nhất; thay đổi ở đây dễ ảnh hưởng cả visualize, checkpoint, race và tree.
