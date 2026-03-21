import time
from core.grid import get_neighbors, reconstruct_path, heuristic, get_terrain_cost, path_cost
from core.state import state


def algo_idastar():
    s, e = state.start_cell, state.end_cell
    t0 = time.perf_counter()
    total_visited = set()

    if s == e:
        state.path_cells = [s]
        state.stats.update(nodes=1, path=1, cost=0,
                           time=time.perf_counter() - t0, found=True)
        state.came_from = {s: None}
        state.finished = True
        return

    threshold = heuristic(s, e)

    while True:
        min_exceeded = float('inf')
        found = False
        came_from = {s: None}
        path_set = {s}
        total_visited.add(s)

        # Iterative DFS stack: (node, g, child_index, children_list)
        init_children = [nb for nb in get_neighbors(*s) if nb not in path_set]
        stack = [(s, 0, 0, init_children)]

        while stack:
            node, g, child_idx, children = stack[-1]

            if child_idx >= len(children):
                # All children explored — backtrack
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

            # Visit nb
            came_from[nb] = node
            total_visited.add(nb)
            path_set.add(nb)

            yield total_visited.copy(), set()

            if nb == e:
                found = True
                break

            nb_children = [c for c in get_neighbors(*nb) if c not in path_set]
            stack.append((nb, g + step, 0, nb_children))

        if found:
            p = reconstruct_path(came_from, e)
            state.path_cells = p
            state.stats.update(nodes=len(total_visited), path=len(p),
                               cost=path_cost(p), time=time.perf_counter() - t0, found=True)
            state.came_from = came_from
            state.finished = True
            return

        if min_exceeded == float('inf'):
            break

        threshold = min_exceeded
        yield total_visited.copy(), set()   # show progress between iterations

    state.stats.update(nodes=len(total_visited), found=False,
                       time=time.perf_counter() - t0)
    state.came_from = came_from
    state.finished = True
