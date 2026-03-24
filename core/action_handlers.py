"""Action dispatch helpers for the `/api/action` endpoint."""

from dataclasses import dataclass

from algorithms import ALGO_FUNCS, ALG_NAMES
from core.constants import MAX_C, MAX_R, MAX_SPEED, MIN_C, MIN_R
from core.grid import generate_maze, generate_plain_terrain
from core.state import state

MAX_STEP_HISTORY = 2000
STEP_HISTORY_TRIM = 500
ALLOWED_TABS = {"visualize", "race"}
ALLOWED_TERRAINS = {0, 8, 9, 10}
MISSING = object()


@dataclass(frozen=True)
class RunnerActionHooks:
    build_race_results: object
    cancel_race: object
    checkpoint_wrap: object
    copy_front: object
    init_race: object
    race_checkpoint_wrap: object
    resize_grid: object
    start_algo_thread: object
    start_race: object
    start_race_thread: object


class ActionValidationError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def dispatch_action(payload, hooks):
    payload = payload or {}
    action = payload.get("action")
    if not isinstance(action, str) or not action.strip():
        return _error(
            None,
            "invalid_payload",
            "Action payload must include a non-empty 'action' string.",
        )

    action = action.strip()
    handler = ACTION_HANDLERS.get(action)
    if handler is None:
        return _error(action, "unknown_action", f"Unknown action '{action}'.")

    try:
        return handler(payload, hooks)
    except ActionValidationError as exc:
        return _error(action, exc.code, exc.message)


def _ok(action, **extra):
    body = {"ok": True, "action": action}
    body.update(extra)
    return body


def _error(action, code, message):
    body = {"ok": False, "error": code, "message": message}
    if action is not None:
        body["action"] = action
    return body


def _invalid(message):
    raise ActionValidationError("invalid_payload", message)


def _rejected(message):
    raise ActionValidationError("action_rejected", message)


def _parse_int(payload, key, default=MISSING):
    raw = payload.get(key, MISSING)
    if raw is MISSING:
        if default is MISSING:
            _invalid(f"'{key}' is required.")
        raw = default
    try:
        return int(raw)
    except (TypeError, ValueError):
        _invalid(f"'{key}' must be an integer.")


def _parse_position(payload):
    r = _parse_int(payload, "r")
    c = _parse_int(payload, "c")
    if not (0 <= r < state.rows and 0 <= c < state.cols):
        _invalid(f"Cell ({r}, {c}) is outside the current grid.")
    return r, c, (r, c)


def _parse_algo_idx(payload):
    idx = _parse_int(payload, "idx")
    if not (0 <= idx < len(ALG_NAMES)):
        _invalid(f"'idx' must be between 0 and {len(ALG_NAMES) - 1}.")
    return idx


def _parse_speed(payload):
    value = _parse_int(payload, "value", default=20)
    return max(1, min(MAX_SPEED, value))


def _parse_grid_delta(payload):
    dr = _parse_int(payload, "dr", default=0)
    dc = _parse_int(payload, "dc", default=0)
    return dr, dc


def _parse_grid_size(payload):
    rows = _parse_int(payload, "rows", default=state.rows)
    cols = _parse_int(payload, "cols", default=state.cols)
    rows = max(MIN_R, min(MAX_R, rows))
    cols = max(MIN_C, min(MAX_C, cols))
    return rows, cols


def _parse_terrain(payload):
    terrain_type = _parse_int(payload, "terrain", default=0)
    if terrain_type not in ALLOWED_TERRAINS:
        _invalid("'terrain' must be one of 0, 8, 9, or 10.")
    return terrain_type


def _parse_tab(payload):
    tab = payload.get("tab")
    if tab not in ALLOWED_TABS:
        _invalid("'tab' must be either 'visualize' or 'race'.")
    return tab


def _visual_algo_factory(hooks):
    func = ALGO_FUNCS[state.cur_alg]
    if state.checkpoint_cell:
        return lambda f=func: hooks.checkpoint_wrap(f)
    return func


def _race_algo_generator(hooks, idx):
    func = ALGO_FUNCS[idx]
    if state.checkpoint_cell:
        return hooks.race_checkpoint_wrap(func)
    return func()


def _resume_visual_generator(hooks):
    target = state.step_ptr
    total_calls = state.step_history_gen_base + target
    state.step_history = state.step_history[:target + 1]
    if state.alg_gen:
        try:
            state.alg_gen.close()
        except Exception:
            pass

    new_gen = _race_or_visual_resume_generator(hooks, state.cur_alg, visualize=True)
    for _ in range(total_calls):
        try:
            next(new_gen)
        except StopIteration:
            break
    state.alg_gen = new_gen
    vis, front = state.step_history[target]
    state.vis_cells = set(vis)
    state.front_cells = set(front)


