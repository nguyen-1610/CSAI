import time
from collections import deque
from config import state
from grid import get_neighbors, reconstruct_path, path_cost


def algo_dfs():
    s, e = state.start_cell, state.end_cell
    t0 = time.perf_counter()
    stack     = deque([s])
    came_from = {s: None}
    visited   = set()

    while stack:
        curr = stack.pop()
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
            if nb not in visited:
                if nb not in came_from:
                    came_from[nb] = curr
                stack.append(nb)

        yield visited.copy(), set(stack)

    state.stats.update(nodes=len(visited), found=False, time=time.perf_counter()-t0)
    state.came_from = came_from
    state.finished = True
