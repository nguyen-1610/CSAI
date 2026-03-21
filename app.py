"""
app.py — Web-based Maze Pathfinding Visualizer
Run:  python app.py
Open: http://localhost:5000
"""

import threading
import time
from collections import deque

try:
    from flask import Flask, render_template, jsonify, request
except ImportError:
    print("Flask is required. Install with:  pip install flask")
    raise SystemExit(1)

from config import state
from grid import generate_maze, generate_plain_terrain
from algorithms import ALGO_FUNCS, ALG_NAMES, ALG_FULL

app = Flask(__name__)

# ─── Module state ─────────────────────────────────────────────
_algo_thread = None
_last_alg_name = ""
_show_tree = False
_tree_cache_key = None
_tree_cache = None

_race_order = []
_race_runners = {}
_race_running = False
_race_done = False
_race_results = []
_race_thread = None


_race_paused = False
_race_step_history = []   # list of {idx: (vis_copy, front_copy)} per step
_race_step_ptr = -1

MAX_SPEED = 200
MIN_R, MAX_R = 5, 50
MIN_C, MAX_C = 5, 80


# ─── Helpers ──────────────────────────────────────────────────
def _grid_array(vis=None, front=None, path=None):
    """Flat list of cell types: 0=empty 1=wall 2=start 3=end 4=vis 5=front 6=path 7=checkpoint"""
    rows, cols = state.rows, state.cols
    # During checkpoint phase 2 start_cell == cp; use the override so green stays at orig_start
    s  = state.phase2_orig_start if state.phase2_orig_start else state.start_cell
    e  = state.end_cell
    cp = state.checkpoint_cell
    walls = state.walls
    vis = vis or set()
    front = front or set()
    ps = set(path) if path else set()
    grid = []
    for r in range(rows):
        for c in range(cols):
            pos = (r, c)
            if pos == s:          grid.append(2)
            elif pos == e:        grid.append(3)
            elif cp and pos == cp: grid.append(7)
            elif pos in walls:    grid.append(1)
            elif pos in ps:       grid.append(6)
            elif pos in front:    grid.append(5)
            elif pos in vis:      grid.append(4)
            elif pos in state.terrain: grid.append(state.terrain[pos])
            else:                 grid.append(0)
    return grid


# ─── Tree layout (same algorithm as gui.py) ──────────────────
_TREE_MAX = 400

def _compute_tree(came_from, start, path_cells):
    if not came_from or start not in came_from:
        return [], [], (0, 0)
    path_set = set(path_cells)
    children = {}
    for node, parent in came_from.items():
        if parent is not None:
            children.setdefault(parent, []).append(node)
    relevant = set()
    for node in path_cells:
        relevant.add(node)
        for ch in children.get(node, []):
            relevant.add(ch)
    queue = deque([start])
    order, in_order = [], set()
    while queue and len(order) < _TREE_MAX:
        node = queue.popleft()
        if node in in_order or node not in relevant:
            continue
        in_order.add(node); order.append(node)
        for ch in children.get(node, []):
            if ch not in in_order and ch in relevant:
                queue.append(ch)
    if not order:
        return [], [], (0, 0)
    filt = {}
    for n in order:
        ch = [c for c in children.get(n, []) if c in in_order]
        if ch: filt[n] = ch
    level = {start: 0}
    for n in order:
        for c in filt.get(n, []):
            if c not in level:
                level[c] = level[n] + 1
    width = {}
    for n in reversed(order):
        chs = filt.get(n, [])
        width[n] = max(1, sum(width.get(c, 1) for c in chs)) if chs else 1
    root_w = width.get(start, 1)
    if root_w > 40:
        f = 40 / root_w
        for n in order:
            width[n] = max(0.3, width[n] * f)
    x_start = {start: 0.0}
    for n in order:
        cx = x_start.get(n, 0.0)
        for c in filt.get(n, []):
            if c not in x_start:
                x_start[c] = cx
                cx += width.get(c, 1)
    # Even spacing per level: each row of nodes is evenly distributed
    by_level = {}
    for n in order:
        lv = level[n]
        if lv not in by_level:
            by_level[lv] = []
        by_level[lv].append(n)

    max_count = max(len(v) for v in by_level.values())
    tree_w = float(max(max_count - 1, 1))

    pos_x = {}
    for lv in sorted(by_level.keys()):
        nodes = sorted(by_level[lv], key=lambda n: x_start.get(n, 0))
        count = len(nodes)
        if count == 1:
            pos_x[nodes[0]] = tree_w / 2.0
        else:
            for i, n in enumerate(nodes):
                pos_x[n] = tree_w * i / (count - 1)
    positions, edges = [], []
    mx = my = 0.0
    for n in order:
        px, py = pos_x.get(n, 0), float(level.get(n, 0))
        positions.append((n, px, py, n in path_set))
        if px > mx: mx = px
        if py > my: my = py
    for n in order:
        for c in filt.get(n, []):
            positions  # just use positions
            edges.append((n, c, n in path_set and c in path_set))
    return positions, edges, (mx + 1.0, my + 1.0)


