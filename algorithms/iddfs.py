import time
from config import state, ROWS, COLS
from grid import get_neighbors, reconstruct_path


def algo_iddfs():
    s, e = state.start_cell, state.end_cell
    t0 = time.perf_counter()
    total_visited = set()
    total_visited.add(s)

    if s == e:
        state.path_cells = [s]
        state.stats.update(nodes=1, path=1, cost=0,
                           time=time.perf_counter() - t0, found=True)
        state.finished = True
        return

    # Pre-check: flood-fill để phát hiện end không liên thông với start
    reachable = {s}
    queue = [s]
    while queue:
        curr = queue.pop()
        for nb in get_neighbors(*curr):
            if nb not in reachable:
                reachable.add(nb)
                queue.append(nb)
    if e not in reachable:
        state.stats.update(nodes=len(reachable), found=False,
                           time=time.perf_counter() - t0)
        state.finished = True
        return

    for depth in range(ROWS * COLS + 1):
        came_from = {s: None}
        path_set = {s}
        # Transposition table: track max budget at which each node was explored.
        # If we reach a node with budget <= previously explored, skip it.
        # This prevents exponential blowup in open/sparse mazes.
        visited_at = {}

        found = False
        stack = [(s, iter(get_neighbors(*s)), depth, [])]

        while stack:
            node, nb_iter, remaining, rollback = stack[-1]
            nb = next(nb_iter, None)

            if nb is None:
                # Hết neighbor → backtrack: pop frame và hoàn tác came_from
                stack.pop()
                for nb_done, old_parent in rollback:
                    path_set.discard(nb_done)
                    if old_parent is None:
                        came_from.pop(nb_done, None)
                    else:
                        came_from[nb_done] = old_parent
                continue

            if nb in path_set:
                continue

            # Pruning: skip nếu đã duyệt node này với budget >= hiện tại
            new_budget = remaining - 1
            if visited_at.get(nb, -1) >= new_budget:
                continue
            visited_at[nb] = new_budget

            total_visited.add(nb)
            old_parent = came_from.get(nb)
            came_from[nb] = node
            path_set.add(nb)
            rollback.append((nb, old_parent))

            if nb == e:
                found = True
                break

            if new_budget > 0:
                stack.append((nb, iter(get_neighbors(*nb)), new_budget, []))

            yield total_visited, path_set

        if found:
            p = reconstruct_path(came_from, e)
            state.path_cells = p
            state.stats.update(
                nodes=len(total_visited),
                path=len(p),
                cost=len(p) - 1,
                time=time.perf_counter() - t0,
                found=True,
            )
            state.finished = True
            return

        yield total_visited, set()

    state.stats.update(
        nodes=len(total_visited),
        found=False,
        time=time.perf_counter() - t0,
    )
    state.finished = True
