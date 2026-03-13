#!/usr/bin/env python3
"""
========================================================
 Maze Pathfinding Visualizer — AI Lab 1
 Search Algorithms: BFS, DFS, UCS, A*, IDDFS,
                    Bidirectional BFS, Beam Search, IDA*
========================================================
Controls:
  Left-drag   : Draw walls
  Right-drag  : Erase walls
  S key       : Activate "set start" mode, then click grid
  E key       : Activate "set end"   mode, then click grid
  SPACE       : Run / Stop current algorithm
  C key       : Clear search visualization
  R key       : Reset everything
========================================================
"""

import pygame
import sys
import time
import heapq
import random
from collections import deque

# IDDFS and IDA* recurse up to O(ROWS*COLS) deep — raise the limit
sys.setrecursionlimit(100_000)

pygame.init()

# ─────────────────────────────────────────────
# WINDOW & GRID SETTINGS
# ─────────────────────────────────────────────
W, H   = 1180, 730
ROWS   = 28
COLS   = 40
CELL   = 17          # pixels per cell
GX     = 8           # grid left offset
GY     = 54          # grid top  offset
PX     = GX + COLS * CELL + 16   # panel left edge
PW     = W - PX - 8              # panel width

# ─────────────────────────────────────────────
# COLOR PALETTE
# ─────────────────────────────────────────────
BG         = ( 18,  20,  32)
C_EMPTY    = ( 42,  46,  62)
C_WALL     = ( 12,  14,  22)
C_START    = ( 46, 213, 115)
C_END      = (213,  60,  60)
C_VISITED  = ( 38,  75, 155)
C_FRONTIER = ( 70, 130, 210)
C_PATH     = (252, 196,  25)
C_WHITE    = (225, 228, 240)
C_GRAY     = (130, 135, 155)
C_PANEL    = ( 25,  28,  42)
C_BTN      = ( 48,  62, 105)
C_BTN_H    = ( 68,  88, 145)
C_BTN_A    = ( 88, 118, 190)
C_BTN_OK   = ( 40, 130,  70)
C_BTN_SEL  = ( 35, 120,  70)
C_GREEN    = ( 46, 180,  95)
C_RED      = (190,  55,  55)
C_ORANGE   = (210, 130,  40)
C_YELLOW   = (230, 190,  30)

DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]

ALG_NAMES = ["BFS", "DFS", "UCS", "A*", "IDDFS", "Bidir.", "Beam", "IDA*"]
ALG_FULL  = [
    "Breadth-First Search",
    "Depth-First Search",
    "Uniform Cost Search",
    "A* (Manhattan heuristic)",
    "Iterative Deepening DFS",
    "Bidirectional BFS",
    "Beam Search  (width=8)",
    "Iterative Deepening A*",
]

screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Maze Pathfinding Visualizer  |  AI Lab 1")
clock  = pygame.time.Clock()

try:
    FS = pygame.font.SysFont("consolas", 12)
    FM = pygame.font.SysFont("consolas", 14, bold=True)
    FL = pygame.font.SysFont("consolas", 16, bold=True)
    FT = pygame.font.SysFont("consolas", 18, bold=True)
except Exception:
    FS = FM = FL = FT = pygame.font.Font(None, 15)


# ─────────────────────────────────────────────
# GLOBAL STATE
# ─────────────────────────────────────────────
walls       = set()
start_cell  = (4, 4)
end_cell    = (ROWS - 5, COLS - 5)

vis_cells   = set()
front_cells = set()
path_cells  = []

running     = False
finished    = False
cur_alg     = 0
set_mode    = None    # None | 'start' | 'end'
speed       = 20      # steps advanced per frame
alg_gen     = None
_counter    = [0]     # tie-breaking counter for heapq

stats = {"nodes": 0, "path": 0, "cost": 0, "time": 0.0, "found": None}


# ─────────────────────────────────────────────
# GRID HELPERS
# ─────────────────────────────────────────────
def in_bounds(r, c):
    return 0 <= r < ROWS and 0 <= c < COLS

