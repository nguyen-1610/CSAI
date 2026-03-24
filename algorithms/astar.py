import heapq
import time

from algorithms._contract import finalize_failure, finalize_success
from core.grid import get_neighbors, get_terrain_cost, heuristic, next_id, reconstruct_path
from core.state import state


def algo_astar():
    s, e = state.start_cell, state.end_cell
    elapsed = 0.0
    t_step = time.perf_counter()
    g_score = {s: 0}
    came_from = {s: None}
    visited = set()
    open_heap = [(heuristic(s, e), next_id(), s)]
    open_set = {s}
    peak_mem = 1

    if s == e:
        finalize_success([s], came_from, 1, 0, 0.0, iterations=1, peak_memory=peak_mem)
        return

    while open_heap:
        _, _, curr = heapq.heappop(open_heap)
        if curr in visited:
            continue
        visited.add(curr)
        open_set.discard(curr)

        if curr == e:
            path = reconstruct_path(came_from, e)
            finalize_success(
                path,
                came_from,
                len(visited),
                g_score[e],
                elapsed + (time.perf_counter() - t_step),
                iterations=1,
                peak_memory=peak_mem,
            )
            return

        for nb in get_neighbors(*curr):
            tentative = g_score[curr] + get_terrain_cost(nb)
            if tentative < g_score.get(nb, float("inf")):
                g_score[nb] = tentative
                came_from[nb] = curr
                heapq.heappush(open_heap, (tentative + heuristic(nb, e), next_id(), nb))
                open_set.add(nb)

        peak_mem = max(peak_mem, len(visited) + len(open_set))
        elapsed += time.perf_counter() - t_step
        yield visited.copy(), open_set.copy()
        t_step = time.perf_counter()

    finalize_failure(
        came_from,
        len(visited),
        elapsed + (time.perf_counter() - t_step),
        iterations=1,
        peak_memory=peak_mem,
    )
