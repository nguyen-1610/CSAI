"""Run orchestration for visualize mode and race mode."""

import logging
import threading
import time

from algorithms import ALGO_FUNCS, ALG_NAMES
from algorithms._contract import finalize_failure, finalize_success
from core.action_handlers import RunnerActionHooks, dispatch_action
from core.constants import (
    RUN_LOOP_INTERVAL_SECONDS,
    STEP_HISTORY_LIMIT,
    STEP_HISTORY_TRIM,
    THREAD_JOIN_TIMEOUT_SECONDS,
)
from core.grid import build_grid_array
from core.state import state

logger = logging.getLogger(__name__)


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


def reset_runtime_state(wait_for_threads=True, timeout=THREAD_JOIN_TIMEOUT_SECONDS):
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
            "rows": state.rows,
            "cols": state.cols,
            "speed": state.speed,
            "order": list(race.order),
            "running": race.running,
            "paused": race.paused,
            "done": race.done,
            "step_ptr": race.step_ptr,
            "runners": runner_data,
            "results": [dict(item) for item in race.results] if race.done else None,
        }


def _path_to_came_from(path):
    came_from = {}
    previous = None
    for node in path:
        came_from[node] = previous
        previous = node
    return came_from


def _race_checkpoint_wrap(algo_func):
    """Checkpoint wrapper safe for race mode (multiple concurrent runners)."""
    s = state.start_cell
    e = state.end_cell
    cp = state.checkpoint_cell

    saved_start = state.start_cell
    saved_end = state.end_cell
    state.start_cell = s
    state.end_cell = cp
    gen1 = algo_func()
    vis1 = set()
    first1 = True
    try:
        while True:
            vis, front = next(gen1)
            if first1:
                state.start_cell = saved_start
                state.end_cell = saved_end
                first1 = False
            vis1 = set(vis)
            yield vis, front
    except StopIteration:
        if first1:
            state.start_cell = saved_start
            state.end_cell = saved_end

    path1 = list(state.path_cells)
    came_from1 = dict(state.came_from)
    stats1 = dict(state.stats)
    found1 = stats1.get("found")
    nodes1 = stats1.get("nodes", 0)
    cost1 = stats1.get("cost", 0)
    time1 = stats1.get("time", 0.0)
    iter1 = stats1.get("iterations", 1)
    peak1 = stats1.get("peak_memory", 0)

    if not found1:
        finalize_failure(came_from1, nodes1, time1, iterations=iter1, peak_memory=peak1)
        return

    saved_start2 = state.start_cell
    state.start_cell = cp
    state.end_cell = e
    state.path_cells = path1
    state.came_from = dict(came_from1)
    state.vis_cells = set()
    state.front_cells = set()
    state.stats = state.new_stats()

    gen2 = algo_func()
    first2 = True
    try:
        while True:
            vis2, front2 = next(gen2)
            if first2:
                state.start_cell = saved_start2
                first2 = False
            yield vis1 | set(vis2), front2 - vis1
    except StopIteration:
        if first2:
            state.start_cell = saved_start2

    path2 = list(state.path_cells)
    came_from2 = dict(state.came_from)
    stats2 = dict(state.stats)
    found2 = stats2.get("found")
    nodes2 = stats2.get("nodes", 0)
    cost2 = stats2.get("cost", 0)
    time2 = stats2.get("time", 0.0)
    iter2 = stats2.get("iterations", 1)
    peak2 = stats2.get("peak_memory", 0)
    if found2 and path1 and path2:
        combined = path1 + path2[1:]
        finalize_success(
            combined,
            _path_to_came_from(combined),
            nodes1 + nodes2,
            cost1 + cost2,
            time1 + time2,
            iterations=iter1 + iter2,
            peak_memory=max(peak1, peak2),
        )
    else:
        finalize_failure(
            came_from2,
            nodes1 + nodes2,
            time1 + time2,
            iterations=iter1 + iter2,
            peak_memory=max(peak1, peak2),
        )


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
        came_from1 = dict(state.came_from)
        stats1 = dict(state.stats)
        found1 = stats1.get("found")
        nodes1 = stats1.get("nodes", 0)
        cost1 = stats1.get("cost", 0)
        time1 = stats1.get("time", 0.0)
        iter1 = stats1.get("iterations", 1)
        peak1 = stats1.get("peak_memory", 0)

        if not found1:
            finalize_failure(came_from1, nodes1, time1, iterations=iter1, peak_memory=peak1)
            return

        state.finished = False
        state.path_cells = path1
        state.came_from = dict(came_from1)
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
        came_from2 = dict(state.came_from)
        stats2 = dict(state.stats)
        found2 = stats2.get("found")
        nodes2 = stats2.get("nodes", 0)
        cost2 = stats2.get("cost", 0)
        time2 = stats2.get("time", 0.0)
        iter2 = stats2.get("iterations", 1)
        peak2 = stats2.get("peak_memory", 0)
        if found2 and path1 and path2:
            combined = path1 + path2[1:]
            finalize_success(
                combined,
                _path_to_came_from(combined),
                nodes1 + nodes2,
                cost1 + cost2,
                time1 + time2,
                iterations=iter1 + iter2,
                peak_memory=max(peak1, peak2),
            )
        else:
            finalize_failure(
                came_from2,
                nodes1 + nodes2,
                time1 + time2,
                iterations=iter1 + iter2,
                peak_memory=max(peak1, peak2),
            )

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


