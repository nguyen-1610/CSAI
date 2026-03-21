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
        self.terrain     = {}    # (r,c) → cell type: 8=water 9=swamp 10=grass
        self.start_cell      = (4, 4)
        self.end_cell        = (self.rows - 5, self.cols - 5)
        self.checkpoint_cell = None

        self.vis_cells   = set()
        self.front_cells = set()
        self.path_cells  = []

        self.running     = False
        self.finished    = False
        self.cur_alg     = 0
        self.set_mode    = None    # None | 'start' | 'end' | 'checkpoint'
        self.speed       = 20
        self.alg_gen     = None
        self._counter    = [0]

        self.stats = {"nodes": 0, "path": 0, "cost": 0, "time": 0.0, "found": None}
        self.run_history = []
        self.came_from   = {}

        self.step_history = []   # list of (vis_copy, front_copy) for step-back
        self.step_ptr     = -1   # pointer into step_history
        self.paused       = False

        # Used by _checkpoint_wrap so the display keeps green at orig_start during phase 2
        self.phase2_orig_start = None

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
        self.step_history = []
        self.step_ptr     = -1
        self.paused       = False
        self.phase2_orig_start = None

    def start_algorithm(self, func):
        self.clear_search()
        self._counter[0] = 0
        self.running  = True
        self.alg_gen  = func()


# ─────────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────────
state = State()
