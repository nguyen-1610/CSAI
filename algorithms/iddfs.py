import time

from algorithms._contract import finalize_failure, finalize_success
from core.grid import get_neighbors, path_cost, reconstruct_path
from core.state import state


def algo_iddfs():
    s, e = state.start_cell, state.end_cell
    elapsed = 0.0
    t_step = time.perf_counter()
    total_visited = {s}
    came_from = {s: None}
    peak_mem = 1

    if s == e:
        finalize_success([s], came_from, 1, 0, 0.0, iterations=1, peak_memory=peak_mem)
        return

    iterations = 0

    previous_depth_had_visible_cells = False

    for depth in range(state.rows * state.cols + 1):
        iterations += 1
        prev_total_count = len(total_visited)
        came_from = {s: None}
        iter_visited = {s}
        path_set = {s}
        visited_at = {s: depth}
        found = False
        stack = [(s, iter(get_neighbors(*s)), depth)]

        # Each depth-limited pass restarts from a clean board in the UI.
        if previous_depth_had_visible_cells:
            elapsed += time.perf_counter() - t_step
            yield set(), set()
            t_step = time.perf_counter()

        while stack:
            node, nb_iter, remaining = stack[-1]

            if remaining <= 0:
                popped_node, _, _ = stack.pop()
                if popped_node != s:
                    path_set.discard(popped_node)
                    came_from.pop(popped_node, None)
                continue

            nb = next(nb_iter, None)

            if nb is None:
                popped_node, _, _ = stack.pop()
                if popped_node != s:
                    path_set.discard(popped_node)
                    came_from.pop(popped_node, None)
                continue

            if nb in path_set:
                continue

            new_budget = remaining - 1
            if visited_at.get(nb, -1) >= new_budget:
                continue
            visited_at[nb] = new_budget

            total_visited.add(nb)
            iter_visited.add(nb)
            came_from[nb] = node
            path_set.add(nb)
            peak_mem = max(peak_mem, len(path_set))

            if nb == e:
                found = True
                break

            elapsed += time.perf_counter() - t_step
            yield iter_visited.copy(), path_set.copy()
            t_step = time.perf_counter()

            if new_budget > 0:
                stack.append((nb, iter(get_neighbors(*nb)), new_budget))
            else:
                path_set.discard(nb)
                came_from.pop(nb, None)

        if found:
            path = reconstruct_path(came_from, e)
            # Once IDDFS completes, show the full explored footprint and clear
            # the frontier because there is no active depth-limited pass left.
            state.vis_cells = total_visited.copy()
            state.front_cells = set()
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

        previous_depth_had_visible_cells = len(iter_visited) > 1
        if previous_depth_had_visible_cells:
            elapsed += time.perf_counter() - t_step
            yield iter_visited.copy(), set()
            t_step = time.perf_counter()

        if depth > 0 and len(total_visited) == prev_total_count:
            state.vis_cells = total_visited.copy()
            state.front_cells = set()
            finalize_failure(
                came_from,
                len(total_visited),
                elapsed + (time.perf_counter() - t_step),
                iterations=iterations,
                peak_memory=peak_mem,
            )
            return

    finalize_failure(
        came_from,
        len(total_visited),
        elapsed + (time.perf_counter() - t_step),
        iterations=iterations,
        peak_memory=peak_mem,
    )
