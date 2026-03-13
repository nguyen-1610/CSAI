"""
config.py — Hằng số cấu hình + Global State
=============================================
Chứa:
  - Window & grid settings (W, H, ROWS, COLS, CELL, ...)
  - Color palette (BG, C_EMPTY, C_WALL, C_START, ...)
  - Direction constants (DIRS)
  - Class State — singleton chứa toàn bộ trạng thái mutable
  - Hàm clear_search() và start_algorithm()

Import từ: (không import file nào trong project)
Được import bởi: grid.py, algorithms/*.py, gui.py
"""

