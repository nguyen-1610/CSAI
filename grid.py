import random
from config import ROWS, COLS, DIRS, state

# ─────────────────────────────────────────────
# GRID HELPERS
# ─────────────────────────────────────────────
def in_bounds(r, c):
    return 0 <= r < ROWS and 0 <= c < COLS

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
# MAZE GENERATION  (Recursive Division)
# ─────────────────────────────────────────────
def generate_maze():
    state.walls = set()
    # Tạo tường bao quanh (viền ngoài)
    for r in range(ROWS):
        state.walls.add((r, 0))
        state.walls.add((r, COLS - 1))
    for c in range(COLS):
        state.walls.add((0, c))
        state.walls.add((ROWS - 1, c))

    def divide(r1, c1, r2, c2):
        w = c2 - c1
        h = r2 - r1
        if w < 2 or h < 2:
            return
        horizontal = h > w if h != w else random.random() < 0.5

        if horizontal:
            # Đặt tường ở hàng chẵn (tính từ r1) để đảm bảo parity
            wall_rows = list(range(r1 + 1, r2, 2)) or [r1 + 1]
            wr = random.choice(wall_rows)
            # Mở lối đi ở cột lẻ (tính từ c1)
            pass_cols = list(range(c1, c2 + 1, 2)) or [random.randrange(c1, c2 + 1)]
            pc = random.choice(pass_cols)
            for c in range(c1, c2 + 1):
                if c != pc:
                    state.walls.add((wr, c))
            divide(r1, c1, wr - 1, c2)
            divide(wr + 1, c1, r2, c2)
        else:
            # Đặt tường ở cột chẵn (tính từ c1) để đảm bảo parity
            wall_cols = list(range(c1 + 1, c2, 2)) or [c1 + 1]
            wc = random.choice(wall_cols)
            # Mở lối đi ở hàng lẻ (tính từ r1)
            pass_rows = list(range(r1, r2 + 1, 2)) or [random.randrange(r1, r2 + 1)]
            pr = random.choice(pass_rows)
            for r in range(r1, r2 + 1):
                if r != pr:
                    state.walls.add((r, wc))
            divide(r1, c1, r2, wc - 1)
            divide(r1, wc + 1, r2, c2)

    # Bắt đầu chia từ ô bên trong (chừa viền ngoài)
    divide(1, 1, ROWS - 2, COLS - 2)

    # Đảm bảo khu vực xung quanh điểm Bắt đầu và Kết thúc trống trải
    # Lưu ý: chỉ xóa các ô bên TRONG viền (không đụng đến border)
    for dr in range(-1, 2):
        for dc in range(-1, 2):
            sr, sc = state.start_cell[0] + dr, state.start_cell[1] + dc
            er, ec = state.end_cell[0]   + dr, state.end_cell[1]   + dc
            if 0 < sr < ROWS - 1 and 0 < sc < COLS - 1:
                state.walls.discard((sr, sc))
            if 0 < er < ROWS - 1 and 0 < ec < COLS - 1:
                state.walls.discard((er, ec))