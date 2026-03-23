import time
from collections import deque
from core.grid import get_neighbors, path_cost
from core.state import state


def algo_bidirectional():
    s, e = state.start_cell, state.end_cell
    elapsed = 0.0
    t_step = time.perf_counter()

    if s == e:
        state.path_cells = [s]
        state.stats.update(nodes=1, path=1, cost=0,
                           time=time.perf_counter() - t_step, found=True)
        state.came_from = {s: None}
        state.finished = True
        return

    # Forward search from s
    fwd_queue    = deque([s])
    fwd_visited  = {s: None}   # node -> parent

    # Backward search from e
    bwd_queue    = deque([e])
    bwd_visited  = {e: None}   # node -> parent

    meeting = None
    peak_mem = 0

    while fwd_queue or bwd_queue:
        # --- Forward step ---
        if fwd_queue:
            curr = fwd_queue.popleft()
            for nb in get_neighbors(*curr):
                if nb not in fwd_visited:
                    fwd_visited[nb] = curr
                    fwd_queue.append(nb)
                    if nb in bwd_visited:
                        meeting = nb
                        break
            if meeting:
                peak_mem = max(peak_mem, len(fwd_visited) + len(bwd_visited) + len(fwd_queue) + len(bwd_queue))
                elapsed += time.perf_counter() - t_step
                yield (set(fwd_visited) | set(bwd_visited)).copy(), set()
                t_step = time.perf_counter()
                break

        # --- Backward step ---
        if bwd_queue:
            curr = bwd_queue.popleft()
            for nb in get_neighbors(*curr):
                if nb not in bwd_visited:
                    bwd_visited[nb] = curr
                    bwd_queue.append(nb)
                    if nb in fwd_visited:
                        meeting = nb
                        break
            if meeting:
                peak_mem = max(peak_mem, len(fwd_visited) + len(bwd_visited) + len(fwd_queue) + len(bwd_queue))
                elapsed += time.perf_counter() - t_step
                yield (set(fwd_visited) | set(bwd_visited)).copy(), set()
                t_step = time.perf_counter()
                break

        visited_all = set(fwd_visited) | set(bwd_visited)
        frontier    = set(fwd_queue)  | set(bwd_queue)
        peak_mem = max(peak_mem, len(fwd_visited) + len(bwd_visited) + len(fwd_queue) + len(bwd_queue))
        elapsed += time.perf_counter() - t_step
        yield visited_all.copy(), frontier.copy()
        t_step = time.perf_counter()

    if meeting is not None:
        # Build path: s -> meeting using fwd_visited
        fwd_path = []
        node = meeting
        while node is not None:
            fwd_path.append(node)
            node = fwd_visited[node]
        fwd_path.reverse()

        # Build path: meeting -> e using bwd_visited
        bwd_path = []
        node = bwd_visited[meeting]
        while node is not None:
            bwd_path.append(node)
            node = bwd_visited[node]

        p = fwd_path + bwd_path
        visited_all = set(fwd_visited) | set(bwd_visited)
        state.path_cells = p
        state.stats.update(nodes=len(visited_all), path=len(p),
                           cost=path_cost(p), time=elapsed + (time.perf_counter() - t_step), found=True,
                           iterations=1, peak_memory=peak_mem)
        state.came_from = fwd_visited
        state.finished = True
        return

    visited_all = set(fwd_visited) | set(bwd_visited)
    state.stats.update(nodes=len(visited_all), found=False,
                       time=elapsed + (time.perf_counter() - t_step),
                       iterations=1, peak_memory=peak_mem)
    state.came_from = fwd_visited
    state.finished = True
