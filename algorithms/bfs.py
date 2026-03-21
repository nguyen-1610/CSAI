import time
from collections import deque
from core.grid import get_neighbors, reconstruct_path, path_cost
from core.state import state


def algo_bfs():
    s, e = state.start_cell, state.end_cell
    t0 = time.perf_counter()
    # deque cho phép popleft() O(1) — nếu dùng list thì pop(0) sẽ là O(n)
    queue     = deque([s])
    # came_from lưu node cha để truy vết đường đi sau khi tìm thấy đích
    came_from = {s: None}
    visited   = set()

    while queue:
        # Lấy node ở đầu hàng đợi (FIFO) — đây là điểm khác biệt cốt lõi so với DFS
        curr = queue.popleft()
        # Bỏ qua nếu đã duyệt (có thể bị thêm vào queue nhiều lần trước khi xử lý)
        if curr in visited:
            continue
        visited.add(curr)

        if curr == e:
            p = reconstruct_path(came_from, e)
            state.path_cells = p
            state.stats.update(nodes=len(visited), path=len(p),
                               cost=path_cost(p), time=time.perf_counter()-t0, found=True)
            state.came_from = came_from
            state.finished = True
            return

        for nb in get_neighbors(*curr):
            # Kiểm tra came_from thay vì visited để tránh thêm cùng 1 node nhiều lần
            # vào queue (tiết kiệm bộ nhớ và tránh duyệt trùng)
            if nb not in visited and nb not in came_from:
                came_from[nb] = curr
                queue.append(nb)

        # Yield snapshot để GUI vẽ animation: visited=đã duyệt, frontier=đang chờ
        yield visited.copy(), set(queue)

    state.stats.update(nodes=len(visited), found=False, time=time.perf_counter()-t0)
    state.came_from = came_from
    state.finished = True
