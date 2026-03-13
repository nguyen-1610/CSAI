# config.py
"""
Configuration and Global State for Maze Pathfinding Visualizer.
"""

# ─────────────────────────────────────────────
# WINDOW & GRID SETTINGS
# ─────────────────────────────────────────────
W, H   = 1180, 730
ROWS   = 28
COLS   = 40
CELL   = 17          # pixels per cell
GX     = 8           # grid left offset
GY     = 54          # grid top  offset
PX     = GX + COLS * CELL + 16   # panel left edge
PW     = W - PX - 8              # panel width

# ─────────────────────────────────────────────
# COLOR PALETTE
# ─────────────────────────────────────────────
BG         = ( 18,  20,  32)
C_EMPTY    = ( 42,  46,  62)
C_WALL     = ( 12,  14,  22)
C_START    = ( 46, 213, 115)
C_END      = (213,  60,  60)
C_VISITED  = ( 38,  75, 155)
C_FRONTIER = ( 70, 130, 210)
C_PATH     = (252, 196,  25)
C_WHITE    = (225, 228, 240)
C_GRAY     = (130, 135, 155)
C_PANEL    = ( 25,  28,  42)
C_BTN      = ( 48,  62, 105)
C_BTN_H    = ( 68,  88, 145)
C_BTN_A    = ( 88, 118, 190)
C_BTN_OK   = ( 40, 130,  70)
C_BTN_SEL  = ( 35, 120,  70)
C_GREEN    = ( 46, 180,  95)
C_RED      = (190,  55,  55)
C_ORANGE   = (210, 130,  40)
C_YELLOW   = (230, 190,  30)

DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


# ─────────────────────────────────────────────
# GLOBAL STATE CLASS
# ─────────────────────────────────────────────
class State:
    def __init__(self):
        self.walls       = set()
        self.start_cell  = (4, 4)
        self.end_cell    = (ROWS - 5, COLS - 5)

        self.vis_cells   = set()
        self.front_cells = set()
        self.path_cells  = []

        self.running     = False
        self.finished    = False
        self.cur_alg     = 0       # Index của thuật toán đang chọn
        self.set_mode    = None    # None | 'start' | 'end'
        self.speed       = 20      # steps advanced per frame
        self.alg_gen     = None
        self._counter    = [0]     # tie-breaking counter for heapq

        self.stats = {"nodes": 0, "path": 0, "cost": 0, "time": 0.0, "found": None}

    def clear_search(self):
        self.running = False
        if self.alg_gen is not None:
            try:
                self.alg_gen.close()
            except Exception:
                pass
        self.alg_gen     = None
        self.vis_cells   = set()
        self.front_cells = set()
        self.path_cells  = []
        self.stats       = {"nodes": 0, "path": 0, "cost": 0, "time": 0.0, "found": None}
        self.finished    = False

    def start_algorithm(self, func):
        self.clear_search()
        self._counter[0] = 0
        self.running  = True
        self.alg_gen  = func()


# ─────────────────────────────────────────────
# SINGLETON INSTANCE
# Toàn bộ project sẽ import biến 'state' này để dùng chung.
# VD: from config import state -> state.walls.add(...)
# ─────────────────────────────────────────────
state = State()