def _get_tree_data():
    global _tree_cache_key, _tree_cache
    if not state.came_from:
        return None
    key = (id(state.came_from), len(state.came_from), state.start_cell)
    if key == _tree_cache_key and _tree_cache is not None:
        return _tree_cache
    _tree_cache_key = key
    positions, edges, bounds = _compute_tree(
        state.came_from, state.start_cell, state.path_cells)
    if not positions:
        _tree_cache = None
        return None
    _tree_cache = {
        "positions": [
            {"node": [n[0], n[1]], "x": px, "y": py, "ip": ip}
            for n, px, py, ip in positions
        ],
        "edges": [
            {"from": [p[0], p[1]], "to": [c[0], c[1]], "ip": ip}
            for p, c, ip in edges
        ],
        "bounds": [bounds[0], bounds[1]],
        "start": list(state.start_cell),
        "end": list(state.end_cell),
        "shown": len(positions),
        "total": len(state.came_from),
        "algo": _last_alg_name,
    }
    return _tree_cache


# ─── Checkpoint wrapper ───────────────────────────────────────
def _checkpoint_wrap(algo_func):
    """Generator: runs algo Start→Checkpoint then Checkpoint→End."""
    orig_start = state.start_cell
    orig_end   = state.end_cell
    cp         = state.checkpoint_cell

    try:
        # ── Phase 1: start → checkpoint ──
        state.end_cell = cp
        gen1 = algo_func()
        vis1 = set()
        try:
            while True:
                vis, front = next(gen1)
                vis1 = set(vis)
                yield vis, front
        except StopIteration:
            pass

        path1   = list(state.path_cells)
        found1  = state.stats.get("found")
        nodes1  = state.stats.get("nodes", 0)
        cost1   = state.stats.get("cost", 0)
        time1   = state.stats.get("time", 0.0)

        if not found1:
            state.finished = True
            return

        # Reset for phase 2 — keep path1 visible as partial path
        state.finished    = False
        state.path_cells  = path1   # stay orange so user sees Start→CP path
        state.came_from   = {}
        state.vis_cells   = set()
        state.front_cells = set()
        state.stats       = {"nodes": 0, "path": 0, "cost": 0, "time": 0.0, "found": None}

        # ── Phase 2: checkpoint → end ──
        state.start_cell       = cp
        state.end_cell         = orig_end
        state.phase2_orig_start = orig_start  # keep green dot at original position
        gen2 = algo_func()
        try:
            while True:
                vis2, front2 = next(gen2)
                # Subtract vis1 so already-blue cells never turn purple
                yield vis1 | vis2, front2 - vis1
        except StopIteration:
            pass

        path2  = list(state.path_cells)
        found2 = state.stats.get("found")
        nodes2 = state.stats.get("nodes", 0)
        cost2  = state.stats.get("cost", 0)
        time2  = state.stats.get("time", 0.0)

        if found2 and path1 and path2:
            combined = path1 + path2[1:]
            state.path_cells = combined
            state.stats.update(nodes=nodes1+nodes2, path=len(combined),
                               cost=cost1+cost2, time=time1+time2, found=True)
        else:
            state.stats.update(nodes=nodes1+nodes2, found=False, time=time1+time2)
        state.came_from = {}
        state.finished  = True

    finally:
        # Always restore original start/end (even if cancelled mid-phase)
        state.start_cell        = orig_start
        state.end_cell          = orig_end
        state.phase2_orig_start = None


# ─── Routes ───────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html",
                           algo_names=ALG_NAMES, algo_full=ALG_FULL)