def get_neighbors(r, c):
    return [
        (r + dr, c + dc)
        for dr, dc in DIRS
        if in_bounds(r + dr, c + dc) and (r + dr, c + dc) not in walls
    ]

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def reconstruct_path(came_from, node):
    path = []
    while node is not None:
        path.append(node)
        node = came_from.get(node)
    return list(reversed(path))

def next_id():
    _counter[0] += 1
    return _counter[0]


# ─────────────────────────────────────────────
# ALGORITHMS  (generator-based for step viz)
# Each generator yields (visited_set, frontier_set)
# When done → sets globals path_cells, stats, finished
# ─────────────────────────────────────────────

def algo_bfs():
    global path_cells, stats, finished
    s, e = start_cell, end_cell
    t0 = time.perf_counter()
    queue     = deque([s])
    came_from = {s: None}
    visited   = {s}

    while queue:
        curr = queue.popleft()
        if curr == e:
            p = reconstruct_path(came_from, e)
            path_cells = p
            stats.update(nodes=len(visited), path=len(p),
                         cost=len(p)-1, time=time.perf_counter()-t0, found=True)
            finished = True; return

        for nb in get_neighbors(*curr):
            if nb not in visited:
                visited.add(nb)
                came_from[nb] = curr
                queue.append(nb)

        yield visited.copy(), set(queue)

    stats.update(nodes=len(visited), found=False, time=time.perf_counter()-t0)
    finished = True


def algo_dfs():
    global path_cells, stats, finished
    s, e = start_cell, end_cell
    t0 = time.perf_counter()
    stack     = [s]
    came_from = {s: None}
    visited   = set()

    while stack:
        curr = stack.pop()
        if curr in visited:
            continue
        visited.add(curr)

        if curr == e:
            p = reconstruct_path(came_from, e)
            path_cells = p
            stats.update(nodes=len(visited), path=len(p),
                         cost=len(p)-1, time=time.perf_counter()-t0, found=True)
            finished = True; return

        for nb in get_neighbors(*curr):
            if nb not in visited:
                if nb not in came_from:
                    came_from[nb] = curr
                stack.append(nb)

        yield visited.copy(), set(stack)

    stats.update(nodes=len(visited), found=False, time=time.perf_counter()-t0)
    finished = True


def algo_ucs():
    global path_cells, stats, finished
    s, e = start_cell, end_cell
    t0 = time.perf_counter()
    pq        = [(0, next_id(), s)]
    came_from = {s: None}
    g_cost    = {s: 0}
    visited   = set()

    while pq:
        cost, _, curr = heapq.heappop(pq)
        if curr in visited:
            continue
        visited.add(curr)

        if curr == e:
            p = reconstruct_path(came_from, e)
            path_cells = p
            stats.update(nodes=len(visited), path=len(p),
                         cost=cost, time=time.perf_counter()-t0, found=True)
            finished = True; return

        for nb in get_neighbors(*curr):
            ng = g_cost[curr] + 1
            if nb not in g_cost or ng < g_cost[nb]:
                g_cost[nb]    = ng
                came_from[nb] = curr
                heapq.heappush(pq, (ng, next_id(), nb))

        yield visited.copy(), {n for _, _, n in pq}

    stats.update(nodes=len(visited), found=False, time=time.perf_counter()-t0)
    finished = True


def algo_astar():
    global path_cells, stats, finished
    s, e = start_cell, end_cell
    t0 = time.perf_counter()
    pq        = [(heuristic(s, e), 0, next_id(), s)]
    came_from = {s: None}
    g_cost    = {s: 0}
    visited   = set()

    while pq:
        f, gc, _, curr = heapq.heappop(pq)
        if curr in visited:
            continue
        visited.add(curr)

        if curr == e:
            p = reconstruct_path(came_from, e)
            path_cells = p
            stats.update(nodes=len(visited), path=len(p),
                         cost=gc, time=time.perf_counter()-t0, found=True)
            finished = True; return

        for nb in get_neighbors(*curr):
            ng = g_cost[curr] + 1
            if nb not in g_cost or ng < g_cost[nb]:
                g_cost[nb]    = ng
                came_from[nb] = curr
                heapq.heappush(pq, (ng + heuristic(nb, e), ng, next_id(), nb))

        yield visited.copy(), {n for _, _, _, n in pq}

    stats.update(nodes=len(visited), found=False, time=time.perf_counter()-t0)
    finished = True


