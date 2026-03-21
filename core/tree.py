"""Search tree projection helpers for the frontend."""

from collections import deque

from core.state import state

_TREE_MAX = 400
_tree_cache_key = None
_tree_cache = None


def compute_tree(came_from, start, path_cells):
    if not came_from or start not in came_from:
        return [], [], (0, 0)
    path_set = set(path_cells)
    children = {}
    for node, parent in came_from.items():
        if parent is not None:
            children.setdefault(parent, []).append(node)
    relevant = set()
    for node in path_cells:
        relevant.add(node)
        for child in children.get(node, []):
            relevant.add(child)
    queue = deque([start])
    order, in_order = [], set()
    while queue and len(order) < _TREE_MAX:
        node = queue.popleft()
        if node in in_order or node not in relevant:
            continue
        in_order.add(node)
        order.append(node)
        for child in children.get(node, []):
            if child not in in_order and child in relevant:
                queue.append(child)
    if not order:
        return [], [], (0, 0)
    filt = {}
    for node in order:
        child_nodes = [child for child in children.get(node, []) if child in in_order]
        if child_nodes:
            filt[node] = child_nodes
    level = {start: 0}
    for node in order:
        for child in filt.get(node, []):
            if child not in level:
                level[child] = level[node] + 1
    width = {}
    for node in reversed(order):
        child_nodes = filt.get(node, [])
        width[node] = max(1, sum(width.get(child, 1) for child in child_nodes)) if child_nodes else 1
    root_w = width.get(start, 1)
    if root_w > 40:
        factor = 40 / root_w
        for node in order:
            width[node] = max(0.3, width[node] * factor)
    x_start = {start: 0.0}
    for node in order:
        cx = x_start.get(node, 0.0)
        for child in filt.get(node, []):
            if child not in x_start:
                x_start[child] = cx
                cx += width.get(child, 1)
    by_level = {}
    for node in order:
        lv = level[node]
        by_level.setdefault(lv, []).append(node)

    max_count = max(len(nodes) for nodes in by_level.values())
    tree_w = float(max(max_count - 1, 1))

    pos_x = {}
    for lv in sorted(by_level.keys()):
        nodes = sorted(by_level[lv], key=lambda node: x_start.get(node, 0))
        count = len(nodes)
        if count == 1:
            pos_x[nodes[0]] = tree_w / 2.0
        else:
            for i, node in enumerate(nodes):
                pos_x[node] = tree_w * i / (count - 1)
    positions, edges = [], []
    mx = my = 0.0
    for node in order:
        px, py = pos_x.get(node, 0), float(level.get(node, 0))
        positions.append((node, px, py, node in path_set))
        if px > mx:
            mx = px
        if py > my:
            my = py
    for node in order:
        for child in filt.get(node, []):
            edges.append((node, child, node in path_set and child in path_set))
    return positions, edges, (mx + 1.0, my + 1.0)


def get_tree_data(algo_name):
    global _tree_cache_key, _tree_cache
    if not state.came_from:
        return None
    key = (id(state.came_from), len(state.came_from), state.start_cell, algo_name)
    if key == _tree_cache_key and _tree_cache is not None:
        return _tree_cache
    _tree_cache_key = key
    positions, edges, bounds = compute_tree(state.came_from, state.start_cell, state.path_cells)
    if not positions:
        _tree_cache = None
        return None
    _tree_cache = {
        "positions": [
            {"node": [node[0], node[1]], "x": px, "y": py, "ip": in_path}
            for node, px, py, in_path in positions
        ],
        "edges": [
            {"from": [parent[0], parent[1]], "to": [child[0], child[1]], "ip": in_path}
            for parent, child, in_path in edges
        ],
        "bounds": [bounds[0], bounds[1]],
        "start": list(state.start_cell),
        "end": list(state.end_cell),
        "shown": len(positions),
        "total": len(state.came_from),
        "algo": algo_name,
    }
    return _tree_cache
