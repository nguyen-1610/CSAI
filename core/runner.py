"""Run orchestration for visualize mode and race mode."""

import threading
import time

from algorithms import ALGO_FUNCS, ALG_NAMES
from core.constants import MAX_C, MAX_R, MAX_SPEED, MIN_C, MIN_R
from core.grid import build_grid_array, generate_maze, generate_plain_terrain
from core.state import state


def _do_cancel_race():
    """Reset all race state while keeping the selected algorithm order."""
    with state.runtime_lock:
        race = state.race
        race.running = False
        race.paused = False
        race.done = False
        race.results = []
        race.runners = {}
        race.step_history = []
        race.step_ptr = -1
        race.history_gen_base = 0


def reset_runtime_state(wait_for_threads=True, timeout=0.5):
    """Reset visualize and race runtime state for tests and fresh app sessions."""
    with state.runtime_lock:
        state.running = False
        state.race.running = False
        state.race.paused = False
        algo_thread = state.algo_thread
        race_thread = state.race.thread

    if wait_for_threads:
        if algo_thread and algo_thread.is_alive():
            algo_thread.join(timeout)
        if race_thread and race_thread.is_alive():
            race_thread.join(timeout)

    with state.runtime_lock:
        state.algo_thread = None
        state.race.reset(keep_order=False)
        state.reset_to_defaults()


def get_visual_state():
    with state.runtime_lock:
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
            "stats": dict(state.stats),
            "checkpoint": list(state.checkpoint_cell) if state.checkpoint_cell else None,
            "maze_running": False,
        }


def get_race_state():
    with state.runtime_lock:
        race = state.race
        runner_data = {}
        for idx in race.order:
            runner = race.runners.get(idx)
            if runner:
                runner_data[str(idx)] = {
                    "name": ALG_NAMES[idx],
                    "done": runner.get("done", False),
                    "grid": build_grid_array(
                        runner.get("vis", set()),
                        runner.get("front", set()),
                        runner.get("path", []),
                    ),
                    "path": [list(pos) for pos in runner.get("path", [])],
                    "stats": dict(runner["stats"]) if runner.get("stats") else None,
                }
            else:
                runner_data[str(idx)] = {
                    "name": ALG_NAMES[idx],
                    "done": False,
                    "grid": build_grid_array(),
                    "stats": None,
                }
        return {
            "order": list(race.order),
            "running": race.running,
            "paused": race.paused,
            "done": race.done,
            "step_ptr": race.step_ptr,
            "runners": runner_data,
            "results": [dict(item) for item in race.results] if race.done else None,
        }


