"""
gui.py — Pygame Rendering + Main Event Loop
=============================================
Chứa:
  - Font init (FS, FM, FL, FT)
  - Screen & clock creation
  - Button layout (alg_rects, btn_run, btn_clear, ...)
  - UI helpers: txt(), draw_btn(), mk_btn(), grid_cell()
  - draw_all() — render toàn bộ giao diện
  - run()      — main event loop (while True, 60 FPS)

Import từ: config (mọi thứ), grid (in_bounds, generate_maze), algorithms (ALGO_FUNCS, ALG_NAMES, ALG_FULL)
Được import bởi: main.py
"""

