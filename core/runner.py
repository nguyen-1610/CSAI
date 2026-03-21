"""Run orchestration for visualize mode and race mode."""

import threading
import time

from algorithms import ALGO_FUNCS, ALG_NAMES
from core.constants import MAX_C, MAX_R, MAX_SPEED, MIN_C, MIN_R
from core.grid import build_grid_array, generate_maze, generate_plain_terrain
from core.state import state

_algo_thread = None
_last_alg_name = ""
_show_tree = False

_race_order = []
_race_runners = {}
_race_running = False
_race_done = False
_race_results = []
_race_thread = None
_race_paused = False
_race_step_history = []
_race_step_ptr = -1


def get_visual_state():
    return {
        "rows": state.rows,
        "cols": state.cols,
        "grid": build_grid_array(state.vis_cells, state.front_cells, state.path_cells),
        "running": state.running,
        "finished": state.finished,
        "paused": state.paused,
        "step_ptr": state.step_ptr,
        "path_cells": [list(pos) for pos in state.path_cells],
        "cur_alg": state.cur_alg,
        "speed": state.speed,
        "set_mode": state.set_mode,
        "stats": state.stats,
        "has_tree": bool(state.came_from) and state.finished,
        "show_tree": _show_tree,
        "algo_name": _last_alg_name,
        "checkpoint": list(state.checkpoint_cell) if state.checkpoint_cell else None,
        "maze_running": False,
    }


def get_race_state():
    runner_data = {}
    for idx in _race_order:
        runner = _race_runners.get(idx)
        if runner:
            runner_data[str(idx)] = {
                "name": ALG_NAMES[idx],
                "done": runner.get("done", False),
                "grid": build_grid_array(
                    runner.get("vis", set()),
                    runner.get("front", set()),
                    runner.get("path", []),
                ),
                "stats": runner.get("stats"),
            }
        else:
            runner_data[str(idx)] = {
                "name": ALG_NAMES[idx],
                "done": False,
                "grid": build_grid_array(),
                "stats": None,
            }
    return {
        "order": _race_order,
        "running": _race_running,
        "paused": _race_paused,
        "done": _race_done,
        "step_ptr": _race_step_ptr,
        "runners": runner_data,
        "results": _race_results if _race_done else None,
    }


def is_tree_visible():
    return _show_tree


def get_last_algorithm_name():
    return _last_alg_name