def algo_iddfs():
    """Iterative Deepening DFS — fully iterative, no recursion."""
    global path_cells, stats, finished
    s, e = start_cell, end_cell
    t0 = time.perf_counter()
    all_visited = set()

    for depth_limit in range(1, ROWS * COLS + 1):
        # Explicit stack: (node, parent, depth)
        stack = [(s, None, 0)]
        came_from_iter = {s: None}
        iter_vis = set()
        found = False

        while stack:
            node, parent, d = stack.pop()
            if node in iter_vis:
                continue
            iter_vis.add(node)
            all_visited.add(node)
            came_from_iter[node] = parent

            if node == e:
                found = True
                break

            if d < depth_limit:
                for nb in get_neighbors(*node):
                    if nb not in iter_vis:
                        stack.append((nb, node, d + 1))

        if found:
            p = reconstruct_path(came_from_iter, e)
            path_cells = p
            stats.update(nodes=len(all_visited), path=len(p),
                         cost=len(p)-1, time=time.perf_counter()-t0, found=True)
            finished = True
            return

        yield all_visited.copy(), set()

    stats.update(nodes=len(all_visited), found=False, time=time.perf_counter()-t0)
    finished = True


def algo_bidirectional():
    """Bidirectional BFS."""
    global path_cells, stats, finished
    s, e = start_cell, end_cell
    t0 = time.perf_counter()
    fwd_q     = deque([s])
    bwd_q     = deque([e])
    fwd_came  = {s: None}
    bwd_came  = {e: None}
    fwd_vis   = {s}
    bwd_vis   = {e}

    def build(meet):
        p1 = reconstruct_path(fwd_came, meet)
        p2 = reconstruct_path(bwd_came, meet)
        return p1 + list(reversed(p2))[1:]

    def step_queue(q, came, vis, other_vis):
        if not q:
            return None
        curr = q.popleft()
        for nb in get_neighbors(*curr):
            if nb not in vis:
                vis.add(nb)
                came[nb] = curr
                q.append(nb)
                if nb in other_vis:
                    return nb
        return None

    while fwd_q or bwd_q:
        meet = step_queue(fwd_q, fwd_came, fwd_vis, bwd_vis)
        if meet:
            p = build(meet)
            path_cells = p
            stats.update(nodes=len(fwd_vis)+len(bwd_vis), path=len(p),
                         cost=len(p)-1, time=time.perf_counter()-t0, found=True)
            finished = True; return

        meet = step_queue(bwd_q, bwd_came, bwd_vis, fwd_vis)
        if meet:
            p = build(meet)
            path_cells = p
            stats.update(nodes=len(fwd_vis)+len(bwd_vis), path=len(p),
                         cost=len(p)-1, time=time.perf_counter()-t0, found=True)
            finished = True; return

        yield fwd_vis | bwd_vis, set(fwd_q) | set(bwd_q)

    stats.update(nodes=len(fwd_vis)+len(bwd_vis), found=False, time=time.perf_counter()-t0)
    finished = True


def algo_beam(beam_width=8):
    """Beam Search with configurable beam width."""
    global path_cells, stats, finished
    s, e = start_cell, end_cell
    t0 = time.perf_counter()
    beam      = [s]
    came_from = {s: None}
    visited   = {s}

    while beam:
        if e in beam:
            p = reconstruct_path(came_from, e)
            path_cells = p
            stats.update(nodes=len(visited), path=len(p),
                         cost=len(p)-1, time=time.perf_counter()-t0, found=True)
            finished = True; return

        candidates = []
        for curr in beam:
            for nb in get_neighbors(*curr):
                if nb not in visited:
                    visited.add(nb)
                    came_from[nb] = curr
                    candidates.append((heuristic(nb, e), next_id(), nb))

        if not candidates:
            break

        candidates.sort()
        beam = [n for _, _, n in candidates[:beam_width]]
        yield visited.copy(), set(beam)

    stats.update(nodes=len(visited), found=False, time=time.perf_counter()-t0)
    finished = True


