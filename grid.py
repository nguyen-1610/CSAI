"""
grid.py — Grid Helpers + Maze Generation
=========================================
Chứa:
  - in_bounds(r, c)          — kiểm tra ô nằm trong grid
  - get_neighbors(r, c)      — trả về các ô lân cận hợp lệ (không phải wall)
  - heuristic(a, b)          — Manhattan distance
  - reconstruct_path(cf, n)  — dựng path từ came_from dict
  - next_id()                — tie-breaker counter cho heapq
  - generate_maze()          — tạo mê cung bằng recursive division

Import từ: config (ROWS, COLS, DIRS, state)
Được import bởi: algorithms/*.py, gui.py
"""