def handle_action(data):
    global _last_alg_name, _show_tree
    global _race_order, _race_runners, _race_running, _race_paused, _race_done, _race_results, _race_thread
    global _race_step_history, _race_step_ptr

    payload = data or {}
    action = payload.get("action")

    if action == "select_algo":
        idx = int(payload.get("idx", 0))
        if 0 <= idx < len(ALG_NAMES):
            if state.running:
                state.clear_search()
            state.cur_alg = idx

    elif action == "run":
        if state.running:
            state.running = False
            state.paused = True
        elif state.paused:
            if state.step_history:
                vis, front = state.step_history[-1]
                state.vis_cells = set(vis)
                state.front_cells = set(front)
            state.step_history.clear()
            state.step_ptr = -1
            state.paused = False
            state.running = True
            _start_algo_thread()
        else:
            if state.finished:
                state.clear_search()
                _show_tree = False
            func = ALGO_FUNCS[state.cur_alg]
            if state.checkpoint_cell:
                state.start_algorithm(lambda f=func: _checkpoint_wrap(f))
            else:
                state.start_algorithm(func)
            _last_alg_name = ALG_NAMES[state.cur_alg]
            _start_algo_thread()

    elif action == "step":
        if not state.finished:
            if not state.alg_gen:
                func = ALGO_FUNCS[state.cur_alg]
                if state.checkpoint_cell:
                    state.start_algorithm(lambda f=func: _checkpoint_wrap(f))
                else:
                    state.start_algorithm(func)
                _last_alg_name = ALG_NAMES[state.cur_alg]
                state.running = False
            state.running = False
            state.paused = True
            if state.step_ptr < len(state.step_history) - 1:
                state.step_ptr += 1
                vis, front = state.step_history[state.step_ptr]
                state.vis_cells = set(vis)
                state.front_cells = set(front)
            elif state.alg_gen and not state.finished:
                if not state.step_history:
                    state.step_history.append((set(state.vis_cells), set(state.front_cells)))
                    state.step_ptr = 0
                try:
                    vis, front = next(state.alg_gen)
                    state.vis_cells = vis
                    state.front_cells = front
                    if len(state.step_history) < 2000:
                        state.step_history.append((set(vis), set(front)))
                        state.step_ptr = len(state.step_history) - 1
                except StopIteration:
                    state.running = False
                    state.finished = True

    elif action == "step_back":
        if state.step_ptr > 0:
            state.step_ptr -= 1
            vis, front = state.step_history[state.step_ptr]
            state.vis_cells = set(vis)
            state.front_cells = set(front)

    elif action == "cancel_algo":
        state.clear_search()
        _show_tree = False

    elif action == "clear":
        state.clear_search()
        _show_tree = False

    elif action == "maze":
        state.clear_search()
        _show_tree = False
        generate_maze()

    elif action == "set_checkpoint":
        r, c = int(payload["r"]), int(payload["c"])
        pos = (r, c)
        if pos not in (state.start_cell, state.end_cell):
            state.checkpoint_cell = pos
            state.clear_search()

    elif action == "remove_checkpoint":
        state.checkpoint_cell = None
        state.clear_search()

    elif action == "reset":
        state.clear_search()
        state.walls.clear()
        state.terrain.clear()
        _show_tree = False

    elif action == "speed":
        state.speed = max(1, min(MAX_SPEED, int(payload.get("value", 20))))

    elif action == "set_mode":
        mode = payload.get("mode")
        state.set_mode = mode if state.set_mode != mode else None

    elif action == "set_start":
        r, c = int(payload["r"]), int(payload["c"])
        pos = (r, c)
        if pos != state.end_cell and 0 <= r < state.rows and 0 <= c < state.cols:
            state.start_cell = pos

    elif action == "set_end":
        r, c = int(payload["r"]), int(payload["c"])
        pos = (r, c)
        if pos != state.start_cell and 0 <= r < state.rows and 0 <= c < state.cols:
            state.end_cell = pos

    elif action == "grid_cell":
        r, c = int(payload["r"]), int(payload["c"])
        pos = (r, c)
        if state.set_mode == "start":
            state.start_cell = pos
            state.set_mode = None
        elif state.set_mode == "end":
            state.end_cell = pos
            state.set_mode = None
        elif not state.running and pos not in (state.start_cell, state.end_cell):
            if payload.get("remove"):
                state.walls.discard(pos)
            else:
                state.walls.add(pos)
                state.terrain.pop(pos, None)

    elif action == "change_grid":
        dr, dc = int(payload.get("dr", 0)), int(payload.get("dc", 0))
        nr = max(MIN_R, min(MAX_R, state.rows + dr))
        nc = max(MIN_C, min(MAX_C, state.cols + dc))
        if nr != state.rows or nc != state.cols:
            _resize_grid(nr, nc)

    elif action == "set_grid":
        nr = max(MIN_R, min(MAX_R, int(payload.get("rows", state.rows))))
        nc = max(MIN_C, min(MAX_C, int(payload.get("cols", state.cols))))
        if nr != state.rows or nc != state.cols:
            _resize_grid(nr, nc)

    elif action == "set_terrain":
        r, c = int(payload["r"]), int(payload["c"])
        pos = (r, c)
        terrain_type = int(payload.get("terrain", 0))
        if (
            pos not in (state.start_cell, state.end_cell)
            and pos != state.checkpoint_cell
            and pos not in state.walls
            and not state.running
        ):
            if terrain_type == 0:
                state.terrain.pop(pos, None)
            else:
                state.terrain[pos] = terrain_type

    elif action == "clear_terrain":
        state.terrain.clear()

    elif action == "weighted_maze":
        state.clear_search()
        _show_tree = False
        generate_plain_terrain()

    elif action == "toggle_tree":
        if state.finished and state.came_from:
            _show_tree = not _show_tree

    elif action == "race_toggle":
        idx = int(payload.get("idx", -1))
        if not _race_running and 0 <= idx < len(ALG_NAMES):
            if _race_done:
                _race_done = False
                _race_results = []
                _race_step_history.clear()
                _race_step_ptr = -1
            if idx in _race_order:
                _race_order.remove(idx)
            elif len(_race_order) < 8:
                _race_order.append(idx)

    elif action == "race_start":
        if _race_running:
            _race_running = False
            _race_paused = True
        elif _race_paused and _race_runners and not _race_done:
            _race_paused = False
            _race_running = True
            _race_thread = threading.Thread(target=_race_loop, daemon=True)
            _race_thread.start()
        elif len(_race_order) >= 2:
            _start_race()

    elif action == "race_cancel":
        _race_running = False
        _race_paused = False
        _race_done = False
        _race_results = []
        _race_runners = {}
        _race_step_history.clear()
        _race_step_ptr = -1

    elif action == "race_step":
        if len(_race_order) >= 2:
            if not _race_runners:
                _init_race()
            _race_running = False
            _race_paused = True
            if _race_step_ptr < len(_race_step_history) - 1:
                _race_step_ptr += 1
                snap = _race_step_history[_race_step_ptr]
                for idx, (vis, front) in snap.items():
                    runner = _race_runners.get(idx)
                    if runner:
                        runner["vis"] = set(vis)
                        runner["front"] = set(front)
            elif not _race_done:
                if not _race_step_history:
                    baseline = {
                        idx: (set(_race_runners[idx]["vis"]), set(_race_runners[idx]["front"]))
                        for idx in _race_order
                        if _race_runners.get(idx)
                    }
                    _race_step_history.append(baseline)
                    _race_step_ptr = 0
                snap = {}
                for idx in _race_order:
                    runner = _race_runners.get(idx)
                    if not runner or runner["done"]:
                        snap[idx] = (
                            set(runner["vis"] if runner else []),
                            set(runner["front"] if runner else []),
                        )
                        continue
                    try:
                        vis, front = next(runner["gen"])
                        runner["vis"] = vis
                        runner["front"] = _copy_front(front)
                        snap[idx] = (set(vis), set(runner["front"]))
                    except StopIteration:
                        runner["done"] = True
                        runner["path"] = list(state.path_cells)
                        runner["stats"] = dict(state.stats)
                        state.clear_search()
                        snap[idx] = (set(runner["vis"]), set())
                if len(_race_step_history) < 300:
                    _race_step_history.append(snap)
                    _race_step_ptr = len(_race_step_history) - 1
                if all(_race_runners.get(i, {}).get("done", False) for i in _race_order):
                    _race_done = True
                    _race_running = False
                    _race_results = _build_race_results()

    elif action == "race_step_back":
        if _race_step_ptr > 0:
            _race_step_ptr -= 1
            snap = _race_step_history[_race_step_ptr]
            for idx, (vis, front) in snap.items():
                runner = _race_runners.get(idx)
                if runner:
                    runner["vis"] = set(vis)
                    runner["front"] = set(front)

    elif action == "race_stop":
        _race_running = False
        _race_done = True
        _race_results = _build_race_results()

    return {"ok": True}