def _race_or_visual_resume_generator(hooks, idx, visualize=False):
    func = ALGO_FUNCS[idx]
    if visualize:
        if state.checkpoint_cell:
            return hooks.checkpoint_wrap(func)
        return func()
    return _race_algo_generator(hooks, idx)


def _resume_race_generators(hooks):
    race = state.race
    target = race.step_ptr
    total_calls = race.history_gen_base + target
    race.step_history = race.step_history[:target + 1]
    for idx in race.order:
        runner = race.runners.get(idx)
        if not runner:
            continue
        state._counter[0] = 0
        new_gen = _race_algo_generator(hooks, idx)
        runner["done"] = False
        runner["path"] = []
        runner["stats"] = None
        state.clear_search()
        for _ in range(total_calls):
            try:
                vis, front = next(new_gen)
                runner["vis"] = vis
                runner["front"] = hooks.copy_front(front)
            except StopIteration:
                runner["done"] = True
                runner["path"] = list(state.path_cells)
                runner["stats"] = dict(state.stats)
                state.clear_search()
                break
        runner["gen"] = new_gen
        state.clear_search()

    snap = race.step_history[target]
    for idx, (vis, front) in snap.items():
        runner = race.runners.get(idx)
        if runner:
            runner["vis"] = set(vis)
            runner["front"] = set(front)


def _make_visual_snapshot():
    return {
        "path_cells": list(state.path_cells),
        "vis_cells": set(state.vis_cells),
        "front_cells": set(state.front_cells),
        "came_from": dict(state.came_from),
        "stats": dict(state.stats),
        "finished": state.finished,
    }


def _restore_visual_snapshot(snapshot):
    state.path_cells = list(snapshot["path_cells"])
    state.vis_cells = set(snapshot["vis_cells"])
    state.front_cells = set(snapshot["front_cells"])
    state.came_from = dict(snapshot["came_from"])
    state.stats = dict(snapshot["stats"])
    state.finished = snapshot["finished"]
    state.running = False
    state.paused = False
    state.alg_gen = None


def _discard_incomplete_visual_session():
    # We intentionally do not preserve live generator state across tabs.
    # Leaving Visualize mid-run or mid-step returns to a clean editing state.
    if (
        state.running
        or state.paused
        or state.alg_gen is not None
        or state.step_history
        or state.vis_cells
        or state.front_cells
        or state.path_cells
        or state.stats.get("found") is not None
    ):
        state.clear_search()


def handle_select_algo(payload, hooks):
    idx = _parse_algo_idx(payload)
    if state.running:
        state.clear_search()
    state.cur_alg = idx
    return _ok("select_algo")


def handle_run(_payload, hooks):
    if state.running:
        state.running = False
        state.paused = True
        return _ok("run")

    if state.paused:
        if state.step_ptr < len(state.step_history) - 1:
            _resume_visual_generator(hooks)
        state.step_ptr = len(state.step_history) - 1
        state.paused = False
        state.running = True
        hooks.start_algo_thread()
        return _ok("run")

    if state.finished:
        state.clear_search()
    state.start_algorithm(_visual_algo_factory(hooks))
    hooks.start_algo_thread()
    return _ok("run")


def handle_step(_payload, hooks):
    if state.finished:
        return _ok("step")

    if not state.alg_gen:
        state.start_algorithm(_visual_algo_factory(hooks))
        state.running = False

    state.running = False
    state.paused = True

    if state.step_ptr < len(state.step_history) - 1:
        state.step_ptr += 1
        vis, front = state.step_history[state.step_ptr]
        state.vis_cells = set(vis)
        state.front_cells = set(front)
        return _ok("step")

    if state.alg_gen and not state.finished:
        if not state.step_history:
            state.step_history.append((set(state.vis_cells), set(state.front_cells)))
            state.step_ptr = 0
        try:
            vis, front = next(state.alg_gen)
            state.vis_cells = vis
            state.front_cells = front
            if len(state.step_history) < MAX_STEP_HISTORY:
                state.step_history.append((set(vis), set(front)))
                state.step_ptr = len(state.step_history) - 1
        except StopIteration:
            state.running = False
            state.finished = True

    return _ok("step")


def handle_step_back(_payload, _hooks):
    if not state.running and state.step_ptr > 0:
        state.step_ptr -= 1
        vis, front = state.step_history[state.step_ptr]
        state.vis_cells = set(vis)
        state.front_cells = set(front)
    return _ok("step_back")


def handle_cancel_algo(_payload, _hooks):
    state.clear_search()
    return _ok("cancel_algo")


def handle_clear(_payload, _hooks):
    state.clear_search()
    return _ok("clear")


def handle_maze(_payload, hooks):
    hooks.cancel_race()
    state.clear_search()
    generate_maze()
    return _ok("maze")


