import time
from collections import deque
from core.grid import get_neighbors, reconstruct_path, path_cost
from core.state import state


def algo_dfs():
    s, e = state.start_cell, state.end_cell
    elapsed = 0.0
    t_step = time.perf_counter()
    stack     = deque([s])
    came_from = {s: None}
    visited   = set()
    peak_mem  = 0

    while stack:
        curr = stack.pop()
        if curr in visited:
            continue
        visited.add(curr)

        if curr == e:
            p = reconstruct_path(came_from, e)
            state.path_cells = p
            state.stats.update(nodes=len(visited), path=len(p),
                               cost=path_cost(p), time=elapsed + (time.perf_counter() - t_step), found=True,
                               iterations=1, peak_memory=peak_mem)
            state.came_from = came_from
            state.finished = True
            return

        for nb in get_neighbors(*curr):
            if nb not in visited:
                if nb not in came_from:
                    came_from[nb] = curr
                stack.append(nb)

        peak_mem = max(peak_mem, len(came_from) + len(stack))
        elapsed += time.perf_counter() - t_step
        yield visited.copy(), set(stack)
        t_step = time.perf_counter()

    state.stats.update(nodes=len(visited), found=False, time=elapsed + (time.perf_counter() - t_step),
                       iterations=1, peak_memory=peak_mem)
    state.came_from = came_from
    state.finished = True
