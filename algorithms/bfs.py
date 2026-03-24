import time
from collections import deque

from algorithms._contract import finalize_failure, finalize_success
from core.grid import get_neighbors, path_cost, reconstruct_path
from core.state import state


def algo_bfs():
    s, e = state.start_cell, state.end_cell
    elapsed = 0.0
    t_step = time.perf_counter()
    queue = deque([s])
    came_from = {s: None}
    visited = set()
    peak_mem = 1

    if s == e:
        finalize_success([s], came_from, 1, 0, 0.0, iterations=1, peak_memory=peak_mem)
        return

    while queue:
        curr = queue.popleft()
        if curr in visited:
            continue
        visited.add(curr)

        if curr == e:
            path = reconstruct_path(came_from, e)
            finalize_success(
                path,
                came_from,
                len(visited),
                path_cost(path),
                elapsed + (time.perf_counter() - t_step),
                iterations=1,
                peak_memory=peak_mem,
            )
            return

        for nb in get_neighbors(*curr):
            if nb not in visited and nb not in came_from:
                came_from[nb] = curr
                queue.append(nb)

        peak_mem = max(peak_mem, len(came_from) + len(queue))
        elapsed += time.perf_counter() - t_step
        yield visited.copy(), set(queue)
        t_step = time.perf_counter()

    finalize_failure(
        came_from,
        len(visited),
        elapsed + (time.perf_counter() - t_step),
        iterations=1,
        peak_memory=peak_mem,
    )
