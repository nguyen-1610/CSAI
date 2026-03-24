import time
import heapq
from core.grid import get_neighbors, reconstruct_path, next_id, get_terrain_cost
from core.state import state
from algorithms._contract import finalize_failure, finalize_success


def algo_ucs():
    s, e = state.start_cell, state.end_cell
    elapsed = 0.0
    t_step = time.perf_counter()
    heap = [(0, next_id(), s)]
    came_from = {s: None}
    cost_so_far = {s: 0}
    visited = set()
    peak_mem = 0

    while heap:
        cost, _, curr = heapq.heappop(heap)
        if curr in visited:
            continue
        visited.add(curr)

        if curr == e:
            p = reconstruct_path(came_from, e)
            finalize_success(
                p,
                came_from,
                len(visited),
                cost,
                elapsed + (time.perf_counter() - t_step),
                iterations=1,
                peak_memory=peak_mem,
            )
            return

        for nb in get_neighbors(*curr):
            new_cost = cost + get_terrain_cost(nb)
            if nb not in cost_so_far or new_cost < cost_so_far[nb]:
                cost_so_far[nb] = new_cost
                came_from[nb] = curr
                heapq.heappush(heap, (new_cost, next_id(), nb))

        peak_mem = max(peak_mem, len(visited) + len(cost_so_far))
        frontier = {item[2] for item in heap}
        elapsed += time.perf_counter() - t_step
        yield visited.copy(), frontier
        t_step = time.perf_counter()

    finalize_failure(
        came_from,
        len(visited),
        elapsed + (time.perf_counter() - t_step),
        iterations=1,
        peak_memory=peak_mem,
    )
