import time
from core.grid import get_neighbors, reconstruct_path, path_cost
from core.state import state


def algo_iddfs():
    s, e = state.start_cell, state.end_cell
    # elapsed: tổng thời gian CPU thuần túy của thuật toán (không tính thời gian yield chờ GUI)
    elapsed = 0.0
    t_step = time.perf_counter()
    total_visited = set()
    total_visited.add(s)

    if s == e:
        state.path_cells = [s]
        state.stats.update(nodes=1, path=1, cost=0,
                           time=time.perf_counter() - t_step, found=True)
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
                           time=time.perf_counter() - t_step)
        state.finished = True
        return

    iterations = 0
    peak_mem = 0

    for depth in range(state.rows * state.cols + 1):
        iterations += 1
        came_from = {s: None}
        path_set = {s}
        # Transposition table: track max budget at which each node was explored.
        # If we reach a node with budget <= previously explored, skip it.
        # This prevents exponential blowup in open/sparse mazes.
        visited_at = {}

        found = False
        # Frame: (node, nb_iter, remaining, should_clean)
        # should_clean=True → xóa node khỏi path_set/came_from khi frame bị pop
        stack = [(s, iter(get_neighbors(*s)), depth, False)]

        while stack:
            node, nb_iter, remaining, _ = stack[-1]
            nb = next(nb_iter, None)

            if nb is None:
                # Hết neighbor → backtrack: mỗi node tự dọn dẹp chính nó khi pop
                popped_node, _, _, should_clean = stack.pop()
                if should_clean:
                    path_set.discard(popped_node)
                    came_from.pop(popped_node, None)
                continue

            if nb in path_set:
                continue

            # Pruning: skip nếu đã duyệt node này với budget >= hiện tại
            new_budget = remaining - 1
            if visited_at.get(nb, -1) >= new_budget:
                continue
            visited_at[nb] = new_budget

            total_visited.add(nb)
            came_from[nb] = node
            path_set.add(nb)
            peak_mem = max(peak_mem, len(path_set))

            if nb == e:
                found = True
                break

            if new_budget > 0:
                stack.append((nb, iter(get_neighbors(*nb)), new_budget, True))

            elapsed += time.perf_counter() - t_step
            yield total_visited.copy(), path_set.copy()
            t_step = time.perf_counter()

            if new_budget <= 0:
                # Leaf node: không push stack → cleanup ngay sau yield
                path_set.discard(nb)
                came_from.pop(nb, None)

        if found:
            p = reconstruct_path(came_from, e)
            state.path_cells = p
            state.stats.update(
                nodes=len(total_visited),
                path=len(p),
                cost=path_cost(p),
                time=elapsed + (time.perf_counter() - t_step),
                found=True,
                iterations=iterations,
                peak_memory=peak_mem,
            )
            state.came_from = came_from
            state.finished = True
            return

        elapsed += time.perf_counter() - t_step
        yield total_visited.copy(), set()
        t_step = time.perf_counter()

    state.stats.update(
        nodes=len(total_visited),
        found=False,
        time=elapsed + (time.perf_counter() - t_step),
        iterations=iterations,
        peak_memory=peak_mem,
    )
    state.came_from = came_from
    state.finished = True