def _start_race_thread():
    with state.runtime_lock:
        race = state.race
        if race.thread and race.thread.is_alive():
            return
        race.thread = threading.Thread(target=_race_loop, daemon=True)
        race.thread.start()


def _algo_loop():
    with state.runtime_lock:
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
                    if len(state.step_history) < STEP_HISTORY_LIMIT:
                        state.step_history.append(snap)
                    else:
                        state.step_history = state.step_history[STEP_HISTORY_TRIM:]
                        state.step_history_gen_base += STEP_HISTORY_TRIM
                        state.step_history.append(snap)
                    state.step_ptr = len(state.step_history) - 1
                except StopIteration:
                    state.running = False
                    break
                except Exception as exc:
                    logger.exception("Visualize algorithm loop failed: %s", exc)
                    state.running = False
                    break
        time.sleep(RUN_LOOP_INTERVAL_SECONDS)
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
        _start_race_thread()


def _race_loop():
    with state.runtime_lock:
        race = state.race
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
                        runner["path"] = list(state.path_cells or [])
                        snap[idx] = (set(vis), set(runner["front"]))
                    except StopIteration:
                        runner["done"] = True
                        if state.vis_cells or state.front_cells:
                            runner["vis"] = set(state.vis_cells)
                            runner["front"] = set(state.front_cells)
                        runner["path"] = list(state.path_cells)
                        runner["stats"] = dict(state.stats)
                        state.clear_search()
                        snap[idx] = (set(runner["vis"]), set(runner["front"]))
                    except Exception as exc:
                        logger.exception("Race runner failed for %s: %s", ALG_NAMES[idx], exc)
                        runner["done"] = True
                        runner["stats"] = state.new_stats()
                        state.clear_search()
                        snap[idx] = (set(runner["vis"]), set())
                if any_active:
                    if len(race.step_history) < STEP_HISTORY_LIMIT:
                        race.step_history.append(snap)
                    else:
                        race.step_history = race.step_history[STEP_HISTORY_TRIM:]
                        race.history_gen_base += STEP_HISTORY_TRIM
                        race.step_history.append(snap)
                    race.step_ptr = len(race.step_history) - 1
            if all(race.runners.get(i, {}).get("done", False) for i in race.order):
                race.running = False
                race.done = True
                race.results = _build_race_results()
                break
        time.sleep(RUN_LOOP_INTERVAL_SECONDS)
    with state.runtime_lock:
        if state.race.thread is threading.current_thread():
            state.race.thread = None


def _action_hooks():
    return RunnerActionHooks(
        build_race_results=_build_race_results,
        cancel_race=_do_cancel_race,
        checkpoint_wrap=_checkpoint_wrap,
        copy_front=_copy_front,
        init_race=_init_race,
        race_checkpoint_wrap=_race_checkpoint_wrap,
        resize_grid=_resize_grid,
        start_algo_thread=_start_algo_thread,
        start_race=_start_race,
        start_race_thread=_start_race_thread,
    )


def handle_action(data):
    """Primary `/api/action` dispatcher used by the Flask route."""
    with state.runtime_lock:
        return dispatch_action(data, _action_hooks())
