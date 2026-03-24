import time
from collections import deque

from algorithms._contract import finalize_failure, finalize_success
from core.grid import get_neighbors, path_cost
from core.state import state


def _merge_came_from(fwd_visited, bwd_visited, meeting):
    merged = dict(fwd_visited)
    for node, parent in bwd_visited.items():
        if node == meeting:
            continue
        merged[node] = parent
    return merged


def algo_bidirectional():
    s, e = state.start_cell, state.end_cell
    elapsed = 0.0
    t_step = time.perf_counter()

    if s == e:
        finalize_success([s], {s: None}, 1, 0, 0.0, iterations=1, peak_memory=1)
        return

    fwd_queue = deque([s])
    fwd_visited = {s: None}
    bwd_queue = deque([e])
    bwd_visited = {e: None}
    meeting = None
    peak_mem = 1

    while fwd_queue or bwd_queue:
        if fwd_queue:
            curr = fwd_queue.popleft()
            for nb in get_neighbors(*curr):
                if nb not in fwd_visited:
                    fwd_visited[nb] = curr
                    fwd_queue.append(nb)
                    if nb in bwd_visited:
                        meeting = nb
                        break
            if meeting is not None:
                peak_mem = max(
                    peak_mem,
                    len(fwd_visited) + len(bwd_visited) + len(fwd_queue) + len(bwd_queue),
                )
                elapsed += time.perf_counter() - t_step
                yield (set(fwd_visited) | set(bwd_visited)).copy(), set()
                t_step = time.perf_counter()
                break

        if bwd_queue:
            curr = bwd_queue.popleft()
            for nb in get_neighbors(*curr):
                if nb not in bwd_visited:
                    bwd_visited[nb] = curr
                    bwd_queue.append(nb)
                    if nb in fwd_visited:
                        meeting = nb
                        break
            if meeting is not None:
                peak_mem = max(
                    peak_mem,
                    len(fwd_visited) + len(bwd_visited) + len(fwd_queue) + len(bwd_queue),
                )
                elapsed += time.perf_counter() - t_step
                yield (set(fwd_visited) | set(bwd_visited)).copy(), set()
                t_step = time.perf_counter()
                break

        visited_all = set(fwd_visited) | set(bwd_visited)
        frontier = set(fwd_queue) | set(bwd_queue)
        peak_mem = max(
            peak_mem,
            len(fwd_visited) + len(bwd_visited) + len(fwd_queue) + len(bwd_queue),
        )
        elapsed += time.perf_counter() - t_step
        yield visited_all.copy(), frontier.copy()
        t_step = time.perf_counter()

    visited_all = set(fwd_visited) | set(bwd_visited)
    if meeting is not None:
        fwd_path = []
        node = meeting
        while node is not None:
            fwd_path.append(node)
            node = fwd_visited[node]
        fwd_path.reverse()

        bwd_path = []
        node = bwd_visited[meeting]
        while node is not None:
            bwd_path.append(node)
            node = bwd_visited[node]

        path = fwd_path + bwd_path
        finalize_success(
            path,
            _merge_came_from(fwd_visited, bwd_visited, meeting),
            len(visited_all),
            path_cost(path),
            elapsed + (time.perf_counter() - t_step),
            iterations=1,
            peak_memory=peak_mem,
        )
        return

    finalize_failure(
        _merge_came_from(fwd_visited, bwd_visited, meeting),
        len(visited_all),
        elapsed + (time.perf_counter() - t_step),
        iterations=1,
        peak_memory=peak_mem,
    )
