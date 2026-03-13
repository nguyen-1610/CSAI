# Cấu trúc thư mục cho Maze Pathfinding Visualizer

## Cây thư mục đề xuất

```
lab01/
├── main.py                      # Entry point (~10 dòng)
├── config.py                    # Hằng số + State class + clear_search/start_algorithm (~120 dòng)
├── grid.py                      # Grid helpers + maze generation (~75 dòng)
├── gui.py                       # Toàn bộ rendering pygame + main event loop (~300 dòng)
├── algorithms/                  # Plugin folder - mỗi thuật toán 1 file
│   ├── __init__.py              # Registry: ALGO_FUNCS, ALG_NAMES, ALG_FULL (~30 dòng)
│   ├── bfs.py                   # Breadth-First Search
│   ├── dfs.py                   # Depth-First Search
│   ├── ucs.py                   # Uniform Cost Search
│   ├── astar.py                 # A* Search
│   ├── iddfs.py                 # Iterative Deepening DFS
│   ├── bidirectional.py         # Bidirectional BFS
│   ├── beam.py                  # Beam Search
│   └── idastar.py               # Iterative Deepening A*
├── README.md
├── .gitignore
└── .venv/
```

**Tổng: 4 core files + 9 algorithm files = 13 files**

## Dependency Graph (không circular import)

```
Layer 0:  config.py              (không import file nào trong project)
Layer 1:  grid.py                (import config)
Layer 2:  algorithms/*.py        (import config, grid)
          algorithms/__init__.py (import tất cả algorithm modules)
Layer 3:  gui.py                 (import config, grid, algorithms)
Layer 4:  main.py                (import gui)
```

## Chi tiết từng file

### `config.py` — Hằng số + State

**Phần constants:**

* Window: `W`, `H`, `ROWS`, `COLS`, `CELL`, `GX`, `GY`, `PX`, `PW`
* Màu sắc: `BG`, `C_EMPTY`, `C_WALL`, `C_START`, `C_END`, `C_VISITED`, `C_FRONTIER`, `C_PATH`, các màu UI
* `DIRS` = [(-1,0), (1,0), (0,-1), (0,1)]

**Phần state:**

* Class `State` với attributes: `walls`, `start_cell`, `end_cell`, `vis_cells`, `front_cells`, `path_cells`, `running`, `finished`, `cur_alg`, `set_mode`, `speed`, `alg_gen`, `_counter`, `stats`
* Singleton instance: `state = State()`
* Hàm `clear_search()` và `start_algorithm()`

### `grid.py` — Grid utilities + Maze generation

**Grid helpers:**

* `in_bounds(r, c)` — kiểm tra ô trong grid
* `get_neighbors(r, c)` — trả về ô lân cận hợp lệ (không phải wall)
* `heuristic(a, b)` — Manhattan distance
* `reconstruct_path(came_from, node)` — dựng path từ end về start
* `next_id()` — tie-breaker cho heapq

**Maze generation:**

* `generate_maze()` — tạo mê cung bằng recursive division (iterative stack-based)

### `algorithms/__init__.py` — Plugin Registry

```python
from algorithms.bfs import algo_bfs
from algorithms.dfs import algo_dfs
# ... tương tự

REGISTRY = [
    {"name": "BFS",   "full": "Breadth-First Search",              "func": algo_bfs},
    {"name": "DFS",   "full": "Depth-First Search",                "func": algo_dfs},
    # ...
]

ALGO_FUNCS = [e["func"] for e in REGISTRY]
ALG_NAMES  = [e["name"] for e in REGISTRY]
ALG_FULL   = [e["full"] for e in REGISTRY]
```

### Mỗi file algorithm (vd `algorithms/bfs.py`)

* Import `from config import state` và `from grid import get_neighbors, reconstruct_path` (tuỳ algo)
* Hàm generator `algo_bfs()` — yield `(visited, frontier)` mỗi bước
* Thay `global path_cells, stats, finished` bằng `state.path_cells`, `state.stats`, `state.finished`

### `gui.py` — Giao diện pygame

* Font init, screen/clock
* Button layout
* Hàm `txt()`, `draw_btn()`, `mk_btn()`
* `draw_all()` — render toàn bộ
* `run()` — main event loop (while True)

### `main.py` — Entry point

```python
import pygame, sys
pygame.init()
sys.setrecursionlimit(100_000)
from gui import run
run()
```

## Cách thêm thuật toán mới (plugin workflow)

1. Tạo `algorithms/greedy.py` với `algo_greedy()` generator
2. Thêm 1 dòng import + 1 entry vào `REGISTRY` trong `algorithms/__init__.py`
3. Xong — GUI tự nhận algorithm mới

## Thứ tự thực hiện

1. Tạo cấu trúc thư mục + tất cả file rỗng (hoặc với comment mô tả)
2. Tạo `config.py` — copy hằng số + tạo State class
3. Tạo `grid.py` — extract helpers + maze gen
4. Tạo `algorithms/` + 8 file + `__init__.py`
5. Tạo `gui.py` — rendering + event loop
6. Tạo `main.py` — entry point
7. Test: `python main.py`

## Verification

* Chạy `python main.py` — app hoạt động y hệt bản gốc
* Test từng algorithm: BFS, DFS, UCS, A*, IDDFS, Bidirectional, Beam, IDA*
* Test maze generation, draw/erase walls, set start/end
* Test clear search, reset all, speed controls