def algo_idastar():
    """Iterative Deepening A* — fully iterative, no recursion."""
    global path_cells, stats, finished
    s, e = start_cell, end_cell
    t0 = time.perf_counter()
    all_visited = set()
    threshold = heuristic(s, e)

    while True:
        min_exceeded = float('inf')
        # Explicit stack: (node, parent, g_cost)
        stack = [(s, None, 0)]
        came_from_iter = {s: None}
        iter_vis = set()
        found = False

        while stack:
            node, parent, g = stack.pop()
            f = g + heuristic(node, e)
            if f > threshold:
                min_exceeded = min(min_exceeded, f)
                continue
            if node in iter_vis:
                continue
            iter_vis.add(node)
            all_visited.add(node)
            came_from_iter[node] = parent

            if node == e:
                found = True
                break

            for nb in get_neighbors(*node):
                if nb not in iter_vis:
                    stack.append((nb, node, g + 1))

        yield all_visited.copy(), set()

        if found:
            p = reconstruct_path(came_from_iter, e)
            path_cells = p
            stats.update(nodes=len(all_visited), path=len(p),
                         cost=len(p)-1, time=time.perf_counter()-t0, found=True)
            finished = True
            return

        if min_exceeded == float('inf'):
            break
        threshold = min_exceeded

    stats.update(nodes=len(all_visited), found=False, time=time.perf_counter()-t0)
    finished = True


ALGO_FUNCS = [
    algo_bfs, algo_dfs, algo_ucs, algo_astar,
    algo_iddfs, algo_bidirectional, algo_beam, algo_idastar,
]


# ─────────────────────────────────────────────
# MAZE GENERATION  (Recursive Division)
# ─────────────────────────────────────────────
def generate_maze():
    global walls
    walls = set()
    for r in range(ROWS):
        walls.add((r, 0)); walls.add((r, COLS - 1))
    for c in range(COLS):
        walls.add((0, c)); walls.add((ROWS - 1, c))

    def divide(r1, c1, r2, c2):
        w = c2 - c1
        h = r2 - r1
        if w < 2 or h < 2:
            return
        horizontal = h > w if h != w else random.random() < 0.5

        if horizontal:
            wr = random.randrange(r1 + 1, r2)
            pc = random.randrange(c1, c2 + 1)
            for c in range(c1, c2 + 1):
                if c != pc:
                    walls.add((wr, c))
            divide(r1, c1, wr - 1, c2)
            divide(wr + 1, c1, r2, c2)
        else:
            wc = random.randrange(c1 + 1, c2)
            pr = random.randrange(r1, r2 + 1)
            for r in range(r1, r2 + 1):
                if r != pr:
                    walls.add((r, wc))
            divide(r1, c1, r2, wc - 1)
            divide(r1, wc + 1, r2, c2)

    divide(1, 1, ROWS - 2, COLS - 2)

    # Ensure start/end cells are clear
    for dr in range(-1, 2):
        for dc in range(-1, 2):
            walls.discard((start_cell[0] + dr, start_cell[1] + dc))
            walls.discard((end_cell[0]   + dr, end_cell[1]   + dc))


# ─────────────────────────────────────────────
# STATE MANAGEMENT
# ─────────────────────────────────────────────
def clear_search():
    global vis_cells, front_cells, path_cells, stats, finished, alg_gen, running
    running = False
    # Explicitly close old generator BEFORE nullifying.
    # Without this Python throws GeneratorExit into mid-recursion IDDFS/IDA* -> crash.
    if alg_gen is not None:
        try:
            alg_gen.close()
        except Exception:
            pass
    alg_gen     = None
    vis_cells   = set()
    front_cells = set()
    path_cells  = []
    stats       = {"nodes": 0, "path": 0, "cost": 0, "time": 0.0, "found": None}
    finished    = False

