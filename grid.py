import random
from config import DIRS, state

# ─────────────────────────────────────────────
# GRID HELPERS
# ─────────────────────────────────────────────
def in_bounds(r, c):
    return 0 <= r < state.rows and 0 <= c < state.cols

def get_neighbors(r, c):
    """
    Trả về danh sách các ô (r, c) hợp lệ xung quanh.
    Lưu ý: Nó truy cập trực tiếp state.walls từ config để biết ô nào là tường.
    """
    return [
        (r + dr, c + dc)
        for dr, dc in DIRS
        if in_bounds(r + dr, c + dc) and (r + dr, c + dc) not in state.walls
    ]

def heuristic(a, b):
    """Tính khoảng cách Manhattan giữa 2 điểm (dành cho A*, Greedy)."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def reconstruct_path(came_from, node):
    """Lần ngược từ node đích về node bắt đầu để tạo đường đi."""
    path = []
    while node is not None:
        path.append(node)
        node = came_from.get(node)
    return list(reversed(path))

def next_id():
    """Hỗ trợ tie-breaking cho heapq khi 2 node có cùng cost."""
    state._counter[0] += 1
    return state._counter[0]


# ─────────────────────────────────────────────
# TERRAIN / WEIGHTED COSTS
# ─────────────────────────────────────────────
# cell type → movement cost  (8=deep water, 9=swamp, 10=grass)
TERRAIN_COSTS = {8: 10, 9: 5, 10: 2}

def get_terrain_cost(pos):
    """Returns movement cost to enter a cell (default 1 for empty/road)."""
    return TERRAIN_COSTS.get(state.terrain.get(pos), 1)

def path_cost(path):
    """Actual terrain-weighted cost of a path (sum of entry costs, skipping start)."""
    return sum(get_terrain_cost(cell) for cell in path[1:])


# ─────────────────────────────────────────────
# MAZE GENERATION  (Recursive Division)
# ─────────────────────────────────────────────
def generate_maze():
    rows, cols = state.rows, state.cols
    state.walls = set()
    for r in range(rows):
        state.walls.add((r, 0));  state.walls.add((r, cols - 1))
    for c in range(cols):
        state.walls.add((0, c));  state.walls.add((rows - 1, c))

    def divide(r1, c1, r2, c2):
        w = c2 - c1;  h = r2 - r1
        if w < 2 or h < 2:  return
        horizontal = h > w if h != w else random.random() < 0.5
        if horizontal:
            wr = random.choice(list(range(r1 + 1, r2, 2)) or [r1 + 1])
            pc = random.choice(list(range(c1, c2 + 1, 2)) or [random.randrange(c1, c2 + 1)])
            for c in range(c1, c2 + 1):
                if c != pc:  state.walls.add((wr, c))
            divide(r1, c1, wr - 1, c2);  divide(wr + 1, c1, r2, c2)
        else:
            wc = random.choice(list(range(c1 + 1, c2, 2)) or [c1 + 1])
            pr = random.choice(list(range(r1, r2 + 1, 2)) or [random.randrange(r1, r2 + 1)])
            for r in range(r1, r2 + 1):
                if r != pr:  state.walls.add((r, wc))
            divide(r1, c1, r2, wc - 1);  divide(r1, wc + 1, r2, c2)

    divide(1, 1, rows - 2, cols - 2)
    _clear_around_markers(rows, cols)


def generate_maze_gen():
    """Animated maze generation — reveals walls in clockwise spiral order."""
    rows, cols = state.rows, state.cols
    # Compute the complete maze first
    generate_maze()
    target_walls = frozenset(state.walls)
    state.walls = set()          # reset; animation will fill it in

    # Build clockwise spiral traversal of all cells (outside → inside)
    spiral = []
    top, bottom, left, right = 0, rows - 1, 0, cols - 1
    while top <= bottom and left <= right:
        for c in range(left, right + 1):       spiral.append((top,    c))
        for r in range(top + 1, bottom + 1):   spiral.append((r,      right))
        if top < bottom:
            for c in range(right - 1, left - 1, -1): spiral.append((bottom, c))
        if left < right:
            for r in range(bottom - 1, top, -1):     spiral.append((r,      left))
        top += 1; bottom -= 1; left += 1; right -= 1

    for pos in spiral:
        if pos in target_walls:
            state.walls.add(pos)
            yield                # yield after each wall cell


def generate_plain_terrain():
    """Fill the entire grid with random terrain — no walls at all."""
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
                    state.terrain[pos] = 8    # deep water (18%)
                elif rnd < 0.42:
                    state.terrain[pos] = 9    # swamp (24%)
                elif rnd < 0.72:
                    state.terrain[pos] = 10   # grass (30%)
                # else: road/empty (28%)


def _clear_around_markers(rows, cols):
    """Remove walls in the 3×3 area around start, end, and checkpoint."""
    pts = [state.start_cell, state.end_cell]
    if state.checkpoint_cell:
        pts.append(state.checkpoint_cell)
    for pt in pts:
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                r, c = pt[0] + dr, pt[1] + dc
                if 0 < r < rows - 1 and 0 < c < cols - 1:
                    state.walls.discard((r, c))
