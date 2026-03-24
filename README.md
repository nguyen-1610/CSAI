# Maze Pathfinding Visualizer

Web app Flask để visualize và so sánh các thuật toán tìm đường trên grid.

Project này là app demo single-user:

- ưu tiên code gọn, dễ demo, dễ sửa
- không có multi-user hoặc per-session state
- có thể deploy nhẹ lên Render nếu cần

## Tính năng hiện tại

- Tab `Visualize`
  - chạy 1 thuật toán
  - `Run`, `Pause`, `Continue`
  - `Step`, `Step Back`
  - kéo thả start, end, checkpoint
  - `Basic Maze`, `Weighted Maze`
  - weighted terrain với grass, swamp, water
- Tab `Race`
  - chọn nhiều thuật toán để chạy song song
  - xem mini mazes
  - xem chart so sánh nodes, path, cost, time, iterations, peak memory

Lưu ý:

- Tree view đã bị loại bỏ khỏi code hiện tại.
- Grid ở tab `Visualize` luôn auto-fit, không còn zoom/pan bằng chuột.

## Cách chạy

Repo dùng virtual environment tại `.venv/`.

### macOS / Linux

```bash
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Hoặc không cần activate:

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

Hoặc không cần activate:

```powershell
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python app.py
```

Mở `http://localhost:5000`.

### Tắt auto-reload

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

### Smoke test tay nên chạy

- Tab `Visualize`
  - chọn thuật toán và `Run`
  - `Pause` / `Continue`
  - `Step` / `Step Back`
  - kéo thả start/end/checkpoint
  - `Basic Maze` và `Weighted Maze`
- Tab `Race`
  - chọn ít nhất 2 thuật toán
  - `Race`, `Pause`, `Continue`
  - `Step`, `Step Back`
  - xem panel và chart

## API hiện tại

Frontend hiện dùng đúng 3 endpoint:

- `GET /api/state`
- `GET /api/race`
- `POST /api/action`

Frontend dùng polling:

- `visualize.js` poll `/api/state`
- `race.js` poll `/api/race`
- cả hai đang poll khoảng mỗi `40ms`

## Tài liệu liên quan

- [Architecture.md](./Architecture.md)
- [AGENTS.md](./AGENTS.md)
- [PRChecklist.md](./PRChecklist.md)
- [RefactorPlan.md](./RefactorPlan.md)