def start_algorithm():
    global alg_gen, running, finished, vis_cells, front_cells, path_cells, stats
    clear_search()
    _counter[0] = 0
    running  = True
    alg_gen  = ALGO_FUNCS[cur_alg]()


# ─────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────
def txt(surface, text, x, y, font=FS, color=C_WHITE, cx=False):
    s = font.render(text, True, color)
    if cx:
        x -= s.get_width() // 2
    surface.blit(s, (x, y))

def draw_btn(surface, rect, label, active=False, hover=False, base=C_BTN):
    color = C_BTN_A if active else (C_BTN_H if hover else base)
    pygame.draw.rect(surface, color, rect, border_radius=5)
    pygame.draw.rect(surface, (65, 78, 118), rect, 1, border_radius=5)
    txt(surface, label, rect.centerx, rect.centery - 7, FM, C_WHITE, cx=True)

def mk_btn(y, h=27):
    return pygame.Rect(PX, y, PW, h)


# ─────────────────────────────────────────────
# BUTTON LAYOUT
# ─────────────────────────────────────────────
BW2 = (PW - 4) // 2
alg_rects = [
    pygame.Rect(PX + (i % 2) * (BW2 + 4), 58 + (i // 2) * 30, BW2, 24)
    for i in range(len(ALG_NAMES))
]

btn_run    = mk_btn(200)
btn_clear  = mk_btn(233)
btn_maze   = mk_btn(266)
btn_reset  = mk_btn(299)

spd_minus  = pygame.Rect(PX,          354, 36, 24)
spd_plus   = pygame.Rect(PX + PW - 36, 354, 36, 24)

btn_setS   = mk_btn(430, 26)
btn_setE   = mk_btn(462, 26)


# ─────────────────────────────────────────────
# DRAW
# ─────────────────────────────────────────────
def draw_all():
    screen.fill(BG)
    mx, my = pygame.mouse.get_pos()

    # ── Title bar ─────────────────────────────
    txt(screen, "Maze Pathfinding Visualizer", GX, 10, FL, C_WHITE)
    hint = "MODE: SET START — click grid" if set_mode == 'start' else \
           "MODE: SET END — click grid"   if set_mode == 'end'   else \
           "LMB: wall  RMB: erase  S/E: set points  SPACE: run/stop  R: reset"
    hint_col = C_GREEN if set_mode == 'start' else C_RED if set_mode == 'end' else C_GRAY
    txt(screen, hint, GX, 34, FS, hint_col)

    # ── Grid cells ────────────────────────────
    for r in range(ROWS):
        for c in range(COLS):
            px2 = GX + c * CELL
            py2 = GY + r * CELL
            cell = (r, c)
            if   cell in walls:       color = C_WALL
            elif cell == start_cell:  color = C_START
            elif cell == end_cell:    color = C_END
            elif cell in path_cells:  color = C_PATH
            elif cell in vis_cells:   color = C_VISITED
            elif cell in front_cells: color = C_FRONTIER
            else:                     color = C_EMPTY
            pygame.draw.rect(screen, color, (px2 + 1, py2 + 1, CELL - 1, CELL - 1))

    # Grid border
    pygame.draw.rect(screen, (55, 62, 85),
                     (GX, GY, COLS * CELL, ROWS * CELL), 1)

    # ── Panel background ──────────────────────
    pygame.draw.rect(screen, C_PANEL, (PX - 6, 0, W - PX + 6, H))
    pygame.draw.line(screen, (55, 62, 85), (PX - 6, 0), (PX - 6, H))

    # ── Algorithm buttons ─────────────────────
    txt(screen, "ALGORITHMS", PX, 40, FM, C_GRAY)
    for i, (rect, name) in enumerate(zip(alg_rects, ALG_NAMES)):
        sel = (i == cur_alg)
        draw_btn(screen, rect, name, active=sel,
                 hover=rect.collidepoint(mx, my),
                 base=C_BTN_SEL if sel else C_BTN)

    # Current algorithm name
    txt(screen, ALG_FULL[cur_alg], PX, 182, FS, C_YELLOW)

    # ── Control buttons ───────────────────────
    txt(screen, "CONTROLS", PX, 185 + 8, FM, C_GRAY)
    lbl_run = "■  STOP" if running else "▶  RUN"
    draw_btn(screen, btn_run,   lbl_run,       running,  btn_run.collidepoint(mx, my))
    draw_btn(screen, btn_clear, "CLEAR PATH",  False,    btn_clear.collidepoint(mx, my))
    draw_btn(screen, btn_maze,  "GEN MAZE",    False,    btn_maze.collidepoint(mx, my))
    draw_btn(screen, btn_reset, "RESET ALL",   False,    btn_reset.collidepoint(mx, my))

    # ── Speed slider ──────────────────────────
    txt(screen, f"SPEED: {speed:>3} steps/frame", PX, 337, FM, C_GRAY)
    draw_btn(screen, spd_minus, " -", False, spd_minus.collidepoint(mx, my))
    draw_btn(screen, spd_plus,  "+ ", False, spd_plus.collidepoint(mx, my))
    # Speed bar
    bar_x = PX + 40
    bar_w = PW - 80
    bar_h = 6
    bar_y = 362
    pygame.draw.rect(screen, C_BTN, (bar_x, bar_y, bar_w, bar_h), border_radius=3)
    fill_w = int(bar_w * speed / 100)
    pygame.draw.rect(screen, C_BTN_A, (bar_x, bar_y, fill_w, bar_h), border_radius=3)

    # ── Legend ───────────────────────────────
    txt(screen, "LEGEND", PX, 384, FM, C_GRAY)
    legend = [
        (C_START, "Start"),    (C_END,      "End"),
        (C_WALL,  "Wall"),     (C_VISITED,  "Visited"),
        (C_FRONTIER, "Queue"), (C_PATH,     "Path"),
    ]
    for i, (c, label) in enumerate(legend):
        lx = PX + (i % 2) * (PW // 2)
        ly = 402 + (i // 2) * 18
        pygame.draw.rect(screen, c, (lx, ly + 2, 12, 12), border_radius=2)
        txt(screen, label, lx + 16, ly, FS, C_GRAY)

    # ── Set start/end ─────────────────────────
    txt(screen, "SET POINTS", PX, 414, FM, C_GRAY)
    draw_btn(screen, btn_setS, "Set Start  [S]",
             set_mode == 'start', btn_setS.collidepoint(mx, my),
             C_GREEN if set_mode == 'start' else C_BTN)
    draw_btn(screen, btn_setE, "Set End    [E]",
             set_mode == 'end',   btn_setE.collidepoint(mx, my),
             C_RED   if set_mode == 'end'   else C_BTN)

    # ── Statistics ───────────────────────────
    txt(screen, "STATISTICS", PX, 502, FM, C_GRAY)
    sep_y = 517
    pygame.draw.line(screen, (55, 62, 85), (PX, sep_y), (PX + PW, sep_y))

    found = stats["found"]
    if   found is True:   status, sc = "PATH FOUND",     C_GREEN
    elif found is False:  status, sc = "NO PATH / ERROR", C_RED
    else:                 status, sc = "READY",           C_GRAY

    txt(screen, status, PX + PW // 2, 522, FM, sc, cx=True)

    rows_stat = [
        ("Algorithm", ALG_NAMES[cur_alg]),
        ("Nodes visited", str(stats["nodes"])),
        ("Path length",   str(stats["path"])),
        ("Path cost",     str(stats["cost"])),
        ("Time (s)",      f"{stats['time']:.5f}"),
    ]
    for i, (k, v) in enumerate(rows_stat):
        y_row = 542 + i * 20
        txt(screen, k, PX,      y_row, FS, C_GRAY)
        txt(screen, v, PX + PW, y_row, FS, C_WHITE, cx=False)
        # right-align value
        vsurf = FS.render(v, True, C_WHITE)
        screen.blit(vsurf, (PX + PW - vsurf.get_width(), y_row))

    # ── Progress indicator ───────────────────
    if running:
        dots = "." * (int(time.time() * 3) % 4)
        txt(screen, f"Running{dots}", PX, 650, FS, C_ORANGE)
    elif finished and stats["found"]:
        txt(screen, "✓ Done", PX, 650, FM, C_GREEN)

    pygame.display.flip()


# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────
def grid_cell(mx, my):
    c = (mx - GX) // CELL
    r = (my - GY) // CELL
    if in_bounds(r, c):
        return r, c
    return None

dragging = None   # True = draw walls, False = erase walls

while True:
    mx, my = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()

        # ── Keyboard ──────────────────────────
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_s:
                set_mode = 'start'
            elif event.key == pygame.K_e:
                set_mode = 'end'
            elif event.key == pygame.K_SPACE:
                if running:
                    running = False
                else:
                    start_algorithm()
            elif event.key == pygame.K_c:
                clear_search()
            elif event.key == pygame.K_r:
                clear_search(); walls = set()
            elif event.key == pygame.K_ESCAPE:
                set_mode = None

        # ── Mouse button down ─────────────────
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # Panel buttons
                if btn_run.collidepoint(mx, my):
                    if running: running = False
                    else:       start_algorithm()
                elif btn_clear.collidepoint(mx, my):
                    clear_search()
                elif btn_maze.collidepoint(mx, my):
                    clear_search(); generate_maze()
                elif btn_reset.collidepoint(mx, my):
                    clear_search(); walls = set()
                elif spd_minus.collidepoint(mx, my):
                    speed = max(1, speed - 5)
                elif spd_plus.collidepoint(mx, my):
                    speed = min(100, speed + 10)
                elif btn_setS.collidepoint(mx, my):
                    set_mode = 'start'
                elif btn_setE.collidepoint(mx, my):
                    set_mode = 'end'
                else:
                    # Algorithm buttons
                    for i, rect in enumerate(alg_rects):
                        if rect.collidepoint(mx, my):
                            cur_alg = i
                            clear_search()
                            break
                    else:
                        # Grid interaction
                        cell = grid_cell(mx, my)
                        if cell:
                            r, c = cell
                            if set_mode == 'start':
                                start_cell = (r, c)
                                walls.discard((r, c))
                                set_mode = None
                                clear_search()
                            elif set_mode == 'end':
                                end_cell = (r, c)
                                walls.discard((r, c))
                                set_mode = None
                                clear_search()
                            elif (r, c) not in (start_cell, end_cell):
                                walls.add((r, c))
                                dragging = True
                                clear_search()

            elif event.button == 3:
                cell = grid_cell(mx, my)
                if cell:
                    walls.discard(cell)
                    dragging = False

        elif event.type == pygame.MOUSEBUTTONUP:
            dragging = None

        # ── Mouse drag ────────────────────────
        elif event.type == pygame.MOUSEMOTION:
            if dragging is not None:
                cell = grid_cell(mx, my)
                if cell and cell not in (start_cell, end_cell):
                    if dragging:
                        walls.add(cell)
                    else:
                        walls.discard(cell)

    # ── Advance algorithm ─────────────────────
    if running and alg_gen and not finished:
        for _ in range(speed):
            try:
                v, f        = next(alg_gen)
                vis_cells   = v
                front_cells = f
            except StopIteration:
                running = False
                break
            except RecursionError:
                # IDDFS / IDA* can hit Python stack limit on large open grids.
                # sys.setrecursionlimit(100_000) should prevent this, but
                # catch it anyway so the GUI never crashes.
                running = False
                finished = True
                stats["found"] = False
                stats["nodes"] = len(vis_cells)
                break
            except Exception as exc:
                # Any other unexpected error — stop gracefully, never crash
                running = False
                finished = True
                stats["found"] = False
                print(f"[Algorithm error] {type(exc).__name__}: {exc}")
                break

    draw_all()
    clock.tick(60)