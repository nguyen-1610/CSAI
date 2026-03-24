# CLAUDE.md

Nội dung file này được giữ đồng bộ với `AGENTS.md` để tránh docs lệch nhau trong quá trình maintain.

## Mục tiêu project

- Visualizer cho các thuật toán tìm đường trong mê cung/grid.
- Có 2 mode chính:
  - `Visualize`: chạy 1 thuật toán, hỗ trợ pause, step, step-back, checkpoint, weighted terrain.
  - `Race`: chạy nhiều thuật toán song song để so sánh kết quả.

Lưu ý:

- Tree view không còn nằm trong code hiện tại.
- Grid ở tab `Visualize` luôn auto-fit, không còn zoom/pan bằng chuột.
- App là demo single-user với runtime singleton trong một process.

## Cách chạy

Repo dùng virtual environment tại `.venv/`.

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

Mở `http://localhost:5000`.

## Verify nhanh

```bash
source .venv/bin/activate
python -m compileall app.py algorithms core
python -m unittest discover -s tests -v
node --check static/js/app.js
node --check static/js/visualize.js
node --check static/js/race.js
```

## Kiến trúc hiện tại

- `app.py`: Flask app mỏng, render template và expose API routes.
- `core/action_handlers.py`: parse/validate action payload và dispatch theo nhóm action.
- `core/runner.py`: orchestration cho visualize/race và background threads.
- `core/state.py`: singleton runtime state.
- `core/grid.py`: helper grid, terrain cost, build grid array, maze generation.
- `static/js/visualize.js`: poll `/api/state`, render grid, handle interaction.
- `static/js/race.js`: poll `/api/race`, render mini mazes và charts.

## API contract hiện tại

Frontend hiện dùng đúng 3 endpoint:

- `GET /api/state`
- `GET /api/race`
- `POST /api/action`

`/api/state` gồm:

- `rows`, `cols`, `grid`
- `running`, `finished`, `paused`
- `step_ptr`
- `path_cells`
- `cur_alg`
- `speed`
- `set_mode`
- `stats`
- `checkpoint`

`/api/race` gồm:

- `rows`, `cols`, `speed`
- `order`
- `running`, `paused`, `done`
- `step_ptr`
- `runners`
- `results`

Action strings hiện có:

- visualize:
  - `select_algo`
  - `run`, `step`, `step_back`, `cancel_algo`
  - `clear`, `reset`, `maze`, `weighted_maze`
  - `set_start`, `set_end`, `set_checkpoint`, `remove_checkpoint`
  - `grid_cell`, `set_terrain`, `clear_terrain`
  - `speed`, `set_mode`, `change_grid`, `set_grid`
- race:
  - `race_toggle`, `race_start`, `race_cancel`, `race_step`, `race_step_back`, `race_stop`
- system:
  - `switch_tab`

Không còn:

- `/api/tree`
- `toggle_tree`
- `show_tree`
- `has_tree`

## Frontend behavior quan trọng

- `visualize.js` poll `/api/state` khoảng mỗi `40ms`
- `race.js` poll `/api/race` khoảng mỗi `40ms`
- tab switch gửi command `switch_tab` qua `/api/action`
- grid ở `Visualize` luôn auto-fit

## Weighted terrain

- `8`: water
- `9`: swamp
- `10`: grass

Thuật toán có tính cost phải dùng helper trong `core/grid.py`, không hard-code `len(path) - 1`.
