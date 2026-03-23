import time
import heapq
from core.grid import get_neighbors, reconstruct_path, heuristic, next_id, get_terrain_cost
from core.state import state


def algo_astar():
    s, e = state.start_cell, state.end_cell
    elapsed = 0.0
    t_step = time.perf_counter()

    g_score = {s: 0}
    came_from = {s: None}
    visited = set()
    # (f, tie-breaker, node)
    open_heap = [(heuristic(s, e), next_id(), s)]
    open_set = {s}
    peak_mem = 0

    while open_heap:
        f, _, curr = heapq.heappop(open_heap)
        if curr in visited:
            continue
        visited.add(curr)
        open_set.discard(curr)

        if curr == e:
            p = reconstruct_path(came_from, e)
            state.path_cells = p
            state.stats.update(nodes=len(visited), path=len(p),
                               cost=g_score[e], time=elapsed + (time.perf_counter() - t_step), found=True,
                               iterations=1, peak_memory=peak_mem)
            state.came_from = came_from
            state.finished = True
            return

        for nb in get_neighbors(*curr):
            tentative = g_score[curr] + get_terrain_cost(nb)
            if tentative < g_score.get(nb, float('inf')):
                g_score[nb] = tentative
                came_from[nb] = curr
                heapq.heappush(open_heap, (tentative + heuristic(nb, e), next_id(), nb))
                open_set.add(nb)

        peak_mem = max(peak_mem, len(visited) + len(open_set))
        elapsed += time.perf_counter() - t_step
        yield visited.copy(), open_set.copy()
        t_step = time.perf_counter()

    state.stats.update(nodes=len(visited), found=False, time=elapsed + (time.perf_counter() - t_step),
                       iterations=1, peak_memory=peak_mem)
    state.came_from = came_from
    state.finished = True
