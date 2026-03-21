import time
import heapq
from core.grid import get_neighbors, reconstruct_path, heuristic, next_id, get_terrain_cost
from core.state import state


def algo_astar():
    s, e = state.start_cell, state.end_cell
    t0 = time.perf_counter()

    g_score = {s: 0}
    came_from = {s: None}
    visited = set()
    # (f, tie-breaker, node)
    open_heap = [(heuristic(s, e), next_id(), s)]
    open_set = {s}

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
                               cost=g_score[e], time=time.perf_counter() - t0, found=True)
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

        yield visited.copy(), open_set.copy()

    state.stats.update(nodes=len(visited), found=False, time=time.perf_counter() - t0)
    state.came_from = came_from
    state.finished = True