def _checkpoint_wrap(algo_func):
    """Run start->checkpoint and checkpoint->end as one combined generator."""
    orig_start = state.start_cell
    orig_end = state.end_cell
    checkpoint = state.checkpoint_cell

    try:
        state.end_cell = checkpoint
        gen1 = algo_func()
        vis1 = set()
        try:
            while True:
                vis, front = next(gen1)
                vis1 = set(vis)
                yield vis, front
        except StopIteration:
            pass

        path1 = list(state.path_cells)
        found1 = state.stats.get("found")
        nodes1 = state.stats.get("nodes", 0)
        cost1 = state.stats.get("cost", 0)
        time1 = state.stats.get("time", 0.0)

        if not found1:
            state.finished = True
            return

        state.finished = False
        state.path_cells = path1
        state.came_from = {}
        state.vis_cells = set()
        state.front_cells = set()
        state.stats = {"nodes": 0, "path": 0, "cost": 0, "time": 0.0, "found": None}

        state.start_cell = checkpoint
        state.end_cell = orig_end
        state.phase2_orig_start = orig_start
        gen2 = algo_func()
        try:
            while True:
                vis2, front2 = next(gen2)
                yield vis1 | vis2, front2 - vis1
        except StopIteration:
            pass

        path2 = list(state.path_cells)
        found2 = state.stats.get("found")
        nodes2 = state.stats.get("nodes", 0)
        cost2 = state.stats.get("cost", 0)
        time2 = state.stats.get("time", 0.0)

        if found2 and path1 and path2:
            combined = path1 + path2[1:]
            state.path_cells = combined
            state.stats.update(
                nodes=nodes1 + nodes2,
                path=len(combined),
                cost=cost1 + cost2,
                time=time1 + time2,
                found=True,
            )
        else:
            state.stats.update(nodes=nodes1 + nodes2, found=False, time=time1 + time2)
        state.came_from = {}
        state.finished = True

    finally:
        state.start_cell = orig_start
        state.end_cell = orig_end
        state.phase2_orig_start = None