@app.route("/api/state")
def api_state():
    return jsonify({
        "rows": state.rows, "cols": state.cols,
        "grid": _grid_array(state.vis_cells, state.front_cells, state.path_cells),
        "running": state.running,
        "finished": state.finished,
        "paused": state.paused,
        "step_ptr": state.step_ptr,
        "path_cells": [list(p) for p in state.path_cells],
        "cur_alg": state.cur_alg,
        "speed": state.speed,
        "set_mode": state.set_mode,
        "stats": state.stats,
        "has_tree": bool(state.came_from) and state.finished,
        "show_tree": _show_tree,
        "algo_name": _last_alg_name,
        "checkpoint": list(state.checkpoint_cell) if state.checkpoint_cell else None,
        "maze_running": False,
    })


@app.route("/api/race")
def api_race():
    rd = {}
    for idx in _race_order:
        runner = _race_runners.get(idx)
        if runner:
            rd[str(idx)] = {
                "name": ALG_NAMES[idx],
                "done": runner.get("done", False),
                "grid": _grid_array(runner.get("vis", set()),
                                    runner.get("front", set()),
                                    runner.get("path", [])),
                "stats": runner.get("stats"),
            }
        else:
            rd[str(idx)] = {
                "name": ALG_NAMES[idx],
                "done": False,
                "grid": _grid_array(),
                "stats": None,
            }
    return jsonify({
        "order": _race_order,
        "running": _race_running,
        "paused": _race_paused,
        "done": _race_done,
        "step_ptr": _race_step_ptr,
        "runners": rd,
        "results": _race_results if _race_done else None,
    })


@app.route("/api/tree")
def api_tree():
    if not _show_tree:
        return jsonify(None)
    return jsonify(_get_tree_data())


