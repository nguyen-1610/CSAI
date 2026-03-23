import time
from core.grid import get_neighbors, reconstruct_path, heuristic, path_cost
from core.state import state

# Số lượng node tối đa được giữ lại sau mỗi bước mở rộng
BEAM_WIDTH = 8


def algo_beam():
    s, e = state.start_cell, state.end_cell
    elapsed = 0.0
    t_step = time.perf_counter()

    came_from = {s: None}
    visited   = set()
    # beam là tập node đang xét ở "tầng" hiện tại (khác BFS: không giữ toàn bộ queue)
    beam      = [s]

    while beam:
        next_candidates = []

        for curr in beam:
            if curr in visited:
                continue
            visited.add(curr)

            if curr == e:
                p = reconstruct_path(came_from, e)
                state.path_cells = p
                state.stats.update(nodes=len(visited), path=len(p),
                                   cost=path_cost(p), time=elapsed + (time.perf_counter() - t_step), found=True)
                state.came_from = came_from
                state.finished = True
                return

            for nb in get_neighbors(*curr):
                # came_from dùng để kiểm tra đã được xếp vào candidates chưa,
                # tránh thêm cùng 1 node từ nhiều cha khác nhau
                if nb not in visited and nb not in came_from:
                    came_from[nb] = curr
                    next_candidates.append(nb)

        # Sắp xếp tất cả ứng viên theo heuristic (Manhattan đến đích) tăng dần,
        # sau đó CẮT BỚT chỉ giữ BEAM_WIDTH node triển vọng nhất.
        # Đây là điểm khác biệt cốt lõi: các node bị loại sẽ KHÔNG BAO GIỜ được xét lại
        # → thuật toán nhanh nhưng có thể bỏ sót đường đi nếu đường đúng nằm ngoài beam
        next_candidates.sort(key=lambda n: heuristic(n, e))
        beam = next_candidates[:BEAM_WIDTH]

        elapsed += time.perf_counter() - t_step
        yield visited.copy(), set(beam)
        t_step = time.perf_counter()

    state.stats.update(nodes=len(visited), found=False, time=elapsed + (time.perf_counter() - t_step))
    state.came_from = came_from
    state.finished = True