def handle_set_checkpoint(payload, hooks):
    _, _, pos = _parse_position(payload)
    if pos in (state.start_cell, state.end_cell):
        # Dragging the checkpoint across start/end should fail quietly.
        return _ok("set_checkpoint")
    hooks.cancel_race()
    state.checkpoint_cell = pos
    state.clear_search()
    return _ok("set_checkpoint")


def handle_remove_checkpoint(_payload, hooks):
    hooks.cancel_race()
    state.checkpoint_cell = None
    state.clear_search()
    return _ok("remove_checkpoint")


def handle_reset(_payload, hooks):
    hooks.cancel_race()
    state.clear_search()
    state.walls.clear()
    state.terrain.clear()
    return _ok("reset")


def handle_speed(payload, _hooks):
    state.speed = _parse_speed(payload)
    return _ok("speed")


def handle_set_mode(payload, _hooks):
    mode = payload.get("mode")
    if mode is not None and not isinstance(mode, str):
        _invalid("'mode' must be a string or null.")
    state.set_mode = mode if state.set_mode != mode else None
    return _ok("set_mode")


def handle_set_start(payload, hooks):
    _, _, pos = _parse_position(payload)
    if pos == state.end_cell:
        # The drag interaction can hover over the end cell; ignore that state.
        return _ok("set_start")
    hooks.cancel_race()
    state.start_cell = pos
    return _ok("set_start")


def handle_set_end(payload, hooks):
    _, _, pos = _parse_position(payload)
    if pos == state.start_cell:
        # The drag interaction can hover over the start cell; ignore that state.
        return _ok("set_end")
    hooks.cancel_race()
    state.end_cell = pos
    return _ok("set_end")


def handle_grid_cell(payload, hooks):
    _, _, pos = _parse_position(payload)
    if state.set_mode == "start":
        state.start_cell = pos
        state.set_mode = None
        return _ok("grid_cell")
    if state.set_mode == "end":
        state.end_cell = pos
        state.set_mode = None
        return _ok("grid_cell")
    if state.running or pos in (state.start_cell, state.end_cell):
        return _ok("grid_cell")

    hooks.cancel_race()
    if payload.get("remove"):
        state.walls.discard(pos)
        state.terrain.pop(pos, None)
    else:
        state.walls.add(pos)
        state.terrain.pop(pos, None)
    return _ok("grid_cell")


def handle_change_grid(payload, hooks):
    dr, dc = _parse_grid_delta(payload)
    rows = max(MIN_R, min(MAX_R, state.rows + dr))
    cols = max(MIN_C, min(MAX_C, state.cols + dc))
    if rows != state.rows or cols != state.cols:
        hooks.cancel_race()
        hooks.resize_grid(rows, cols)
    return _ok("change_grid")


def handle_set_grid(payload, hooks):
    rows, cols = _parse_grid_size(payload)
    if rows != state.rows or cols != state.cols:
        hooks.cancel_race()
        hooks.resize_grid(rows, cols)
    return _ok("set_grid")


def handle_set_terrain(payload, hooks):
    _, _, pos = _parse_position(payload)
    terrain_type = _parse_terrain(payload)
    if (
        pos in (state.start_cell, state.end_cell)
        or pos == state.checkpoint_cell
        or pos in state.walls
        or state.running
    ):
        # Brush drags frequently sweep over protected cells; keep those as no-ops.
        return _ok("set_terrain")

    hooks.cancel_race()
    if terrain_type == 0:
        state.terrain.pop(pos, None)
    else:
        state.terrain[pos] = terrain_type
    return _ok("set_terrain")


def handle_clear_terrain(_payload, hooks):
    hooks.cancel_race()
    state.terrain.clear()
    return _ok("clear_terrain")


def handle_weighted_maze(_payload, hooks):
    hooks.cancel_race()
    state.clear_search()
    generate_plain_terrain()
    return _ok("weighted_maze")


def handle_race_toggle(payload, _hooks):
    race = state.race
    if race.running:
        _rejected("Cannot change race selection while a race is running.")

    idx = _parse_algo_idx(payload)
    if race.done:
        race.done = False
        race.results = []
        race.step_history = []
        race.step_ptr = -1
        race.history_gen_base = 0

    if idx in race.order:
        race.order.remove(idx)
    elif len(race.order) >= 8:
        _rejected("Race mode supports at most 8 algorithms at a time.")
    else:
        race.order.append(idx)
    return _ok("race_toggle")


def handle_race_start(_payload, hooks):
    race = state.race
    if race.running:
        race.running = False
        race.paused = True
        return _ok("race_start")

    if race.paused and race.runners and not race.done:
        if race.step_ptr < len(race.step_history) - 1:
            _resume_race_generators(hooks)
        race.step_ptr = len(race.step_history) - 1
        race.paused = False
        race.running = True
        hooks.start_race_thread()
        return _ok("race_start")

    if len(race.order) < 2:
        _rejected("Select at least two algorithms before starting a race.")

    hooks.start_race()
    return _ok("race_start")


