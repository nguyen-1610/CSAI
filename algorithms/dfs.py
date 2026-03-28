import time
from collections import deque

from algorithms._contract import finalize_failure, finalize_success
from core.grid import get_neighbors, path_cost, reconstruct_path
from core.state import state

# Push order for LIFO stack → pop (explore) order: RIGHT, DOWN, LEFT, UP
_PUSH_ORDER = {(-1, 0): 0, (0, -1): 1, (1, 0): 2, (0, 1): 3}


def algo_dfs():
    s, e = state.start_cell, state.end_cell
    elapsed = 0.0
    t_step = time.perf_counter()
    stack = deque([s])
    pending = {s}
    came_from = {s: None}
    visited = set()
    peak_mem = 1

    if s == e:
        finalize_success([s], came_from, 1, 0, 0.0, iterations=1, peak_memory=peak_mem)
        return

    while stack:
        curr = stack.pop()
        pending.discard(curr)
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

        for nb in sorted(
            get_neighbors(*curr),
            key=lambda n: _PUSH_ORDER[(n[0] - curr[0], n[1] - curr[1])],
        ):
            if nb in visited:
                continue
            came_from[nb] = curr
            if nb in pending:
                stack.remove(nb)
            stack.append(nb)
            pending.add(nb)

        peak_mem = max(peak_mem, len(came_from) + len(stack))
        elapsed += time.perf_counter() - t_step
        yield visited.copy(), set(stack)
        t_step = time.perf_counter()

    finalize_failure(
        came_from,
        len(visited),
        elapsed + (time.perf_counter() - t_step),
        iterations=1,
        peak_memory=peak_mem,
    )
