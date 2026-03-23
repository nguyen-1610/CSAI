"""Runtime state for the maze visualizer."""

from core.constants import COLS, ROWS


class State:
    def __init__(self):
        self.rows = ROWS
        self.cols = COLS
        self.walls = set()
        self.terrain = {}    # (r, c) -> cell type: 8=water 9=swamp 10=grass
        self.start_cell = (4, 4)
        self.end_cell = (self.rows - 5, self.cols - 5)
        self.checkpoint_cell = None

        self.vis_cells = set()
        self.front_cells = set()
        self.path_cells = []

        self.running = False
        self.finished = False
        self.cur_alg = 0
        self.set_mode = None    # None | 'start' | 'end' | 'checkpoint'
        self.speed = 20
        self.alg_gen = None
        self._counter = [0]

        self.stats = {"nodes": 0, "path": 0, "cost": 0, "time": 0.0, "found": None, "iterations": 1, "peak_memory": 0}
        self.run_history = []
        self.came_from = {}

        self.step_history = []   # list of (vis_copy, front_copy) for step-back
        self.step_ptr = -1
        self.step_history_gen_base = 0  # generator calls before history[0]
        self.paused = False

        # Used by checkpoint mode so the UI keeps green at the original start during phase 2.
        self.phase2_orig_start = None

    def clear_search(self):
        self.running = False
        if self.alg_gen is not None:
            try:
                self.alg_gen.close()
            except Exception:
                pass
        self.alg_gen = None
        self.vis_cells = set()
        self.front_cells = set()
        self.path_cells = []
        self.stats = {"nodes": 0, "path": 0, "cost": 0, "time": 0.0, "found": None, "iterations": 1, "peak_memory": 0}
        self.finished = False
        self.came_from = {}
        self.step_history = []
        self.step_ptr = -1
        self.step_history_gen_base = 0
        self.paused = False
        self.phase2_orig_start = None

    def start_algorithm(self, func):
        self.clear_search()
        self._counter[0] = 0
        self.running = True
        self.alg_gen = func()


state = State()
