import time
import unittest

from app import app
from core.runner import reset_runtime_state


class MazeApiBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config.update(TESTING=True)

    def setUp(self):
        reset_runtime_state()
        self.client = app.test_client()

    def tearDown(self):
        reset_runtime_state()

    def post_action(self, expected_status=200, expected_ok=True, **payload):
        response = self.client.post("/api/action", json=payload)
        self.assertEqual(response.status_code, expected_status)
        body = response.get_json()
        self.assertIsNotNone(body)
        self.assertEqual(body.get("ok"), expected_ok)
        return body

    def get_visual_state(self):
        response = self.client.get("/api/state")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIsNotNone(body)
        return body

    def get_race_state(self):
        response = self.client.get("/api/race")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIsNotNone(body)
        return body

    def wait_for_visual_state(self, predicate, timeout=2.0):
        deadline = time.time() + timeout
        state = self.get_visual_state()
        while time.time() < deadline:
            if predicate(state):
                return state
            time.sleep(0.01)
            state = self.get_visual_state()
        self.fail(f"Timed out waiting for visualize state. Last state: {state}")

    def wait_for_race_state(self, predicate, timeout=2.0):
        deadline = time.time() + timeout
        state = self.get_race_state()
        while time.time() < deadline:
            if predicate(state):
                return state
            time.sleep(0.01)
            state = self.get_race_state()
        self.fail(f"Timed out waiting for race state. Last state: {state}")

    def configure_small_grid(self):
        self.post_action(action="set_grid", rows=6, cols=6)
        self.post_action(action="set_start", r=0, c=0)
        self.post_action(action="set_end", r=5, c=5)
        self.post_action(action="speed", value=400)

    def test_get_visual_state_matches_expected_shape(self):
        state = self.get_visual_state()

        self.assertEqual(
            set(state.keys()),
            {
                "rows",
                "cols",
                "grid",
                "running",
                "finished",
                "paused",
                "step_ptr",
                "path_cells",
                "cur_alg",
                "speed",
                "set_mode",
                "stats",
                "checkpoint",
                "maze_running",
            },
        )
        self.assertEqual(len(state["grid"]), state["rows"] * state["cols"])
        self.assertEqual(
            set(state["stats"].keys()),
            {"nodes", "path", "cost", "time", "found", "iterations", "peak_memory"},
        )

    def test_get_race_state_matches_expected_shape(self):
        state = self.get_race_state()

        self.assertEqual(
            set(state.keys()),
            {
                "rows",
                "cols",
                "speed",
                "order",
                "running",
                "paused",
                "done",
                "step_ptr",
                "runners",
                "results",
            },
        )
        self.assertGreater(state["rows"], 0)
        self.assertGreater(state["cols"], 0)
        self.assertGreater(state["speed"], 0)
        self.assertEqual(state["order"], [])
        self.assertEqual(state["runners"], {})
        self.assertIsNone(state["results"])

    def test_post_action_returns_ok_and_updates_speed(self):
        self.post_action(action="speed", value=123)
        state = self.get_visual_state()

        self.assertEqual(state["speed"], 123)

    def test_unknown_action_returns_error_details(self):
        body = self.post_action(
            expected_status=400,
            expected_ok=False,
            action="nope",
        )

        self.assertEqual(body["error"], "unknown_action")
        self.assertEqual(body["action"], "nope")

    def test_invalid_payload_returns_error_details(self):
        body = self.post_action(
            expected_status=400,
            expected_ok=False,
            action="set_start",
            r="bad",
            c=0,
        )

        self.assertEqual(body["error"], "invalid_payload")
        self.assertEqual(body["action"], "set_start")

    def test_race_start_requires_two_algorithms(self):
        body = self.post_action(
            expected_status=400,
            expected_ok=False,
            action="race_start",
        )

        self.assertEqual(body["error"], "action_rejected")
        self.assertEqual(body["action"], "race_start")

    def test_race_state_reflects_grid_shape_and_speed(self):
        self.post_action(action="set_grid", rows=7, cols=9)
        self.post_action(action="speed", value=77)

        race = self.get_race_state()

        self.assertEqual(race["rows"], 7)
        self.assertEqual(race["cols"], 9)
        self.assertEqual(race["speed"], 77)

    def test_set_start_end_and_grid_cell_actions_update_grid(self):
        self.configure_small_grid()

        self.post_action(action="set_start", r=1, c=1)
        self.post_action(action="set_end", r=4, c=4)
        self.post_action(action="grid_cell", r=2, c=2)
        state = self.get_visual_state()

        self.assertEqual(state["grid"][1 * state["cols"] + 1], 2)
        self.assertEqual(state["grid"][4 * state["cols"] + 4], 3)
        self.assertEqual(state["grid"][2 * state["cols"] + 2], 1)

        self.post_action(action="grid_cell", r=2, c=2, remove=True)
        state = self.get_visual_state()
        self.assertEqual(state["grid"][2 * state["cols"] + 2], 0)

    def test_step_and_step_back_maintain_history(self):
        self.configure_small_grid()

        self.post_action(action="step")
        first = self.get_visual_state()
        self.assertTrue(first["paused"])
        self.assertFalse(first["running"])
        self.assertGreaterEqual(first["step_ptr"], 1)
        self.assertFalse(first["finished"])

        first_grid = list(first["grid"])

        self.post_action(action="step")
        second = self.get_visual_state()
        self.assertGreater(second["step_ptr"], first["step_ptr"])

        self.post_action(action="step_back")
        rewound = self.get_visual_state()
        self.assertEqual(rewound["step_ptr"], first["step_ptr"])
        self.assertEqual(rewound["grid"], first_grid)

    def test_run_action_completes_and_reports_path(self):
        self.configure_small_grid()

        self.post_action(action="run")
        state = self.wait_for_visual_state(lambda item: item["finished"], timeout=2.5)

        self.assertFalse(state["running"])
        self.assertTrue(state["stats"]["found"])
        self.assertGreater(len(state["path_cells"]), 0)
        self.assertGreater(state["stats"]["path"], 0)

    def test_race_toggle_and_race_start_produce_results(self):
        self.configure_small_grid()

        self.post_action(action="race_toggle", idx=0)
        self.post_action(action="race_toggle", idx=1)
        race = self.get_race_state()
        self.assertEqual(race["order"], [0, 1])

        self.post_action(action="race_start")
        race = self.wait_for_race_state(lambda item: item["done"], timeout=2.5)

        self.assertFalse(race["running"])
        self.assertTrue(race["done"])
        self.assertIsNotNone(race["results"])
        self.assertEqual(len(race["results"]), 2)
        self.assertEqual({item["alg_idx"] for item in race["results"]}, {0, 1})

    def test_switch_tab_preserves_finished_visual_snapshot(self):
        self.configure_small_grid()

        self.post_action(action="run")
        before = self.wait_for_visual_state(lambda item: item["finished"], timeout=2.5)

        self.post_action(action="switch_tab", tab="race")
        self.post_action(action="switch_tab", tab="visualize")
        after = self.get_visual_state()

        self.assertTrue(after["finished"])
        self.assertFalse(after["running"])
        self.assertFalse(after["paused"])
        self.assertEqual(after["path_cells"], before["path_cells"])
        self.assertEqual(after["stats"], before["stats"])

    def test_switch_tab_discards_unfinished_visual_session(self):
        self.configure_small_grid()

        self.post_action(action="step")
        before = self.get_visual_state()
        self.assertTrue(before["paused"])
        self.assertGreaterEqual(before["step_ptr"], 1)

        self.post_action(action="switch_tab", tab="race")
        self.post_action(action="switch_tab", tab="visualize")
        after = self.get_visual_state()

        self.assertFalse(after["running"])
        self.assertFalse(after["paused"])
        self.assertFalse(after["finished"])
        self.assertEqual(after["step_ptr"], -1)
        self.assertEqual(after["path_cells"], [])
        self.assertIsNone(after["stats"]["found"])


if __name__ == "__main__":
    unittest.main()
