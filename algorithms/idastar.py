import time

from algorithms._contract import finalize_failure, finalize_success
from core.grid import get_neighbors, get_terrain_cost, heuristic, path_cost, reconstruct_path
from core.state import state


def algo_idastar():
    s, e = state.start_cell, state.end_cell
    elapsed = 0.0
    t_step = time.perf_counter()
    total_visited = {s}
    peak_mem = 1

    if s == e:
        finalize_success([s], {s: None}, 1, 0, 0.0, iterations=1, peak_memory=peak_mem)
        return

    threshold = heuristic(s, e)
    iterations = 0

    while True:
        iterations += 1
        min_exceeded = float("inf")
        found = False
        came_from = {s: None}
        path_set = {s}

        init_children = [nb for nb in get_neighbors(*s) if nb not in path_set]
        stack = [(s, 0, 0, init_children)]

        while stack:
            node, g, child_idx, children = stack[-1]

            if child_idx >= len(children):
                path_set.discard(node)
                stack.pop()
                continue

            nb = children[child_idx]
            stack[-1] = (node, g, child_idx + 1, children)

            if nb in path_set:
                continue

            step = get_terrain_cost(nb)
            f = (g + step) + heuristic(nb, e)
            if f > threshold:
                if f < min_exceeded:
                    min_exceeded = f
                continue

            came_from[nb] = node
            total_visited.add(nb)
            path_set.add(nb)
            peak_mem = max(peak_mem, len(path_set))

            elapsed += time.perf_counter() - t_step
            yield total_visited.copy(), set()
            t_step = time.perf_counter()

            if nb == e:
                found = True
                break

            nb_children = [c for c in get_neighbors(*nb) if c not in path_set]
            stack.append((nb, g + step, 0, nb_children))

        if found:
            path = reconstruct_path(came_from, e)
            finalize_success(
                path,
                came_from,
                len(total_visited),
                path_cost(path),
                elapsed + (time.perf_counter() - t_step),
                iterations=iterations,
                peak_memory=peak_mem,
            )
            return

        if min_exceeded == float("inf"):
            break

        threshold = min_exceeded
        elapsed += time.perf_counter() - t_step
        yield total_visited.copy(), set()
        t_step = time.perf_counter()

    finalize_failure(
        came_from,
        len(total_visited),
        elapsed + (time.perf_counter() - t_step),
        iterations=iterations,
        peak_memory=peak_mem,
    )
