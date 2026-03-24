"""Shared contract helpers for search algorithms."""

from core.state import state


def finalize_success(path, came_from, nodes, cost, elapsed, iterations=1, peak_memory=0):
    stats = state.new_stats()
    stats.update(
        nodes=nodes,
        path=len(path),
        cost=cost,
        time=elapsed,
        found=True,
        iterations=iterations,
        peak_memory=peak_memory,
    )
    state.path_cells = list(path)
    state.stats = stats
    state.came_from = dict(came_from)
    state.finished = True
    return stats


def finalize_failure(came_from, nodes, elapsed, iterations=1, peak_memory=0):
    stats = state.new_stats()
    stats.update(
        nodes=nodes,
        path=0,
        cost=0,
        time=elapsed,
        found=False,
        iterations=iterations,
        peak_memory=peak_memory,
    )
    state.path_cells = []
    state.stats = stats
    state.came_from = dict(came_from)
    state.finished = True
    return stats
