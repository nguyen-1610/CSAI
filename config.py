# config.py
"""
Configuration and Global State for Maze Pathfinding Visualizer.
"""

# ─────────────────────────────────────────────
# WINDOW & GRID SETTINGS
# ─────────────────────────────────────────────
W, H   = 1600, 900
ROWS   = 28          # default rows
COLS   = 40          # default cols
PW     = 340         # panel width (left side)

DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


# ─────────────────────────────────────────────
# GLOBAL STATE CLASS
# ─────────────────────────────────────────────
class State:
    def __init__(self):
        self.rows        = ROWS
        self.cols        = COLS
        self.walls       = set()
        self.start_cell  = (4, 4)
        self.end_cell    = (self.rows - 5, self.cols - 5)

        self.vis_cells   = set()
        self.front_cells = set()
        self.path_cells  = []

        self.running     = False
        self.finished    = False
        self.cur_alg     = 0
        self.set_mode    = None    # None | 'start' | 'end'
        self.speed       = 20
        self.alg_gen     = None
        self._counter    = [0]

        self.stats = {"nodes": 0, "path": 0, "cost": 0, "time": 0.0, "found": None}
        self.run_history = []
        self.came_from   = {}

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
        self.came_from   = {}

    def start_algorithm(self, func):
        self.clear_search()
        self._counter[0] = 0
        self.running  = True
        self.alg_gen  = func()


# ─────────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────────
state = State()