def handle_action(data):
    with state.runtime_lock:
        race = state.race
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
                if state.step_ptr < len(state.step_history) - 1:
                    # User stepped back — rewind by recreating generator and fast-forwarding
                    target = state.step_ptr
                    total_calls = state.step_history_gen_base + target
                    state.step_history = state.step_history[:target + 1]
                    if state.alg_gen:
                        try:
                            state.alg_gen.close()
                        except Exception:
                            pass
                    func = ALGO_FUNCS[state.cur_alg]
                    new_gen = (lambda f=func: _checkpoint_wrap(f))() if state.checkpoint_cell else func()
                    for _ in range(total_calls):
                        try:
                            next(new_gen)
                        except StopIteration:
                            break
                    state.alg_gen = new_gen
                    vis, front = state.step_history[target]
                    state.vis_cells = set(vis)
                    state.front_cells = set(front)
                state.step_ptr = len(state.step_history) - 1
                state.paused = False
                state.running = True
                _start_algo_thread()
            else:
                if state.finished:
                    state.clear_search()
                func = ALGO_FUNCS[state.cur_alg]
                if state.checkpoint_cell:
                    state.start_algorithm(lambda f=func: _checkpoint_wrap(f))
                else:
                    state.start_algorithm(func)
                _start_algo_thread()

        elif action == "step":
            if not state.finished:
                if not state.alg_gen:
                    func = ALGO_FUNCS[state.cur_alg]
                    if state.checkpoint_cell:
                        state.start_algorithm(lambda f=func: _checkpoint_wrap(f))
                    else:
                        state.start_algorithm(func)
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
            if not state.running and state.step_ptr > 0:
                state.step_ptr -= 1
                vis, front = state.step_history[state.step_ptr]
                state.vis_cells = set(vis)
                state.front_cells = set(front)

        elif action == "cancel_algo":
            state.clear_search()

        elif action == "clear":
            state.clear_search()

        elif action == "maze":
            _do_cancel_race()
            state.clear_search()
            generate_maze()

        elif action == "set_checkpoint":
            r, c = int(payload["r"]), int(payload["c"])
            pos = (r, c)
            if pos not in (state.start_cell, state.end_cell):
                _do_cancel_race()
                state.checkpoint_cell = pos
                state.clear_search()

        elif action == "remove_checkpoint":
            _do_cancel_race()
            state.checkpoint_cell = None
            state.clear_search()

        elif action == "reset":
            _do_cancel_race()
            state.clear_search()
            state.walls.clear()
            state.terrain.clear()

        elif action == "speed":
            state.speed = max(1, min(MAX_SPEED, int(payload.get("value", 20))))

        elif action == "set_mode":
            mode = payload.get("mode")
            state.set_mode = mode if state.set_mode != mode else None

        elif action == "set_start":
            r, c = int(payload["r"]), int(payload["c"])
            pos = (r, c)
            if pos != state.end_cell and 0 <= r < state.rows and 0 <= c < state.cols:
                _do_cancel_race()
                state.start_cell = pos

        elif action == "set_end":
            r, c = int(payload["r"]), int(payload["c"])
            pos = (r, c)
            if pos != state.start_cell and 0 <= r < state.rows and 0 <= c < state.cols:
                _do_cancel_race()
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
                _do_cancel_race()
                if payload.get("remove"):
                    state.walls.discard(pos)
                    state.terrain.pop(pos, None)  # right-click also clears terrain
                else:
                    state.walls.add(pos)
                    state.terrain.pop(pos, None)

        elif action == "change_grid":
            dr, dc = int(payload.get("dr", 0)), int(payload.get("dc", 0))
            nr = max(MIN_R, min(MAX_R, state.rows + dr))
            nc = max(MIN_C, min(MAX_C, state.cols + dc))
            if nr != state.rows or nc != state.cols:
                _do_cancel_race()
                _resize_grid(nr, nc)

        elif action == "set_grid":
            nr = max(MIN_R, min(MAX_R, int(payload.get("rows", state.rows))))
            nc = max(MIN_C, min(MAX_C, int(payload.get("cols", state.cols))))
            if nr != state.rows or nc != state.cols:
                _do_cancel_race()
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
                _do_cancel_race()
                if terrain_type == 0:
                    state.terrain.pop(pos, None)
                else:
                    state.terrain[pos] = terrain_type

        elif action == "clear_terrain":
            _do_cancel_race()
            state.terrain.clear()

        elif action == "weighted_maze":
            _do_cancel_race()
            state.clear_search()
            generate_plain_terrain()

        elif action == "race_toggle":
            idx = int(payload.get("idx", -1))
            if not race.running and 0 <= idx < len(ALG_NAMES):
                if race.done:
                    race.done = False
                    race.results = []
                    race.step_history = []
                    race.step_ptr = -1
                    race.history_gen_base = 0
                if idx in race.order:
                    race.order.remove(idx)
                elif len(race.order) < 8:
                    race.order.append(idx)

        elif action == "race_start":
            if race.running:
                race.running = False
                race.paused = True
            elif race.paused and race.runners and not race.done:
                if race.step_ptr < len(race.step_history) - 1:
                    # User stepped back — rewind each runner's generator
                    target = race.step_ptr
                    total_calls = race.history_gen_base + target
                    race.step_history = race.step_history[:target + 1]
                    for idx in race.order:
                        runner = race.runners.get(idx)
                        if not runner:
                            continue
                        state._counter[0] = 0
                        func = ALGO_FUNCS[idx]
                        new_gen = _race_checkpoint_wrap(func) if state.checkpoint_cell else func()
                        runner["done"] = False
                        runner["path"] = []
                        runner["stats"] = None
                        state.clear_search()
                        for _ in range(total_calls):
                            try:
                                vis, front = next(new_gen)
                                runner["vis"] = vis
                                runner["front"] = _copy_front(front)
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
                race.step_ptr = len(race.step_history) - 1
                race.paused = False
                race.running = True
                race.thread = threading.Thread(target=_race_loop, daemon=True)
                race.thread.start()
            elif len(race.order) >= 2:
                _start_race()

        elif action == "race_cancel":
            _do_cancel_race()

        elif action == "race_step":
            if len(race.order) >= 2:
                if not race.runners:
                    _init_race()
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
                elif not race.done:
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
                            runner["front"] = _copy_front(front)
                            snap[idx] = (set(vis), set(runner["front"]))
                        except StopIteration:
                            runner["done"] = True
                            runner["path"] = list(state.path_cells)
                            runner["stats"] = dict(state.stats)
                            state.clear_search()
                            snap[idx] = (set(runner["vis"]), set())
                    if len(race.step_history) < 2000:
                        race.step_history.append(snap)
                    else:
                        race.step_history = race.step_history[500:]
                        race.step_history.append(snap)
                    race.step_ptr = len(race.step_history) - 1
                    if all(race.runners.get(i, {}).get("done", False) for i in race.order):
                        race.done = True
                        race.running = False
                        race.results = _build_race_results()

        elif action == "race_step_back":
            if race.step_ptr > 0:
                race.step_ptr -= 1
                snap = race.step_history[race.step_ptr]
                for idx, (vis, front) in snap.items():
                    runner = race.runners.get(idx)
                    if runner:
                        runner["vis"] = set(vis)
                        runner["front"] = set(front)

        elif action == "race_stop":
            race.running = False
            race.done = True
            race.results = _build_race_results()

        elif action == "switch_tab":
            tab_to = payload.get("tab")
            if tab_to == "race":
                state.viz_snapshot = {
                    "path_cells": list(state.path_cells),
                    "vis_cells": set(state.vis_cells),
                    "front_cells": set(state.front_cells),
                    "came_from": dict(state.came_from),
                    "stats": dict(state.stats),
                    "finished": state.finished,
                }
            elif tab_to == "visualize" and state.viz_snapshot is not None:
                state.path_cells = state.viz_snapshot["path_cells"]
                state.vis_cells = state.viz_snapshot["vis_cells"]
                state.front_cells = state.viz_snapshot["front_cells"]
                state.came_from = state.viz_snapshot["came_from"]
                state.stats = state.viz_snapshot["stats"]
                state.finished = state.viz_snapshot["finished"]
                state.running = False
                state.paused = False
                state.alg_gen = None
                state.viz_snapshot = None

        return {"ok": True}


