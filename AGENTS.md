# AGENTS.md

Hướng dẫn này áp dụng cho toàn bộ repo `lab01/`.

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

Repo này dùng virtual environment tại `.venv/`.

- Không cài package Python trực tiếp lên máy.
- Luôn bật `.venv` trước khi chạy app, cài package, hoặc verify.
- Khi `.venv` đã được bật, dùng `python` và `pip` là đủ.
- Nếu không muốn activate shell, dùng trực tiếp `.venv/bin/python` và `.venv/bin/pip`.

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

Mặc định local dev đang bật auto-reload. Nếu muốn tắt:

```bash
source .venv/bin/activate
MAZE_DEBUG=0 python app.py
```

PowerShell:

```powershell
$env:MAZE_DEBUG = "0"
python app.py
```

## Verify nhanh

- Kiểm tra cú pháp:

```bash
source .venv/bin/activate
python -m compileall app.py algorithms core
python -m unittest discover -s tests -v
```

- Nếu sửa UI hoặc API, nên chạy app và test tay ít nhất:
  - chọn thuật toán và `Run`
  - `Pause` / `Continue`
  - `Step` / `Step Back`
  - kéo thả start/end/checkpoint
  - `Basic Maze` và `Weighted Maze`
  - vào tab `Race` và chạy ít nhất 2 thuật toán

## Kiến trúc hiện tại

- `app.py`: Flask app mỏng, chỉ render template và expose API routes.
- `core/constants.py`: chỉ chứa constants như kích thước grid, giới hạn rows/cols, speed.
- `core/state.py`: singleton runtime state.
- `core/grid.py`: helper cho grid, terrain cost, reconstruct path, encode grid cho frontend, maze generation.
- `core/action_handlers.py`: parse/validate action payload và dispatch theo nhóm action.
- `core/runner.py`: orchestration cho visualize mode, checkpoint mode, race mode và background threads.
- `algorithms/*.py`: mỗi thuật toán là một generator.
- `templates/index.html`: khung DOM chính cho cả 2 tab.
- `static/js/app.js`: shell dùng chung, tab switching, helper `act()` và `fitCanvas()`.
- `static/js/visualize.js`: logic của tab `Visualize`, polling `/api/state`, render grid, interaction.
- `static/js/race.js`: logic của tab `Race`, polling `/api/race`, mini mazes và charts.
- `static/css/style.css`: shared styles.
- `static/css/visualize.css`: style riêng cho `Visualize`.
- `static/css/race.css`: style riêng cho `Race`.

Layout hiện tại của tab `Visualize`:

- header ribbon chỉ chứa controls chính
- khu làm việc chính chỉ còn `grid-area`
- sidebar phải chứa:
  - statistics
  - options
  - legend

Behavior UI quan trọng:

- grid luôn auto-fit
- không còn zoom/pan bằng chuột
- frontend dùng polling thay vì websocket

## Quy ước cực kỳ quan trọng

- Không dùng `global` để giữ state ứng dụng.
- Không chuyển state trở lại `core/constants.py`.
- Khi cần trạng thái runtime, luôn dùng:

```python
from core.state import state
```

- Nếu sửa constants hoặc giới hạn grid/speed, sửa trong `core/constants.py`.
- Nếu sửa logic action từ frontend, ưu tiên cập nhật trong `core/action_handlers.py` và `core/runner.py`.

## Contract của thuật toán

Mọi file trong `algorithms/` phải tuân thủ các rule sau:

- Hàm thuật toán phải là generator.
- Trong quá trình chạy, mỗi bước phải `yield (visited, frontier)`.
- Nên `yield` bản copy nếu structure có thể tiếp tục bị mutate.
- Thuật toán đọc input từ `state.start_cell`, `state.end_cell`, `state.walls`, `state.terrain`.
- Khi tìm thấy đường đi, trước khi `return` cần cập nhật đầy đủ:
  - `state.path_cells`
  - `state.stats`
  - `state.came_from`
  - `state.finished = True`
- Khi không tìm thấy đường:
  - vẫn phải cập nhật `state.stats`
  - vẫn nên set `state.came_from`
  - phải set `state.finished = True`

## Weighted terrain

- Terrain đang dùng các mã:
  - `8`: water
  - `9`: swamp
  - `10`: grass
- Chi phí terrain nằm trong `core/grid.py` qua `TERRAIN_COSTS`.
- Thuật toán có tính cost phải dùng `get_terrain_cost()` hoặc `path_cost()`, không hard-code `len(path) - 1`.

## Grid encoding contract với frontend

`core.grid.build_grid_array()` encode cell theo các mã sau. Nếu thay đổi mapping này, bắt buộc update frontend đồng bộ:

- `0`: empty
- `1`: wall
- `2`: start
- `3`: end
- `4`: visited
- `5`: frontier
- `6`: path
- `7`: checkpoint
- `8`: water
- `9`: swamp
- `10`: grass

## API contract

Frontend hiện dùng đúng 3 endpoint:

- `GET /api/state`
- `GET /api/race`
- `POST /api/action`

Shape chính của `/api/state`:

- `rows`, `cols`, `grid`
- `running`, `finished`, `paused`
- `step_ptr`
- `path_cells`
- `cur_alg`
- `speed`
- `set_mode`
- `stats`
- `checkpoint`

Shape chính của `/api/race`:

- `rows`, `cols`, `speed`
- `order`
- `running`, `paused`, `done`
- `step_ptr`
- `runners`
- `results`

Action strings hiện đang tồn tại:

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

- `GET /api/tree`
- `toggle_tree`
- `show_tree`
- `has_tree`

## Frontend editing notes

- Đừng đổi `id` trong `templates/index.html` một cách riêng lẻ; JS đang bind trực tiếp bằng `getElementById`.
- `visualize.js` assume shape của `/api/state` gồm: `rows`, `cols`, `grid`, `running`, `finished`, `paused`, `step_ptr`, `path_cells`, `cur_alg`, `speed`, `set_mode`, `stats`, `checkpoint`.
- `race.js` assume shape của `/api/race` gồm: `rows`, `cols`, `speed`, `order`, `running`, `paused`, `done`, `step_ptr`, `runners`, `results`.
- `visualize.js` poll `/api/state` và `race.js` poll `/api/race`, hiện tại khoảng mỗi `40ms`.

## Khi sửa runner hoặc state

- `core/runner.py` là file nhạy cảm vì nó nối thread loop, checkpoint mode, race mode và state serialization.
- `core/action_handlers.py` là file nhạy vì nó giữ contract action string, validation và error response.
- Step mode phụ thuộc `state.step_history` và `state.step_ptr`.
- Race mode dùng shared singleton `state`; đừng thêm logic làm rò trạng thái giữa các runner.
- Nếu thay đổi cách thuật toán kết thúc, cần kiểm tra lại `Visualize`, `Step`, `Checkpoint`, `Race`.

## Khi thêm thuật toán mới

1. Tạo file mới trong `algorithms/`.
2. Implement theo generator contract ở trên.
3. Import thuật toán trong `algorithms/__init__.py`.
4. Thêm entry vào registry.
5. Chạy app và test cả visualize mode lẫn race mode.

## Ưu tiên khi bảo trì

- Giữ nguyên contract giữa backend và frontend.
- Thay đổi nhỏ, đúng chỗ, tránh refactor rộng nếu không cần.
- Nếu docs cũ mâu thuẫn với hành vi mới, cập nhật docs theo code hiện tại.
