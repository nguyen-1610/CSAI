import time
from config import state
from grid import get_neighbors, reconstruct_path


def algo_iddfs():
    s, e = state.start_cell, state.end_cell
    t0 = time.perf_counter()
    total_visited = set()

    def dls(node, limit, came_from, visited, path_set):
        """Recursive Depth-Limited Search. Returns True if goal found."""
        visited.add(node)
        if node == e:
            return True
        if limit <= 0:
            return False
        for nb in get_neighbors(*node):
            if nb not in path_set:
                came_from[nb] = node
                path_set.add(nb)
                if dls(nb, limit - 1, came_from, visited, path_set):
                    return True
                path_set.discard(nb)
        return False

    depth = 0
    while True:
        came_from = {s: None}
        visited = set()
        path_set = {s}

        found = dls(s, depth, came_from, visited, path_set)
        total_visited |= visited

        if found:
            p = reconstruct_path(came_from, e)
            state.path_cells = p
            state.stats.update(nodes=len(total_visited), path=len(p),
                               cost=len(p) - 1, time=time.perf_counter() - t0,
                               found=True)
            state.finished = True
            return

        # yield sau mỗi vòng lặp depth để animation hiển thị tiến trình
        yield total_visited.copy(), set()

        # nếu không mở rộng thêm node mới => không có đường
        if len(visited) <= len(total_visited) - len(visited) + 1 and depth > 0:
            pass  # tiếp tục tăng depth

        depth += 1

        # giới hạn depth tránh vòng lặp vô tận trên lưới hữu hạn
        from config import ROWS, COLS
        if depth > ROWS * COLS:
            break

    state.stats.update(nodes=len(total_visited), found=False,
                       time=time.perf_counter() - t0)
    state.finished = True
