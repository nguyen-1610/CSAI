"""Runtime state for the single-user maze visualizer."""

import threading

from core.constants import COLS, DEFAULT_SPEED, ROWS


class RaceRuntime:
    def __init__(self):
        self.order = []
        self.runners = {}
        self.running = False
        self.done = False
        self.results = []
        self.thread = None
        self.paused = False
        self.step_history = []
        self.step_ptr = -1
        self.history_gen_base = 0

    def reset(self, keep_order=True):
        order = list(self.order) if keep_order else []
        self.order = order
        self.runners = {}
        self.running = False
        self.done = False
        self.results = []
        self.thread = None
        self.paused = False
        self.step_history = []
        self.step_ptr = -1
        self.history_gen_base = 0


class State:
    def __init__(self):
        # This demo app intentionally keeps one in-process singleton runtime.
        # That tradeoff keeps local/demo deployment simple, including Render.
        self.runtime_lock = threading.RLock()
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
        self.speed = DEFAULT_SPEED
        self.alg_gen = None
        self.algo_thread = None
        self._counter = [0]

        self.stats = self._new_stats()
        self.came_from = {}

        self.step_history = []   # list of (vis_copy, front_copy) for step-back
        self.step_ptr = -1
        self.step_history_gen_base = 0  # generator calls before history[0]
        self.paused = False

        # Used by checkpoint mode so the UI keeps green at the original start during phase 2.
        self.phase2_orig_start = None
        self.race = RaceRuntime()
        self.viz_snapshot = None

    def _new_stats(self):
        return {
            "nodes": 0,
            "path": 0,
            "cost": 0,
            "time": 0.0,
            "found": None,
            "iterations": 1,
            "peak_memory": 0,
        }

    def new_stats(self):
        return self._new_stats()

    def clear_search(self):
        with self.runtime_lock:
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
            self.stats = self._new_stats()
            self.finished = False
            self.came_from = {}
            self.step_history = []
            self.step_ptr = -1
            self.step_history_gen_base = 0
            self.paused = False
            self.phase2_orig_start = None

    def start_algorithm(self, func):
        with self.runtime_lock:
            self.clear_search()
            self._counter[0] = 0
            self.running = True
            self.alg_gen = func()

    def reset_to_defaults(self):
        with self.runtime_lock:
            self.clear_search()
            self.rows = ROWS
            self.cols = COLS
            self.walls = set()
            self.terrain = {}
            self.start_cell = (4, 4)
            self.end_cell = (self.rows - 5, self.cols - 5)
            self.checkpoint_cell = None
            self.cur_alg = 0
            self.set_mode = None
            self.speed = DEFAULT_SPEED
            self._counter[0] = 0
            self.viz_snapshot = None


state = State()