def _race_checkpoint_wrap(algo_func):
    """
    Checkpoint wrapper safe for race mode (multiple concurrent runners).

    State is temporarily set only around the FIRST next() call of each
    sub-generator — the moment the algorithm captures its local s/e —
    then immediately restored so other runners are not affected.
    """
    s  = state.start_cell
    e  = state.end_cell
    cp = state.checkpoint_cell

    # ── Phase 1: start → checkpoint ───────────────────────────────────
    saved_start = state.start_cell
    saved_end   = state.end_cell
    state.start_cell = s   # guard: another runner may have left state.start = cp
    state.end_cell   = cp
    gen1 = algo_func()
    vis1 = set()
    first1 = True
    try:
        while True:
            vis, front = next(gen1)
            if first1:                              # algo captured its (s, cp) — restore
                state.start_cell = saved_start
                state.end_cell   = saved_end
                first1 = False
            vis1 = set(vis)
            yield vis, front
    except StopIteration:
        if first1:
            state.start_cell = saved_start
            state.end_cell   = saved_end

    path1  = list(state.path_cells)
    found1 = state.stats.get("found")
    nodes1 = state.stats.get("nodes", 0)
    cost1  = state.stats.get("cost",  0)
    time1  = state.stats.get("time",  0.0)
    state.clear_search()

    if not found1:
        state.finished = True
        return

    # ── Phase 2: checkpoint → end ─────────────────────────────────────
    saved_start2 = state.start_cell
    state.start_cell = cp
    gen2 = algo_func()
    first2 = True
    try:
        while True:
            vis2, front2 = next(gen2)
            if first2:                              # algo captured its (cp, e) — restore
                state.start_cell = saved_start2
                first2 = False
            yield vis1 | set(vis2), front2 - vis1
    except StopIteration:
        if first2:
            state.start_cell = saved_start2

    path2  = list(state.path_cells)
    found2 = state.stats.get("found")
    nodes2 = state.stats.get("nodes", 0)
    cost2  = state.stats.get("cost",  0)
    time2  = state.stats.get("time",  0.0)

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
        state.stats = state.new_stats()

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
    with state.runtime_lock:
        race = state.race
        return [
            {"name": ALG_NAMES[idx], "alg_idx": idx, **race.runners[idx]["stats"]}
            for idx in race.order
            if race.runners.get(idx) and race.runners[idx].get("stats")
        ]