def _resize_grid(rows, cols):
    state.clear_search()
    state.walls.clear()
    state.terrain.clear()
    state.checkpoint_cell = None
    state.rows, state.cols = rows, cols
    sr, sc = state.start_cell
    state.start_cell = (min(sr, rows - 1), min(sc, cols - 1))
    er, ec = state.end_cell
    state.end_cell = (min(er, rows - 1), min(ec, cols - 1))
    if state.start_cell == state.end_cell:
        state.end_cell = (rows - 1, cols - 1)


def _copy_front(front):
    return front.copy() if hasattr(front, "copy") else set(front)


def _build_race_results():
    return [
        {"name": ALG_NAMES[idx], **_race_runners[idx]["stats"]}
        for idx in _race_order
        if _race_runners.get(idx) and _race_runners[idx].get("stats")
    ]


def _start_algo_thread():
    global _algo_thread
    if _algo_thread and _algo_thread.is_alive():
        return
    _algo_thread = threading.Thread(target=_algo_loop, daemon=True)
    _algo_thread.start()


def _algo_loop():
    while state.running and state.alg_gen and not state.finished:
        for _ in range(state.speed):
            if not state.running:
                break
            try:
                vis, front = next(state.alg_gen)
                state.vis_cells = vis
                state.front_cells = front
            except StopIteration:
                state.running = False
                break
            except Exception as exc:
                print(f"[Algo error] {exc}")
                state.running = False
                break
        time.sleep(1 / 60)


def _init_race():
    global _race_runners, _race_done, _race_results, _race_step_history, _race_step_ptr
    state.clear_search()
    _race_done = False
    _race_results = []
    _race_step_history = []
    _race_step_ptr = -1
    _race_runners = {}
    for idx in _race_order:
        state._counter[0] = 0
        _race_runners[idx] = {
            "idx": idx,
            "gen": ALGO_FUNCS[idx](),
            "vis": set(),
            "front": set(),
            "done": False,
            "path": [],
            "stats": None,
        }
    state.clear_search()


def _start_race():
    global _race_running, _race_paused, _race_thread
    _init_race()
    _race_running = True
    _race_paused = False
    _race_thread = threading.Thread(target=_race_loop, daemon=True)
    _race_thread.start()


def _race_loop():
    global _race_running, _race_done, _race_results
    while _race_running:
        all_done = True
        for idx in _race_order:
            runner = _race_runners.get(idx)
            if not runner or runner["done"]:
                continue
            all_done = False
            for _ in range(state.speed):
                try:
                    vis, front = next(runner["gen"])
                    runner["vis"] = vis
                    runner["front"] = _copy_front(front)
                except StopIteration:
                    runner["done"] = True
                    runner["path"] = list(state.path_cells)
                    runner["stats"] = dict(state.stats)
                    state.clear_search()
                    break
                except Exception as exc:
                    print(f"[Race error] {ALG_NAMES[idx]}: {exc}")
                    runner["done"] = True
                    runner["stats"] = {"nodes": 0, "path": 0, "cost": 0, "time": 0.0, "found": None}
                    state.clear_search()
                    break
        if all_done:
            _race_running = False
            _race_done = True
            _race_results = _build_race_results()
            break
        time.sleep(1 / 60)