@app.route("/api/action", methods=["POST"])
def api_action():
    global _last_alg_name, _show_tree
    global _race_order, _race_runners, _race_running, _race_paused, _race_done, _race_results, _race_thread
    global _race_step_history, _race_step_ptr

    d = request.json
    act = d.get("action")

    if act == "select_algo":
        idx = int(d.get("idx", 0))
        if 0 <= idx < len(ALG_NAMES):
            if state.running:
                state.clear_search()
            state.cur_alg = idx

    elif act == "run":
        if state.running:
            # Pause — don't snapshot here; step history only built by ▶ button
            state.running = False
            state.paused  = True
        elif state.paused:
            # Continue — restore to latest stepped state so gen matches display
            if state.step_history:
                vis, front = state.step_history[-1]
                state.vis_cells   = set(vis)
                state.front_cells = set(front)
            state.step_history.clear()
            state.step_ptr = -1
            state.paused  = False
            state.running = True
            _start_algo_thread()
        else:
            # Fresh start
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

    elif act == "step":
        if state.finished:
            pass  # nothing to step when finished
        else:
            # Initialize generator if not yet started
            if not state.alg_gen:
                func = ALGO_FUNCS[state.cur_alg]
                if state.checkpoint_cell:
                    state.start_algorithm(lambda f=func: _checkpoint_wrap(f))
                else:
                    state.start_algorithm(func)
                _last_alg_name = ALG_NAMES[state.cur_alg]
                state.running = False
            state.running = False
            state.paused  = True
            # Restore from cached future (user stepped back then forward)
            if state.step_ptr < len(state.step_history) - 1:
                state.step_ptr += 1
                vis, front = state.step_history[state.step_ptr]
                state.vis_cells   = set(vis)
                state.front_cells = set(front)
            elif state.alg_gen and not state.finished:
                # Save baseline before first step so step_back can return here
                if not state.step_history:
                    state.step_history.append((set(state.vis_cells), set(state.front_cells)))
                    state.step_ptr = 0
                # Advance exactly one node expansion
                try:
                    vis, front = next(state.alg_gen)
                    state.vis_cells   = vis
                    state.front_cells = front
                    if len(state.step_history) < 2000:
                        state.step_history.append((set(vis), set(front)))
                        state.step_ptr = len(state.step_history) - 1
                except StopIteration:
                    state.running  = False
                    state.finished = True

    elif act == "step_back":
        if state.step_ptr > 0:
            state.step_ptr -= 1
            vis, front = state.step_history[state.step_ptr]
            state.vis_cells   = set(vis)
            state.front_cells = set(front)
        # step_ptr == 0: already at baseline, cannot go further back

    elif act == "cancel_algo":
        state.clear_search()
        _show_tree = False

    elif act == "clear":
        state.clear_search()
        _show_tree = False

    elif act == "maze":
        state.clear_search()
        _show_tree = False
        generate_maze()

    elif act == "set_checkpoint":
        r, c = int(d["r"]), int(d["c"])
        pos = (r, c)
        if pos not in (state.start_cell, state.end_cell):
            state.checkpoint_cell = pos
            state.clear_search()

    elif act == "remove_checkpoint":
        state.checkpoint_cell = None
        state.clear_search()

    elif act == "reset":
        state.clear_search()
        state.walls.clear()
        state.terrain.clear()
        _show_tree = False

    elif act == "speed":
        state.speed = max(1, min(MAX_SPEED, int(d.get("value", 20))))

    elif act == "set_mode":
        m = d.get("mode")
        state.set_mode = m if state.set_mode != m else None

    elif act == "set_start":
        r, c = int(d["r"]), int(d["c"])
        pos = (r, c)
        if pos != state.end_cell and 0 <= r < state.rows and 0 <= c < state.cols:
            state.start_cell = pos

    elif act == "set_end":
        r, c = int(d["r"]), int(d["c"])
        pos = (r, c)
        if pos != state.start_cell and 0 <= r < state.rows and 0 <= c < state.cols:
            state.end_cell = pos

    elif act == "grid_cell":
        r, c = int(d["r"]), int(d["c"])
        pos = (r, c)
        if state.set_mode == "start":
            state.start_cell = pos
            state.set_mode = None
        elif state.set_mode == "end":
            state.end_cell = pos
            state.set_mode = None
        elif not state.running:
            if pos not in (state.start_cell, state.end_cell):
                if d.get("remove"):
                    state.walls.discard(pos)
                else:
                    state.walls.add(pos)
                    state.terrain.pop(pos, None)  # walls replace terrain

    elif act == "change_grid":
        dr, dc = int(d.get("dr", 0)), int(d.get("dc", 0))
        nr = max(MIN_R, min(MAX_R, state.rows + dr))
        nc = max(MIN_C, min(MAX_C, state.cols + dc))
        if nr != state.rows or nc != state.cols:
            state.clear_search()
            state.walls.clear()
            state.terrain.clear()
            state.checkpoint_cell = None
            state.rows, state.cols = nr, nc
            sr, sc = state.start_cell
            state.start_cell = (min(sr, nr - 1), min(sc, nc - 1))
            er, ec = state.end_cell
            state.end_cell = (min(er, nr - 1), min(ec, nc - 1))
            if state.start_cell == state.end_cell:
                state.end_cell = (nr - 1, nc - 1)

    elif act == "set_grid":
        nr = max(MIN_R, min(MAX_R, int(d.get("rows", state.rows))))
        nc = max(MIN_C, min(MAX_C, int(d.get("cols", state.cols))))
        if nr != state.rows or nc != state.cols:
            state.clear_search()
            state.walls.clear()
            state.terrain.clear()
            state.checkpoint_cell = None
            state.rows, state.cols = nr, nc
            sr, sc = state.start_cell
            state.start_cell = (min(sr, nr - 1), min(sc, nc - 1))
            er, ec = state.end_cell
            state.end_cell = (min(er, nr - 1), min(ec, nc - 1))
            if state.start_cell == state.end_cell:
                state.end_cell = (nr - 1, nc - 1)

    elif act == "set_terrain":
        r, c = int(d["r"]), int(d["c"])
        pos = (r, c)
        terrain_type = int(d.get("terrain", 0))
        if (pos not in (state.start_cell, state.end_cell)
                and pos != state.checkpoint_cell
                and pos not in state.walls
                and not state.running):
            if terrain_type == 0:
                state.terrain.pop(pos, None)
            else:
                state.terrain[pos] = terrain_type

    elif act == "clear_terrain":
        state.terrain.clear()

    elif act == "weighted_maze":
        state.clear_search()
        _show_tree = False
        generate_plain_terrain()

    elif act == "toggle_tree":
        if state.finished and state.came_from:
            _show_tree = not _show_tree

    elif act == "race_toggle":
        idx = int(d.get("idx", -1))
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

    elif act == "race_start":
        if _race_running:
            # Pause
            _race_running = False
            _race_paused  = True
        elif _race_paused and _race_runners and not _race_done:
            # Continue
            _race_paused  = False
            _race_running = True
            _race_thread  = threading.Thread(target=_race_loop, daemon=True)
            _race_thread.start()
        elif len(_race_order) >= 2:
            _start_race()

    elif act == "race_cancel":
        _race_running = False
        _race_paused  = False
        _race_done    = False
        _race_results = []
        _race_runners = {}
        _race_step_history.clear()
        _race_step_ptr = -1

    elif act == "race_step":
        if len(_race_order) >= 2:
            if not _race_runners:
                _init_race()
            _race_running = False
            _race_paused  = True
            if _race_step_ptr < len(_race_step_history) - 1:
                # Restore from cached future
                _race_step_ptr += 1
                snap = _race_step_history[_race_step_ptr]
                for idx, (vis, front) in snap.items():
                    r = _race_runners.get(idx)
                    if r:
                        r["vis"] = set(vis); r["front"] = set(front)
            elif not _race_done:
                # Save baseline before first step so step_back can return here
                if not _race_step_history:
                    baseline = {idx: (set(_race_runners[idx]["vis"]), set(_race_runners[idx]["front"]))
                                for idx in _race_order if _race_runners.get(idx)}
                    _race_step_history.append(baseline)
                    _race_step_ptr = 0
                # Advance all runners one yield
                snap = {}
                for idx in _race_order:
                    runner = _race_runners.get(idx)
                    if not runner or runner["done"]:
                        snap[idx] = (set(runner["vis"] if runner else []),
                                     set(runner["front"] if runner else []))
                        continue
                    try:
                        vis, front = next(runner["gen"])
                        runner["vis"]   = vis
                        runner["front"] = front.copy() if hasattr(front, "copy") else set(front)
                        snap[idx] = (set(vis), set(runner["front"]))
                    except StopIteration:
                        runner["done"]  = True
                        runner["path"]  = list(state.path_cells)
                        runner["stats"] = dict(state.stats)
                        state.clear_search()
                        snap[idx] = (set(runner["vis"]), set())
                if len(_race_step_history) < 300:
                    _race_step_history.append(snap)
                    _race_step_ptr = len(_race_step_history) - 1
                # Check all done
                if all(_race_runners.get(i, {}).get("done", False) for i in _race_order):
                    _race_done = True
                    _race_running = False
                    _race_results = [
                        {"name": ALG_NAMES[i], **_race_runners[i]["stats"]}
                        for i in _race_order
                        if _race_runners.get(i) and _race_runners[i].get("stats")
                    ]

    elif act == "race_step_back":
        if _race_step_ptr > 0:
            _race_step_ptr -= 1
            snap = _race_step_history[_race_step_ptr]
            for idx, (vis, front) in snap.items():
                r = _race_runners.get(idx)
                if r:
                    r["vis"] = set(vis); r["front"] = set(front)
        # _race_step_ptr == 0: at baseline, cannot go further back

    elif act == "race_stop":
        _race_running = False
        _race_done    = True
        _race_results = [
            {"name": ALG_NAMES[i], **_race_runners[i]["stats"]}
            for i in _race_order
            if _race_runners.get(i) and _race_runners[i].get("stats")
        ]

    return jsonify({"ok": True})


