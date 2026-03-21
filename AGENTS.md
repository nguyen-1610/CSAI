# AGENTS.md

Hướng dẫn này áp dụng cho toàn bộ repo `lab01/`.

## Mục tiêu project

- Visualizer cho các thuật toán tìm đường trong mê cung/grid.
- Có 2 mode chính:
  - `Visualize`: chạy 1 thuật toán, hỗ trợ pause, step, step-back, checkpoint, weighted terrain, tree view.
  - `Race`: chạy nhiều thuật toán song song để so sánh kết quả.

## Cách chạy

Repo này dùng virtual environment tại `.venv/`.

- Không cài package Python trực tiếp lên máy.
- Luôn bật `.venv` trước khi chạy app, cài package, hoặc verify.
- Khi `.venv` đã được bật, dùng `python` và `pip` là đủ; không cần `python3`.
- Nếu không muốn activate shell, dùng trực tiếp `.venv/bin/python` và `.venv/bin/pip`.

```bash
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Mở `http://localhost:5000`.

Mặc định local dev đang bật auto-reload. Nếu muốn tắt:

```bash
source .venv/bin/activate
MAZE_DEBUG=0 python app.py
```

Hoặc chạy không cần activate:

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

## Verify nhanh

- Kiểm tra cú pháp:

```bash
source .venv/bin/activate
python -m compileall app.py algorithms core
```

- Nếu sửa UI hoặc API, nên chạy app và test tay ít nhất:
  - chọn thuật toán và `Run`
  - `Pause` / `Continue`
  - `Step` / `Step Back`
  - kéo thả start/end/checkpoint
  - `Generate Maze` và `Weighted Maze`
  - bật `Show Tree`
  - vào tab `Race` và chạy ít nhất 2 thuật toán

## Kiến trúc hiện tại

- `app.py`: Flask app rất mỏng, chỉ render template và expose API routes.
- `core/constants.py`: chỉ chứa constants như kích thước grid, giới hạn rows/cols, speed.
- `core/state.py`: singleton runtime state. Đây là nơi giữ toàn bộ trạng thái hiện tại của app.
- `core/grid.py`: helper cho grid, terrain cost, reconstruct path, encode grid cho frontend, maze generation.
- `core/runner.py`: action dispatcher chính, orchestration cho visualize mode, checkpoint mode, race mode và background threads.
- `core/tree.py`: dựng dữ liệu cây khám phá để frontend render.
- `algorithms/*.py`: mỗi thuật toán là một generator.
- `templates/index.html`: khung DOM chính cho cả 2 tab.
- `static/js/app.js`: shell dùng chung, tab switching, helper `act()` và `fitCanvas()`.
- `static/js/visualize.js`: logic của tab Visualize, polling `/api/state`, render grid/tree, interaction.
- `static/js/race.js`: logic của tab Race, polling `/api/race`, mini mazes và charts.
- `static/css/style.css`: shared styles.
- `static/css/visualize.css`: style riêng cho Visualize.
- `static/css/race.css`: style riêng cho Race.

Layout hiện tại của tab `Visualize`:

- header ribbon chỉ chứa controls chính
- khu làm việc chính chứa `grid-area` và `tree-area`
- sidebar phải chứa:
  - statistics
  - nút `Show Tree`
  - legend

Behavior UI quan trọng:

- grid luôn auto-fit, không còn zoom/pan bằng chuột
- khi mở tree, sidebar phải sẽ tự ẩn để nhường chỗ
- khi mở tree, view sẽ focus vào root trước
- tree vẫn hỗ trợ zoom/pan riêng

## Quy ước cực kỳ quan trọng

- Không dùng `global` để giữ state ứng dụng.
- Không chuyển state trở lại `core/constants.py`.
- Khi cần trạng thái runtime, luôn dùng:

```python
from core.state import state
```

- Nếu sửa constants hoặc giới hạn grid/speed, sửa trong `core/constants.py`.
- Nếu sửa logic action từ frontend, ưu tiên cập nhật trong `core/runner.py`.

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

Frontend đang hard-code các endpoint sau:

- `GET /api/state`
- `GET /api/race`
- `GET /api/tree`
- `POST /api/action`

Frontend cũng hard-code nhiều action string trong `handle_action()`, ví dụ:

- `run`, `step`, `step_back`, `cancel_algo`
- `clear`, `reset`, `maze`, `weighted_maze`
- `set_start`, `set_end`, `set_checkpoint`, `remove_checkpoint`
- `grid_cell`, `set_terrain`
- `speed`, `change_grid`, `set_grid`
- `toggle_tree`
- `race_toggle`, `race_start`, `race_cancel`, `race_step`, `race_step_back`, `race_stop`

Không đổi tên các action này nếu chưa sửa cả backend lẫn frontend.

## Frontend editing notes

- Đừng đổi `id` trong `templates/index.html` một cách riêng lẻ; JS đang bind trực tiếp bằng `getElementById`.
- `visualize.js` assume shape của `/api/state` gồm các field như `rows`, `cols`, `grid`, `running`, `finished`, `paused`, `step_ptr`, `path_cells`, `stats`, `show_tree`, `checkpoint`.
- `race.js` assume shape của `/api/race` gồm `order`, `running`, `paused`, `done`, `step_ptr`, `runners`, `results`.
- Tree view phụ thuộc `/api/tree` và `state.came_from`; nếu sửa format tree data thì phải sửa render tree tương ứng.
- `btn-tree` đang xuất hiện trong sidebar, còn `btn-tree-close` nằm trong header của tree panel.

## Khi sửa runner hoặc state

- `core/runner.py` là file nhạy cảm nhất vì nó nối tất cả: actions, threads, step mode, checkpoint mode, race mode.
- Step mode phụ thuộc `state.step_history` và `state.step_ptr`.
- Race mode dùng shared singleton `state`; đừng thêm logic làm rò trạng thái giữa các runner.
- Nếu thay đổi cách thuật toán kết thúc, cần kiểm tra lại `Visualize`, `Step`, `Checkpoint`, `Race`, và `Tree`.
- Nếu sửa layout `Visualize`, nhớ kiểm tra tương tác giữa `viz-sidebar`, `tree-area`, và `grid-area`.

## Khi thêm thuật toán mới

1. Tạo file mới trong `algorithms/`.
2. Implement theo generator contract ở trên.
3. Import thuật toán trong `algorithms/__init__.py`.
4. Thêm entry vào `REGISTRY`.
5. Chạy app và test cả visualize mode lẫn race mode.

## Ưu tiên khi bảo trì

- Giữ nguyên contract giữa backend và frontend.
- Thay đổi nhỏ, đúng chỗ, tránh refactor rộng nếu không cần.
- Nếu docs cũ mâu thuẫn với hành vi mới, cập nhật docs theo code hiện tại.