def handle_race_cancel(_payload, hooks):
    hooks.cancel_race()
    return _ok("race_cancel")


def handle_race_step(_payload, hooks):
    race = state.race
    if len(race.order) < 2:
        _rejected("Select at least two algorithms before stepping a race.")

    if not race.runners:
        hooks.init_race()

    race.running = False
    race.paused = True

    if race.step_ptr < len(race.step_history) - 1:
        race.step_ptr += 1
        snap = race.step_history[race.step_ptr]
        for idx, (vis, front) in snap.items():
            runner = race.runners.get(idx)
            if runner:
                runner["vis"] = set(vis)
                runner["front"] = set(front)
        return _ok("race_step")

    if race.done:
        return _ok("race_step")

    if not race.step_history:
        baseline = {
            idx: (set(race.runners[idx]["vis"]), set(race.runners[idx]["front"]))
            for idx in race.order
            if race.runners.get(idx)
        }
        race.step_history.append(baseline)
        race.step_ptr = 0

    snap = {}
    for idx in race.order:
        runner = race.runners.get(idx)
        if not runner or runner["done"]:
            snap[idx] = (
                set(runner["vis"] if runner else []),
                set(runner["front"] if runner else []),
            )
            continue
        try:
            vis, front = next(runner["gen"])
            runner["vis"] = vis
            runner["front"] = hooks.copy_front(front)
            snap[idx] = (set(vis), set(runner["front"]))
        except StopIteration:
            runner["done"] = True
            runner["path"] = list(state.path_cells)
            runner["stats"] = dict(state.stats)
            state.clear_search()
            snap[idx] = (set(runner["vis"]), set())

    if len(race.step_history) < MAX_STEP_HISTORY:
        race.step_history.append(snap)
    else:
        race.step_history = race.step_history[STEP_HISTORY_TRIM:]
        race.step_history.append(snap)
        race.history_gen_base += STEP_HISTORY_TRIM
    race.step_ptr = len(race.step_history) - 1

    if all(race.runners.get(i, {}).get("done", False) for i in race.order):
        race.done = True
        race.running = False
        race.results = hooks.build_race_results()

    return _ok("race_step")


def handle_race_step_back(_payload, _hooks):
    race = state.race
    if race.step_ptr > 0:
        race.step_ptr -= 1
        snap = race.step_history[race.step_ptr]
        for idx, (vis, front) in snap.items():
            runner = race.runners.get(idx)
            if runner:
                runner["vis"] = set(vis)
                runner["front"] = set(front)
    return _ok("race_step_back")


def handle_race_stop(_payload, hooks):
    race = state.race
    race.running = False
    race.done = True
    race.results = hooks.build_race_results()
    return _ok("race_stop")


def handle_switch_tab(payload, _hooks):
    tab_to = _parse_tab(payload)
    if tab_to == "race":
        if state.finished:
            state.viz_snapshot = _make_visual_snapshot()
        else:
            state.viz_snapshot = None
            _discard_incomplete_visual_session()
        return _ok("switch_tab")

    if state.viz_snapshot is not None:
        _restore_visual_snapshot(state.viz_snapshot)
        state.viz_snapshot = None
    return _ok("switch_tab")


VISUALIZE_HANDLERS = {
    "select_algo": handle_select_algo,
    "run": handle_run,
    "step": handle_step,
    "step_back": handle_step_back,
    "cancel_algo": handle_cancel_algo,
    "clear": handle_clear,
    "maze": handle_maze,
    "set_checkpoint": handle_set_checkpoint,
    "remove_checkpoint": handle_remove_checkpoint,
    "reset": handle_reset,
    "speed": handle_speed,
    "set_mode": handle_set_mode,
    "set_start": handle_set_start,
    "set_end": handle_set_end,
    "grid_cell": handle_grid_cell,
    "change_grid": handle_change_grid,
    "set_grid": handle_set_grid,
    "set_terrain": handle_set_terrain,
    "clear_terrain": handle_clear_terrain,
    "weighted_maze": handle_weighted_maze,
}

RACE_HANDLERS = {
    "race_toggle": handle_race_toggle,
    "race_start": handle_race_start,
    "race_cancel": handle_race_cancel,
    "race_step": handle_race_step,
    "race_step_back": handle_race_step_back,
    "race_stop": handle_race_stop,
}

SYSTEM_HANDLERS = {
    "switch_tab": handle_switch_tab,
}

ACTION_HANDLERS = {
    **VISUALIZE_HANDLERS,
    **RACE_HANDLERS,
    **SYSTEM_HANDLERS,
}
