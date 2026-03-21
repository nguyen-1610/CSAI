import time
import heapq
from core.grid import get_neighbors, reconstruct_path, next_id, get_terrain_cost
from core.state import state


def algo_ucs():
    s, e = state.start_cell, state.end_cell
    t0 = time.perf_counter()
    # heap lưu tuple (cost, tie_break_id, node)
    # tie_break_id dùng next_id() để tránh Python so sánh tuple khi cost bằng nhau
    # (so sánh 2 tuple (r,c) với nhau sẽ lỗi nếu kiểu không hỗ trợ <)
    heap        = [(0, next_id(), s)]
    came_from   = {s: None}
    # cost_so_far lưu chi phí tốt nhất đã biết để đến mỗi node
    cost_so_far = {s: 0}
    visited     = set()

    while heap:
        # Luôn lấy node có cost thấp nhất ra trước (min-heap)
        cost, _, curr = heapq.heappop(heap)

        # Node có thể bị đẩy vào heap nhiều lần khi tìm được đường rẻ hơn,
        # nếu đã duyệt rồi thì bỏ qua lần xử lý cũ này
        if curr in visited:
            continue
        visited.add(curr)

        if curr == e:
            p = reconstruct_path(came_from, e)
            state.path_cells = p
            # cost ở đây là tổng chi phí thực tế (g-cost), chính xác hơn len(p)-1
            state.stats.update(nodes=len(visited), path=len(p),
                               cost=cost, time=time.perf_counter()-t0, found=True)
            state.came_from = came_from
            state.finished = True
            return

        for nb in get_neighbors(*curr):
            new_cost = cost + get_terrain_cost(nb)
            # Chỉ cập nhật nếu tìm được đường rẻ hơn đường đã biết trước đó
            if nb not in cost_so_far or new_cost < cost_so_far[nb]:
                cost_so_far[nb] = new_cost
                came_from[nb] = curr
                heapq.heappush(heap, (new_cost, next_id(), nb))

        # Trích xuất tập node đang chờ trong heap để GUI hiển thị frontier
        frontier = {item[2] for item in heap}
        yield visited.copy(), frontier

    state.stats.update(nodes=len(visited), found=False, time=time.perf_counter()-t0)
    state.came_from = came_from
    state.finished = True
