"""Grid helpers, terrain helpers, and maze generation."""

import random

from core.constants import DIRS
from core.state import state


def in_bounds(r, c):
    return 0 <= r < state.rows and 0 <= c < state.cols


def get_neighbors(r, c):
    return [
        (r + dr, c + dc)
        for dr, dc in DIRS
        if in_bounds(r + dr, c + dc) and (r + dr, c + dc) not in state.walls
    ]


def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def reconstruct_path(came_from, node):
    path = []
    while node is not None:
        path.append(node)
        node = came_from.get(node)
    return list(reversed(path))


def next_id():
    state._counter[0] += 1
    return state._counter[0]


TERRAIN_COSTS = {8: 10, 9: 5, 10: 2}


def get_terrain_cost(pos):
    return TERRAIN_COSTS.get(state.terrain.get(pos), 1)


def path_cost(path):
    return sum(get_terrain_cost(cell) for cell in path[1:])


def build_grid_array(vis=None, front=None, path=None):
    """Flat list of cell types used by the frontend canvas renderer."""
    rows, cols = state.rows, state.cols
    s = state.phase2_orig_start if state.phase2_orig_start else state.start_cell
    e = state.end_cell
    cp = state.checkpoint_cell
    walls = state.walls
    vis = vis or set()
    front = front or set()
    path_set = set(path) if path else set()
    grid = []
    for r in range(rows):
        for c in range(cols):
            pos = (r, c)
            if pos == s:
                grid.append(2)
            elif pos == e:
                grid.append(3)
            elif cp and pos == cp:
                grid.append(7)
            elif pos in walls:
                grid.append(1)
            elif pos in path_set:
                grid.append(6)
            elif pos in front:
                grid.append(5)
            elif pos in vis:
                grid.append(4)
            elif pos in state.terrain:
                grid.append(state.terrain[pos])
            else:
                grid.append(0)
    return grid


def generate_maze():
    rows, cols = state.rows, state.cols
    state.walls = set()
    for r in range(rows):
        state.walls.add((r, 0))
        state.walls.add((r, cols - 1))
    for c in range(cols):
        state.walls.add((0, c))
        state.walls.add((rows - 1, c))

    def divide(r1, c1, r2, c2):
        w = c2 - c1
        h = r2 - r1
        if w < 2 or h < 2:
            return
        horizontal = h > w if h != w else random.random() < 0.5
        if horizontal:
            wr = random.choice(list(range(r1 + 1, r2, 2)) or [r1 + 1])
            pc = random.choice(list(range(c1, c2 + 1, 2)) or [random.randrange(c1, c2 + 1)])
            for c in range(c1, c2 + 1):
                if c != pc:
                    state.walls.add((wr, c))
            divide(r1, c1, wr - 1, c2)
            divide(wr + 1, c1, r2, c2)
        else:
            wc = random.choice(list(range(c1 + 1, c2, 2)) or [c1 + 1])
            pr = random.choice(list(range(r1, r2 + 1, 2)) or [random.randrange(r1, r2 + 1)])
            for r in range(r1, r2 + 1):
                if r != pr:
                    state.walls.add((r, wc))
            divide(r1, c1, r2, wc - 1)
            divide(r1, wc + 1, r2, c2)

    divide(1, 1, rows - 2, cols - 2)
    _clear_around_markers(rows, cols)


def generate_maze_gen():
    """Animated maze generation — reveals walls in clockwise spiral order."""
    rows, cols = state.rows, state.cols
    generate_maze()
    target_walls = frozenset(state.walls)
    state.walls = set()

    spiral = []
    top, bottom, left, right = 0, rows - 1, 0, cols - 1
    while top <= bottom and left <= right:
        for c in range(left, right + 1):
            spiral.append((top, c))
        for r in range(top + 1, bottom + 1):
            spiral.append((r, right))
        if top < bottom:
            for c in range(right - 1, left - 1, -1):
                spiral.append((bottom, c))
        if left < right:
            for r in range(bottom - 1, top, -1):
                spiral.append((r, left))
        top += 1
        bottom -= 1
        left += 1
        right -= 1

    for pos in spiral:
        if pos in target_walls:
            state.walls.add(pos)
            yield


def generate_plain_terrain():
    state.walls.clear()
    markers = {state.start_cell, state.end_cell}
    if state.checkpoint_cell:
        markers.add(state.checkpoint_cell)
    state.terrain = {}
    for r in range(state.rows):
        for c in range(state.cols):
            pos = (r, c)
            if pos not in markers:
                rnd = random.random()
                if rnd < 0.18:
                    state.terrain[pos] = 8
                elif rnd < 0.42:
                    state.terrain[pos] = 9
                elif rnd < 0.72:
                    state.terrain[pos] = 10


def _clear_around_markers(rows, cols):
    pts = [state.start_cell, state.end_cell]
    if state.checkpoint_cell:
        pts.append(state.checkpoint_cell)
    for pt in pts:
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                r, c = pt[0] + dr, pt[1] + dc
                if 0 < r < rows - 1 and 0 < c < cols - 1:
                    state.walls.discard((r, c))