def _start_algo_thread():
    with state.runtime_lock:
        if state.algo_thread and state.algo_thread.is_alive():
            return
        state.algo_thread = threading.Thread(target=_algo_loop, daemon=True)
        state.algo_thread.start()


def _algo_loop():
    with state.runtime_lock:
        # Record initial state for fresh runs so history[i] == after i gen calls
        if not state.step_history:
            state.step_history.append((set(state.vis_cells), set(state.front_cells)))
            state.step_history_gen_base = 0
            state.step_ptr = 0
    while True:
        with state.runtime_lock:
            if not (state.running and state.alg_gen and not state.finished):
                break
            for _ in range(state.speed):
                if not state.running:
                    break
                try:
                    vis, front = next(state.alg_gen)
                    state.vis_cells = vis
                    state.front_cells = front
                    snap = (set(vis), set(front))
                    if len(state.step_history) < 2000:
                        state.step_history.append(snap)
                    else:
                        state.step_history = state.step_history[500:]
                        state.step_history_gen_base += 500
                        state.step_history.append(snap)
                    state.step_ptr = len(state.step_history) - 1
                except StopIteration:
                    state.running = False
                    break
                except Exception as exc:
                    print(f"[Algo error] {exc}")
                    state.running = False
                    break
        time.sleep(1 / 60)
    with state.runtime_lock:
        if state.algo_thread is threading.current_thread():
            state.algo_thread = None


def _init_race():
    with state.runtime_lock:
        race = state.race
        state.clear_search()
        race.done = False
        race.results = []
        race.step_history = []
        race.step_ptr = -1
        race.history_gen_base = 0
        race.runners = {}
        for idx in race.order:
            state._counter[0] = 0
            func = ALGO_FUNCS[idx]
            gen = _race_checkpoint_wrap(func) if state.checkpoint_cell else func()
            race.runners[idx] = {
                "idx": idx,
                "gen": gen,
                "vis": set(),
                "front": set(),
                "done": False,
                "path": [],
                "stats": None,
            }
        state.clear_search()


def _start_race():
    with state.runtime_lock:
        _init_race()
        race = state.race
        race.running = True
        race.paused = False
        race.thread = threading.Thread(target=_race_loop, daemon=True)
        race.thread.start()


def _race_loop():
    with state.runtime_lock:
        race = state.race
        # Record initial state for fresh runs so history[i] == after i gen calls per runner
        if not race.step_history:
            baseline = {
                idx: (set(race.runners[idx]["vis"]), set(race.runners[idx]["front"]))
                for idx in race.order if race.runners.get(idx)
            }
            race.step_history.append(baseline)
            race.history_gen_base = 0
            race.step_ptr = 0
    while True:
        with state.runtime_lock:
            race = state.race
            if not race.running:
                break
            for _ in range(state.speed):
                if not race.running:
                    break
                snap = {}
                any_active = False
                for idx in race.order:
                    runner = race.runners.get(idx)
                    if not runner or runner["done"]:
                        snap[idx] = (set(runner["vis"] if runner else []), set())
                        continue
                    any_active = True
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
                    except Exception as exc:
                        print(f"[Race error] {ALG_NAMES[idx]}: {exc}")
                        runner["done"] = True
                        runner["stats"] = state.new_stats()
                        state.clear_search()
                        snap[idx] = (set(runner["vis"]), set())
                if any_active:
                    if len(race.step_history) < 2000:
                        race.step_history.append(snap)
                    else:
                        race.step_history = race.step_history[500:]
                        race.history_gen_base += 500
                        race.step_history.append(snap)
                    race.step_ptr = len(race.step_history) - 1
            if all(race.runners.get(i, {}).get("done", False) for i in race.order):
                race.running = False
                race.done = True
                race.results = _build_race_results()
                break
        time.sleep(1 / 60)
    with state.runtime_lock:
        if state.race.thread is threading.current_thread():
            state.race.thread = None
