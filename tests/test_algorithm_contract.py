import unittest

from algorithms.astar import algo_astar
from algorithms.beam import algo_beam
from algorithms.bidirectional import algo_bidirectional
from algorithms.bfs import algo_bfs
from algorithms.dfs import algo_dfs
from algorithms.idastar import algo_idastar
from algorithms.iddfs import algo_iddfs
from algorithms.ucs import algo_ucs
from core.grid import reconstruct_path
from core.runner import _checkpoint_wrap, _race_checkpoint_wrap, reset_runtime_state
from core.state import state

FULL_STATS_KEYS = {"nodes", "path", "cost", "time", "found", "iterations", "peak_memory"}
ALGORITHMS = [
    ("bfs", algo_bfs),
    ("dfs", algo_dfs),
    ("ucs", algo_ucs),
    ("astar", algo_astar),
    ("beam", algo_beam),
    ("bidirectional", algo_bidirectional),
    ("iddfs", algo_iddfs),
    ("idastar", algo_idastar),
]


class AlgorithmContractTests(unittest.TestCase):
    def setUp(self):
        reset_runtime_state()

    def tearDown(self):
        reset_runtime_state()

    def configure_grid(self, rows, cols, start, end, walls=None, checkpoint=None):
        with state.runtime_lock:
            state.rows = rows
            state.cols = cols
            state.walls = set(walls or ())
            state.terrain = {}
            state.start_cell = start
            state.end_cell = end
            state.checkpoint_cell = checkpoint
            state.clear_search()

    def drain(self, gen):
        while True:
            try:
                next(gen)
            except StopIteration:
                return

    def assert_full_contract(self, expected_found):
        self.assertTrue(state.finished)
        self.assertEqual(set(state.stats.keys()), FULL_STATS_KEYS)
        self.assertEqual(state.stats["found"], expected_found)
        self.assertIsInstance(state.came_from, dict)

    def test_each_algorithm_sets_full_contract_on_success(self):
        for name, algo in ALGORITHMS:
            with self.subTest(name=name):
                start = (0, 0)
                end = (4, 4)
                self.configure_grid(5, 5, start, end)
                self.drain(algo())
                self.assert_full_contract(True)
                self.assertGreater(state.stats["nodes"], 0)
                self.assertGreater(state.stats["path"], 0)
                self.assertEqual(state.stats["path"], len(state.path_cells))
                self.assertEqual(state.path_cells[0], start)
                self.assertEqual(state.path_cells[-1], end)

    def test_each_algorithm_sets_full_contract_on_failure(self):
        for name, algo in ALGORITHMS:
            with self.subTest(name=name):
                start = (0, 0)
                end = (2, 2)
                walls = {(0, 1), (1, 0)}
                self.configure_grid(3, 3, start, end, walls=walls)
                self.drain(algo())
                self.assert_full_contract(False)
                self.assertGreater(state.stats["nodes"], 0)
                self.assertEqual(state.stats["path"], 0)
                self.assertEqual(state.stats["cost"], 0)
                self.assertEqual(state.path_cells, [])

    def test_each_algorithm_handles_start_equals_end(self):
        for name, algo in ALGORITHMS:
            with self.subTest(name=name):
                start = (1, 1)
                self.configure_grid(3, 3, start, start)
                self.drain(algo())
                self.assert_full_contract(True)
                self.assertEqual(state.stats["path"], 1)
                self.assertEqual(state.stats["cost"], 0)
                self.assertEqual(state.path_cells, [start])

    def test_dfs_never_yields_visited_cells_inside_frontier(self):
        self.configure_grid(
            5,
            5,
            (0, 0),
            (4, 4),
            walls={(2, 4), (3, 1), (1, 4), (2, 3), (0, 2), (3, 2)},
        )

        for step, (visited, frontier) in enumerate(algo_dfs(), start=1):
            self.assertTrue(
                set(visited).isdisjoint(frontier),
                f"DFS yielded overlapping visited/frontier cells at step {step}",
            )

    def test_dfs_keeps_snake_path_shape_when_reaching_a_pending_cell(self):
        self.configure_grid(4, 4, (0, 0), (1, 0))
        self.drain(algo_dfs())
        self.assertEqual(
            state.path_cells,
            [
                (0, 0),
                (0, 1),
                (0, 2),
                (0, 3),
                (1, 3),
                (2, 3),
                (3, 3),
                (3, 2),
                (3, 1),
                (3, 0),
                (2, 0),
                (2, 1),
                (2, 2),
                (1, 2),
                (1, 1),
                (1, 0),
            ],
        )

    def test_checkpoint_wrap_success_keeps_full_contract(self):
        self.configure_grid(5, 5, (0, 0), (4, 4), checkpoint=(0, 2))
        self.drain(_checkpoint_wrap(algo_bfs))
        self.assert_full_contract(True)
        self.assertEqual(state.stats["path"], len(state.path_cells))
        self.assertEqual(reconstruct_path(state.came_from, state.end_cell), state.path_cells)
        self.assertGreater(state.stats["iterations"], 0)

    def test_checkpoint_wrap_failure_keeps_full_contract(self):
        self.configure_grid(3, 3, (0, 0), (2, 2), walls={(0, 1), (1, 0)}, checkpoint=(0, 2))
        self.drain(_checkpoint_wrap(algo_bfs))
        self.assert_full_contract(False)
        self.assertEqual(state.stats["path"], 0)
        self.assertEqual(state.path_cells, [])
        self.assertGreater(state.stats["iterations"], 0)

    def test_race_checkpoint_wrap_success_keeps_full_contract(self):
        self.configure_grid(5, 5, (0, 0), (4, 4), checkpoint=(0, 2))
        self.drain(_race_checkpoint_wrap(algo_bfs))
        self.assert_full_contract(True)
        self.assertEqual(state.stats["path"], len(state.path_cells))
        self.assertEqual(reconstruct_path(state.came_from, state.end_cell), state.path_cells)

    def test_race_checkpoint_wrap_failure_keeps_full_contract(self):
        self.configure_grid(3, 3, (0, 0), (2, 2), walls={(0, 1), (1, 0)}, checkpoint=(0, 2))
        self.drain(_race_checkpoint_wrap(algo_bfs))
        self.assert_full_contract(False)
        self.assertEqual(state.stats["path"], 0)
        self.assertEqual(state.path_cells, [])
        self.assertGreater(state.stats["iterations"], 0)



