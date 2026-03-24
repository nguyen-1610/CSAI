import time

from algorithms._contract import finalize_failure, finalize_success
from core.grid import get_neighbors, heuristic, path_cost, reconstruct_path
from core.state import state

# Number of nodes kept after each expansion round.
BEAM_WIDTH = 8


def algo_beam():
    s, e = state.start_cell, state.end_cell
    elapsed = 0.0
    t_step = time.perf_counter()
    came_from = {s: None}
    visited = set()
    beam = [s]
    peak_mem = 1

    if s == e:
        finalize_success([s], came_from, 1, 0, 0.0, iterations=1, peak_memory=peak_mem)
        return

    while beam:
        next_candidates = []

        for curr in beam:
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
                    next_candidates.append(nb)

        next_candidates.sort(key=lambda n: heuristic(n, e))
        beam = next_candidates[:BEAM_WIDTH]

        peak_mem = max(peak_mem, len(visited) + len(beam))
        elapsed += time.perf_counter() - t_step
        yield visited.copy(), set(beam)
        t_step = time.perf_counter()

    finalize_failure(
        came_from,
        len(visited),
        elapsed + (time.perf_counter() - t_step),
        iterations=1,
        peak_memory=peak_mem,
    )