# ─── Algorithm thread ─────────────────────────────────────────
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
            except Exception as e:
                print(f"[Algo error] {e}")
                state.running = False
                break
        time.sleep(1 / 60)


# ─── Race thread ──────────────────────────────────────────────
def _init_race():
    """Set up race generators without starting thread (used for step mode too)."""
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
            "vis": set(), "front": set(),
            "done": False, "path": [], "stats": None,
        }
    state.clear_search()


def _start_race():
    global _race_running, _race_paused, _race_thread
    _init_race()
    _race_running = True
    _race_paused  = False
    _race_thread  = threading.Thread(target=_race_loop, daemon=True)
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
                    runner["front"] = front.copy() if hasattr(front, "copy") else set(front)
                except StopIteration:
                    runner["done"] = True
                    runner["path"] = list(state.path_cells)
                    runner["stats"] = dict(state.stats)
                    state.clear_search()
                    break
                except Exception as e:
                    print(f"[Race error] {ALG_NAMES[idx]}: {e}")
                    runner["done"] = True
                    runner["stats"] = {"nodes": 0, "path": 0, "cost": 0,
                                       "time": 0.0, "found": None}
                    state.clear_search()
                    break
        if all_done:
            _race_running = False
            _race_done = True
            _race_results = [
                {"name": ALG_NAMES[idx], **_race_runners[idx]["stats"]}
                for idx in _race_order
                if _race_runners.get(idx) and _race_runners[idx].get("stats")
            ]
            break
        time.sleep(1 / 60)



# ─── Entry point ──────────────────────────────────────────────
if __name__ == "__main__":
    print("\n  Maze Pathfinding Visualizer (Web)")
    print("  Open: http://localhost:5000\n")
    app.run(debug=False, port=5000, threaded=True)
