"""
gui.py — Maze Pathfinding Visualizer  (v4 — Race + Tree)
"""

import pygame
import math
from collections import deque
from config import W, H, PW, state
from grid import generate_maze
from algorithms import ALGO_FUNCS, ALG_NAMES, ALG_FULL

# ─────────────────────────────────────────────
# INIT
# ─────────────────────────────────────────────
pygame.init()

_ww, _wh = W, H
screen = pygame.display.set_mode((_ww, _wh), pygame.RESIZABLE)
pygame.display.set_caption("Maze Pathfinding Visualizer")
clock = pygame.time.Clock()

# ─────────────────────────────────────────────
# FONTS
# ─────────────────────────────────────────────
_FNAMES = ("Segoe UI Variable", "Segoe UI", "SF Pro Display",
           "Helvetica Neue", "Arial")

def _mf(sz, bold=False):
    for n in _FNAMES:
        try:
            f = pygame.font.SysFont(n, sz, bold=bold)
            if f and f.get_height() > 0:
                return f
        except Exception:
            pass
    return pygame.font.SysFont(None, sz, bold=bold)

FT  = _mf(32, True)
FH  = _mf(16, True)
FB  = _mf(22, True)
FN  = _mf(20)
FS  = _mf(18)
FX  = _mf(17)
FXS = _mf(16)
FTN = _mf(15, True)     # tree node coordinate font
FM  = _mf(18)
for _mono in ("Consolas", "Courier New"):
    try:
        _fm = pygame.font.SysFont(_mono, 18)
        if _fm and _fm.get_height() > 0:
            FM = _fm
            break
    except Exception:
        pass

# ─────────────────────────────────────────────
# COLORS
# ─────────────────────────────────────────────
BG      = (242, 242, 247)
WHITE   = (255, 255, 255)
BLACK   = (0, 0, 0)
BORDER  = (229, 229, 234)
ACCENT  = (0, 122, 255)
GREEN   = (52, 199, 89)
RED     = (255, 59, 48)
ORANGE  = (255, 149, 0)
GRAY1   = (142, 142, 147)
GRAY2   = (174, 174, 178)
GRAY3   = (199, 199, 204)
GRAY4   = (229, 229, 234)
WALL_C  = (28, 28, 30)
START_C = GREEN
END_C   = RED
VIS_C   = ACCENT
FRONT_C = (88, 86, 214)
PATH_C  = ORANGE
HOVER_C = (232, 235, 245)
BTN_SH  = (200, 200, 210)
PRESS_C = (218, 222, 235)

# Tree colors
TREE_BG         = (248, 249, 252)
TREE_PATH_EDGE  = (255, 149, 0)       # orange — solution path edges
TREE_GLOW_EDGE  = (255, 200, 100)     # lighter orange glow beneath path edge
TREE_FAIL_EDGE  = (210, 222, 238)     # pale blue-gray — dead-end edges
TREE_PATH_NODE  = (255, 149, 0)       # orange — path nodes
TREE_PATH_NODE2 = (255, 185, 70)      # lighter orange — path node ring
TREE_FAIL_NODE  = (175, 205, 240)     # light blue — explored dead-end nodes
TREE_START_NODE = (52, 199, 89)
TREE_END_NODE   = (255, 59, 48)
TREE_LEVEL_LINE = (238, 241, 248)     # very subtle depth guide lines

_BAR_PALETTE = [
    (0, 122, 255), (52, 199, 89), (255, 149, 0), (255, 59, 48),
    (88, 86, 214), (175, 82, 222), (0, 199, 190), (255, 204, 0),
]

# ─────────────────────────────────────────────
# MODULE STATE
# ─────────────────────────────────────────────
dd_open   = False
_last_fin = False
_tab      = 0        # 0=Visualize  1=Race
_pressed  = None
_edit     = None
_etext    = ""

MAX_SPEED = 200
MIN_R, MAX_R = 5, 50
MIN_C, MAX_C = 5, 80

# ── Visualize split-tree state ─────────────────
_viz_show_tree   = False
_viz_tree_zoom   = 1.0
_viz_tree_ox     = 0.0
_viz_tree_oy     = 0.0
_viz_tree_drag   = None     # (start_mx, start_my, start_ox, start_oy)
_viz_tree_fit    = True     # auto-fit next draw
_viz_tree_ck     = None     # cache key
_viz_tree_pos    = []
_viz_tree_edges  = []
_viz_tree_bounds = (0, 0)
_last_alg_name   = ""

# ── Race state ──────────────────────────────────
_race_order      = []       # list of alg idx in selection order
_race_scales     = {}       # {idx: float 0-1} panel fade-in animation
_race_runners    = {}       # {idx: runner_dict}
_race_running    = False
_race_done       = False
_race_show_trees = False
_race_results    = []
_race_scroll     = 0
_race_content_h  = 0        # total scrollable height
_race_drag       = None     # active tree drag: (runner_idx, smx, smy, sox, soy)
_race_maze_drag  = None     # active maze pan:  (runner_idx, smx, smy, sox, soy)

# Maze pan (used in Show Tree mode)
_maze_drag       = None   # (start_mx, start_my, start_gx, start_gy)

# Wall / slider drag helpers
_dragging_wall   = None
_dragging_slider = False

# ─────────────────────────────────────────────
# GRID GEOMETRY
# ─────────────────────────────────────────────
g_cell = g_x = g_y = 0

# ── Ribbon dimensions ─────────────────────────────────────────────────────────
_RIB_TAB_H  = 36    # tab selector row
_RIB_BODY_H = 104   # ribbon content row
_RIB_H      = _RIB_TAB_H + _RIB_BODY_H   # = 140
_TAB_H      = _RIB_H   # backward-compat alias

def _ga():
    """Full content area (below ribbon)."""
    y = _RIB_H + 4
    return 0, y, _ww, _wh - y - 4

def _ga_maze():
    """Maze render area (may be left half in split view)."""
    ax, ay, aw, ah = _ga()
    if _tab == 0 and _viz_show_tree:
        hw = int(aw * 0.45)
        return ax, ay, hw, ah
    return ax, ay, aw, ah

def _ga_viz_tree():
    """Right panel in Visualize split view."""
    ax, ay, aw, ah = _ga()
    hw = int(aw * 0.45)
    return ax + hw + 10, ay, aw - hw - 10, ah

def recalc_grid():
    global g_cell, g_x, g_y
    ax, ay, aw, ah = _ga_maze()
    if state.cols <= 0 or state.rows <= 0:
        return
    g_cell = min(aw // state.cols, ah // state.rows)
    g_cell = max(g_cell, 4)
    gw = state.cols * g_cell
    gh = state.rows * g_cell
    g_x = ax + (aw - gw) // 2
    g_y = ay + (ah - gh) // 2

recalc_grid()

# ─────────────────────────────────────────────
# PANEL LAYOUT
# ─────────────────────────────────────────────
_PAD = 16
_CW  = PW - 2 * _PAD

def _build():
    """Compute ribbon button rects for the Visualize tab."""
    L = {}
    ry   = _RIB_TAB_H + 10
    rbot = _RIB_H - 24
    ch   = rbot - ry

    x = 10

    # ── Group 0: Algorithm ───────────────────────────────────────────────────
    L["dd"]    = pygame.Rect(x, ry, 200, 34)
    L["fn_cy"] = ry + 44
    x += 208;  L["_g0r"] = x;  x += 14

    # ── Group 1: Run ─────────────────────────────────────────────────────────
    L["btn_run"] = pygame.Rect(x, ry, 72, ch)
    x += 80;   L["_g1r"] = x;  x += 14

    # ── Group 2: Edit (3 stacked buttons) ────────────────────────────────────
    bwed = 128;  bhed = 20;  gap_ed = 4
    L["btn_clr"] = pygame.Rect(x, ry + 1,                    bwed, bhed)
    L["btn_maz"] = pygame.Rect(x, ry + 1 + bhed + gap_ed,    bwed, bhed)
    L["btn_rst"] = pygame.Rect(x, ry + 1 + 2*(bhed+gap_ed),  bwed, bhed)
    x += bwed + 8;  L["_g2r"] = x;  x += 14

    # ── Group 3: Speed ───────────────────────────────────────────────────────
    mn = 30;  slw = 156
    L["_spd_x"]     = x
    L["_spd_lbl_y"] = ry
    L["btn_sm"] = pygame.Rect(x,              ry + 24, mn,  mn)
    L["slider"]  = pygame.Rect(x + mn + 4,    ry + 24, slw, mn)
    L["btn_sp"]  = pygame.Rect(x+mn+4+slw+4,  ry + 24, mn,  mn)
    x += mn+4+slw+4+mn+8;  L["_g3r"] = x;  x += 14

    # ── Group 4: Grid — "Rows"/"Cols" label + [−][val][+] ───────────────────
    lbl_w = 44;  bz = 28;  iw = 44
    gw = lbl_w + bz + 3 + iw + 3 + bz
    L["_grid_x"] = x
    L["btn_rm"] = pygame.Rect(x + lbl_w,           ry + 4,  bz, bz)
    L["inp_r"]  = pygame.Rect(x + lbl_w + bz + 3,  ry + 4,  iw, bz)
    L["btn_rp"] = pygame.Rect(x+lbl_w+bz+3+iw+3,   ry + 4,  bz, bz)
    L["btn_cm"] = pygame.Rect(x + lbl_w,           ry + 40, bz, bz)
    L["inp_c"]  = pygame.Rect(x + lbl_w + bz + 3,  ry + 40, iw, bz)
    L["btn_cp"] = pygame.Rect(x+lbl_w+bz+3+iw+3,   ry + 40, bz, bz)
    x += gw + 8;  L["_g4r"] = x;  x += 14

    # ── Group 5: Points ──────────────────────────────────────────────────────
    bwp = 120
    L["btn_ss"] = pygame.Rect(x, ry + 4,      bwp, 28)
    L["btn_se"] = pygame.Rect(x, ry + 4 + 36, bwp, 28)
    x += bwp + 8;  L["_g5r"] = x;  x += 14

    # ── Group 6: Stats (text only — positions stored for drawing) ────────────
    L["_stats_x"] = x
    L["_stats_y"] = ry

    return L

_L = _build()

# ─────────────────────────────────────────────
# DRAWING PRIMITIVES
# ─────────────────────────────────────────────
def _tc(surf, text, font, color, cx, cy):
    s = font.render(str(text), True, color)
    surf.blit(s, s.get_rect(center=(cx, cy)))

def _tl(surf, text, font, color, x, cy):
    s = font.render(str(text), True, color)
    surf.blit(s, (x, cy - s.get_height() // 2))

def _tr(surf, text, font, color, rx, cy):
    s = font.render(str(text), True, color)
    surf.blit(s, (rx - s.get_width(), cy - s.get_height() // 2))

def _sec(surf, text, x, y):
    surf.blit(FH.render(text.upper(), True, GRAY1), (x, y))

# Cached soft card shadow
_sh_cache = {}

def _card(surf, rect):
    key = (rect.w, rect.h)
    if key not in _sh_cache:
        pad = 10
        s = pygame.Surface((rect.w + pad*2, rect.h + pad*2), pygame.SRCALPHA)
        for i in range(5):
            spread = 5 - i
            off_y  = int(1 + i * 0.6)
            alpha  = 4 + i * 3
            r = pygame.Rect(pad - spread, pad + off_y - spread,
                            rect.w + spread*2, rect.h + spread*2)
            pygame.draw.rect(s, (0, 0, 0, alpha), r, border_radius=12 + spread)
        _sh_cache[key] = s
    surf.blit(_sh_cache[key], (rect.x - 10, rect.y - 10))
    pygame.draw.rect(surf, WHITE, rect, border_radius=12)

def _is_hov(rect):
    return rect.collidepoint(pygame.mouse.get_pos())

def _is_p(rect):
    return _pressed is not None and _pressed is rect and rect.collidepoint(pygame.mouse.get_pos())

def _btn(surf, rect, label, font=FB, bg=WHITE, fg=BLACK,
         shadow=True, r=10, hov=False, pressed=False, selected=False):
    if selected:
        bg, fg = ACCENT, WHITE
    if pressed and hov:
        pbg = PRESS_C if bg == WHITE else tuple(max(0, c - 30) for c in bg)
        pygame.draw.rect(surf, pbg, rect.move(0, 1), border_radius=r)
        _tc(surf, label, font, fg, rect.centerx, rect.centery + 1)
        return
    if shadow:
        sh_off = 3 if hov and not selected else 2
        pygame.draw.rect(surf, BTN_SH, rect.move(0, sh_off), border_radius=r)
    abg = bg
    if hov and not selected:
        abg = HOVER_C if bg == WHITE else tuple(min(255, c + 22) for c in bg)
    pygame.draw.rect(surf, abg, rect, border_radius=r)
    if bg == WHITE and not selected:
        brd = (200, 200, 210) if hov else BORDER
        pygame.draw.rect(surf, brd, rect, 1, border_radius=r)
    _tc(surf, label, font, fg, rect.centerx, rect.centery)

def _gpos(mx, my):
    if g_cell <= 0 or _tab != 0 or my < _RIB_H:
        return None
    c = (mx - g_x) // g_cell
    r = (my - g_y) // g_cell
    return (r, c) if 0 <= r < state.rows and 0 <= c < state.cols else None

def _ccolor(r, c, ps, vis=None, front=None):
    pos = (r, c)
    if pos == state.start_cell: return START_C
    if pos == state.end_cell:   return END_C
    if pos in state.walls:      return WALL_C
    if pos in ps:               return PATH_C
    f = front if front is not None else state.front_cells
    v = vis   if vis   is not None else state.vis_cells
    if pos in f: return FRONT_C
    if pos in v: return VIS_C
    return WHITE

# ─────────────────────────────────────────────
# GRID SIZE HELPERS
# ─────────────────────────────────────────────
def _change_grid(dr, dc):
    nr = max(MIN_R, min(MAX_R, state.rows + dr))
    nc = max(MIN_C, min(MAX_C, state.cols + dc))
    if nr == state.rows and nc == state.cols:
        return
    state.clear_search()
    state.walls.clear()
    state.rows, state.cols = nr, nc
    sr, sc = state.start_cell
    state.start_cell = (min(sr, nr - 1), min(sc, nc - 1))
    er, ec = state.end_cell
    state.end_cell = (min(er, nr - 1), min(ec, nc - 1))
    if state.start_cell == state.end_cell:
        state.end_cell = (nr - 1, nc - 1)
    recalc_grid()

def _apply_edit():
    global _edit, _etext
    if _edit == "rows":
        v = int(_etext) if _etext.isdigit() and len(_etext) > 0 else state.rows
        v = max(MIN_R, min(MAX_R, v))
        if v != state.rows:
            _change_grid(v - state.rows, 0)
    elif _edit == "cols":
        v = int(_etext) if _etext.isdigit() and len(_etext) > 0 else state.cols
        v = max(MIN_C, min(MAX_C, v))
        if v != state.cols:
            _change_grid(0, v - state.cols)
    _edit = None
    _etext = ""

# ─────────────────────────────────────────────
# TREE LAYOUT ENGINE
# ─────────────────────────────────────────────
_TREE_MAX_NODES = 400

def _compute_tree_layout(came_from, start, path_cells):
    """Returns (positions, edges, bounds).
    positions: [(node, x_unit, y_unit, is_path)]
    edges:     [(parent, child, is_path_edge)]
    bounds:    (max_x_unit+1, max_y_unit+1)
    """
    if not came_from or start not in came_from:
        return [], [], (0, 0)

    path_set = set(path_cells)

    # Build children dict
    children = {}
    for node, parent in came_from.items():
        if parent is not None:
            children.setdefault(parent, []).append(node)

    # Only show path nodes + direct children of path nodes
    relevant = set()
    for node in path_cells:
        relevant.add(node)
        for ch in children.get(node, []):
            relevant.add(ch)

    # BFS order, only relevant nodes
    queue    = deque([start])
    order    = []
    in_order = set()
    while queue and len(order) < _TREE_MAX_NODES:
        node = queue.popleft()
        if node in in_order or node not in relevant:
            continue
        in_order.add(node)
        order.append(node)
        for ch in children.get(node, []):
            if ch not in in_order and ch in relevant:
                queue.append(ch)

    if not order:
        return [], [], (0, 0)

    # Filter children
    filt = {}
    for n in order:
        ch = [c for c in children.get(n, []) if c in in_order]
        if ch:
            filt[n] = ch

    # Depth levels
    level = {start: 0}
    for n in order:
        for c in filt.get(n, []):
            if c not in level:
                level[c] = level[n] + 1

    # Subtree widths (bottom-up) with compression
    width = {}
    for n in reversed(order):
        chs = filt.get(n, [])
        width[n] = max(1, sum(width.get(c, 1) for c in chs)) if chs else 1
    # Compress tree width to prevent root from extending too far
    root_w = width.get(start, 1)
    _MAX_W = 40
    if root_w > _MAX_W:
        _factor = _MAX_W / root_w
        for n in order:
            width[n] = max(0.3, width[n] * _factor)

    # X-start allocation (top-down)
    x_start = {start: 0.0}
    for n in order:
        cx = x_start.get(n, 0.0)
        for c in filt.get(n, []):
            if c not in x_start:
                x_start[c] = cx
                cx += width.get(c, 1)

    # Even spacing per level: each row of nodes is evenly distributed
    by_level = {}
    for n in order:
        lv = level[n]
        if lv not in by_level:
            by_level[lv] = []
        by_level[lv].append(n)

    max_count = max(len(v) for v in by_level.values())
    tree_w = float(max(max_count - 1, 1))

    pos_x = {}
    for lv in sorted(by_level.keys()):
        nodes = sorted(by_level[lv], key=lambda n: x_start.get(n, 0))
        count = len(nodes)
        if count == 1:
            pos_x[nodes[0]] = tree_w / 2.0
        else:
            for i, n in enumerate(nodes):
                pos_x[n] = tree_w * i / (count - 1)

    positions = []
    edges = []
    mx = 0.0; my = 0.0

    for n in order:
        px = pos_x.get(n, 0)
        py = float(level.get(n, 0))
        ip = n in path_set
        positions.append((n, px, py, ip))
        if px > mx: mx = px
        if py > my: my = py

    for n in order:
        for c in filt.get(n, []):
            ip_edge = (n in path_set and c in path_set)
            edges.append((n, c, ip_edge))

    return positions, edges, (mx + 1.0, my + 1.0)


def _auto_fit(positions, bounds, area, node_gap=None, level_gap=None, padding=28):
    """Return (zoom, ox, oy) to fit tree in area."""
    if node_gap is None: node_gap = NODE_GAP
    if level_gap is None: level_gap = LEVEL_GAP
    tw, th = bounds
    if tw <= 0 or th <= 0:
        return 1.0, area.x + area.w // 2, area.y + padding
    tree_pw = tw * node_gap
    tree_ph = th * level_gap
    avail_w = area.w - padding * 2
    avail_h = area.h - padding * 2
    zoom = min(avail_w / max(tree_pw, 1),
               avail_h / max(tree_ph, 1),
               2.5)
    zoom = max(zoom, 0.08)
    ox = area.x + (area.w - tree_pw * zoom) / 2.0
    oy = float(area.y + padding)
    return zoom, ox, oy


NODE_GAP  = 38    # horizontal spacing between node centres
LEVEL_GAP = 80    # vertical spacing between tree levels


def _arrow_edge(surf, color, p1, p2, width, rx_c, ry_c, arrow_sz=0):
    """Line from p1 toward p2 stopping at the oval border (rx_c, ry_c) at p2."""
    dx = p2[0] - p1[0]; dy = p2[1] - p1[1]
    dist = math.sqrt(dx * dx + dy * dy)
    if dist < 1:
        return
    ndx = dx / dist; ndy = dy / dist
    # Tip: back off by the child oval's radius in the direction of travel
    tip = (int(p2[0] - rx_c * ndx * 1.15), int(p2[1] - ry_c * ndy * 1.15))
    pygame.draw.line(surf, color, p1, tip, width)
    if arrow_sz > 2 and dist > rx_c + 6:
        px_ = -ndy; py_ = ndx          # perpendicular
        ax = int(tip[0] - arrow_sz * ndx + arrow_sz * 0.42 * px_)
        ay = int(tip[1] - arrow_sz * ndy + arrow_sz * 0.42 * py_)
        bx = int(tip[0] - arrow_sz * ndx - arrow_sz * 0.42 * px_)
        by = int(tip[1] - arrow_sz * ndy - arrow_sz * 0.42 * py_)
        pygame.draw.polygon(surf, color, [tip, (ax, ay), (bx, by)])


def _draw_tree_in(surf, area, positions, edges, start, end,
                  path_cells, zoom, ox, oy):
    """Render tree with circular nodes and coordinate labels."""
    surf.set_clip(area)
    pygame.draw.rect(surf, TREE_BG, area)

    # Screen coords
    nsc = {}
    for node, px, py, ip in positions:
        nsc[node] = (int(ox + px * NODE_GAP * zoom), int(oy + py * LEVEL_GAP * zoom))

    # Uniform circle radius
    base_r = max(12, int(18 * zoom))
    spec_r = max(16, int(22 * zoom))

    # Build edge lists
    dead_edges = []
    live_edges = []

    for parent, child, ip_edge in edges:
        if parent not in nsc or child not in nsc:
            continue
        p1 = nsc[parent]; p2 = nsc[child]
        rc = spec_r if (child == start or child == end) else base_r
        (live_edges if ip_edge else dead_edges).append((p1, p2, rc, rc))

    # Draw dead-end edges
    ew_dead = max(1, int(zoom * 1.2))
    for p1, p2, rx_c, ry_c in dead_edges:
        _arrow_edge(surf, TREE_FAIL_EDGE, p1, p2, ew_dead, rx_c, ry_c, 0)

    # Draw path edges (glow + solid)
    ew_glow = max(3, int(zoom * 6))
    ew_path = max(2, int(zoom * 3))
    arr_path = max(5, int(6 * zoom)) if zoom >= 0.5 else 0
    for p1, p2, rx_c, ry_c in live_edges:
        _arrow_edge(surf, TREE_GLOW_EDGE, p1, p2, ew_glow, rx_c, ry_c, 0)
    for p1, p2, rx_c, ry_c in live_edges:
        _arrow_edge(surf, TREE_PATH_EDGE, p1, p2, ew_path, rx_c, ry_c, arr_path)

    # Draw circular nodes
    special = []
    for node, px, py, ip in positions:
        if node not in nsc:
            continue
        if node == start or node == end:
            special.append((node, nsc[node], ip))
            continue
        sx, sy = nsc[node]
        if not (area.x - 40 <= sx <= area.right + 40 and
                area.y - 20 <= sy <= area.bottom + 20):
            continue
        r = base_r
        if ip:
            pygame.draw.circle(surf, TREE_PATH_NODE2, (sx, sy), r + 2)
            pygame.draw.circle(surf, TREE_PATH_NODE, (sx, sy), r)
            pygame.draw.circle(surf, WHITE, (sx, sy), r, 1)
        else:
            pygame.draw.circle(surf, TREE_FAIL_NODE, (sx, sy), r)
            if zoom >= 0.4:
                pygame.draw.circle(surf, WHITE, (sx, sy), r, 1)
        # Coordinate label inside node (always visible)
        lbl = f"{node[0]},{node[1]}"
        col = WHITE if ip else (40, 40, 70)
        ls = FTN.render(lbl, True, col)
        surf.blit(ls, ls.get_rect(center=(sx, sy)))

    # Start / End nodes on top
    for node, (sx, sy), ip in special:
        col = TREE_START_NODE if node == start else TREE_END_NODE
        r = spec_r
        pygame.draw.circle(surf, col, (sx, sy), r + 3)
        pygame.draw.circle(surf, col, (sx, sy), r)
        pygame.draw.circle(surf, WHITE, (sx, sy), r, 2)
        coord = f"{node[0]},{node[1]}"
        cs = FTN.render(coord, True, WHITE)
        surf.blit(cs, cs.get_rect(center=(sx, sy)))

    surf.set_clip(None)


def _tree_header(surf, area, shown, total, alg_name="", zoom=1.0):
    """Thin info bar above the tree panel."""
    hdr = pygame.Rect(area.x, area.y, area.w, 28)
    pygame.draw.rect(surf, WHITE, hdr)
    pygame.draw.line(surf, BORDER,
                     (area.x, area.y + 28), (area.right, area.y + 28), 1)
    info = f"Tree: {alg_name}" if alg_name else "Exploration tree"
    info += f"  •  {shown}"
    if shown < total:
        info += f" / {total}"
    info += " nodes"
    _tl(surf, info, FS, GRAY1, area.x + 10, area.y + 14)
    hint = f"Scroll=zoom  Drag=pan  ({zoom:.2f}x)"
    _tr(surf, hint, FX, GRAY2, area.right - 8, area.y + 14)


# ─────────────────────────────────────────────
# DRAW: GRID
# ─────────────────────────────────────────────
def _draw_grid():
    if _tab != 0:
        return
    ps = set(state.path_cells)
    for r in range(state.rows):
        for c in range(state.cols):
            rect = pygame.Rect(g_x + c * g_cell, g_y + r * g_cell, g_cell, g_cell)
            pygame.draw.rect(screen, _ccolor(r, c, ps), rect)
            if g_cell >= 6:
                pygame.draw.rect(screen, BORDER, rect, 1)


# ─────────────────────────────────────────────
# DRAW: VISUALIZE TREE OVERLAY
# ─────────────────────────────────────────────
def _ensure_viz_tree():
    global _viz_tree_ck, _viz_tree_pos, _viz_tree_edges, _viz_tree_bounds
    global _viz_tree_zoom, _viz_tree_ox, _viz_tree_oy, _viz_tree_fit
    key = (id(state.came_from), len(state.came_from), state.start_cell)
    if key == _viz_tree_ck:
        return
    _viz_tree_ck = key
    _viz_tree_pos, _viz_tree_edges, _viz_tree_bounds = _compute_tree_layout(
        state.came_from, state.start_cell, state.path_cells)
    _viz_tree_fit = True


def _draw_viz_tree():
    global _viz_tree_zoom, _viz_tree_ox, _viz_tree_oy, _viz_tree_fit
    if not (_tab == 0 and _viz_show_tree):
        return

    _ensure_viz_tree()
    ax, ay, aw, ah = _ga_viz_tree()
    area = pygame.Rect(ax, ay, aw, ah)

    # Legend bar at bottom
    leg_h = 26
    tree_area = pygame.Rect(ax, ay + 28, aw, ah - 28 - leg_h)

    if not _viz_tree_pos:
        pygame.draw.rect(screen, TREE_BG, area)
        _tc(screen, "Run an algorithm first",
            FS, GRAY2, ax + aw // 2, ay + ah // 2)
        return

    if _viz_tree_fit:
        _viz_tree_zoom, _viz_tree_ox, _viz_tree_oy = _auto_fit(
            _viz_tree_pos, _viz_tree_bounds, tree_area)
        _viz_tree_fit = False

    _draw_tree_in(screen, tree_area, _viz_tree_pos, _viz_tree_edges,
                  state.start_cell, state.end_cell, state.path_cells,
                  _viz_tree_zoom, _viz_tree_ox, _viz_tree_oy)
    _tree_header(screen, area, len(_viz_tree_pos), len(state.came_from),
                 _last_alg_name, _viz_tree_zoom)

    # Legend strip
    leg_rect = pygame.Rect(ax, ay + ah - leg_h, aw, leg_h)
    pygame.draw.rect(screen, WHITE, leg_rect)
    pygame.draw.line(screen, BORDER, (ax, leg_rect.y), (ax + aw, leg_rect.y), 1)
    lx = ax + 10
    for col, lbl in [(TREE_START_NODE, "Start"), (TREE_END_NODE, "End"),
                     (TREE_PATH_NODE, "Path"), (TREE_FAIL_NODE, "Explored")]:
        pygame.draw.circle(screen, col, (lx + 5, leg_rect.centery), 5)
        s = FX.render(lbl, True, GRAY1)
        screen.blit(s, (lx + 13, leg_rect.centery - s.get_height() // 2))
        lx += 13 + s.get_width() + 14



# ─────────────────────────────────────────────
# SHOW TREE BUTTON (Visualize tab, content area)
# ─────────────────────────────────────────────
def _show_tree_btn_rect():
    """Show Tree button — right end of the ribbon body (Visualize tab)."""
    if _tab != 0 or not state.finished or not state.came_from:
        return None
    return pygame.Rect(_ww - 126, _RIB_TAB_H + (_RIB_BODY_H - 30) // 2, 116, 30)


# ─────────────────────────────────────────────
# DRAW: RIBBON
# ─────────────────────────────────────────────
_RIB_LBL_Y = _RIB_H - 14   # group-label centre y


def _rib_div(x):
    """Vertical divider between ribbon groups."""
    pygame.draw.line(screen, GRAY4,
                     (x, _RIB_TAB_H + 10), (x, _RIB_H - 16), 1)


def _rib_grp(label, x1, x2):
    """Draw group name label centred between x1 and x2."""
    s = FXS.render(label.upper(), True, GRAY1)
    screen.blit(s, s.get_rect(centerx=(x1+x2)//2, centery=_RIB_LBL_Y))


def _draw_ribbon_viz():
    """Ribbon content for the Visualize tab."""
    mx2, my2 = pygame.mouse.get_pos()

    # ── Group 0: Algorithm ───────────────────────────────────────────────
    dr = _L["dd"]
    h, p = _is_hov(dr), _is_p(dr)
    bg = PRESS_C if (p and h) else (HOVER_C if h else WHITE)
    pygame.draw.rect(screen, BTN_SH, dr.move(0, 2), border_radius=8)
    pygame.draw.rect(screen, bg, dr, border_radius=8)
    pygame.draw.rect(screen, BORDER, dr, 1, border_radius=8)
    _tl(screen, ALG_NAMES[state.cur_alg], FN, BLACK, dr.x + 10, dr.centery)
    arx, ary = dr.right - 16, dr.centery
    if dd_open:
        pygame.draw.polygon(screen, GRAY1, [(arx-4, ary+3),(arx+4, ary+3),(arx, ary-3)])
    else:
        pygame.draw.polygon(screen, GRAY1, [(arx-4, ary-3),(arx+4, ary-3),(arx, ary+3)])
    _tc(screen, ALG_FULL[state.cur_alg], FXS, GRAY1, dr.centerx, _L["fn_cy"])
    _rib_grp("Algorithm", 10, _L["_g0r"])
    _rib_div(_L["_g0r"] + 7)

    # ── Group 1: Run ────────────────────────────────────────────────────
    x0 = _L["_g0r"] + 14
    if state.running:
        _btn(screen, _L["btn_run"], "Pause", bg=ORANGE, fg=WHITE,
             hov=_is_hov(_L["btn_run"]), pressed=_is_p(_L["btn_run"]))
    else:
        _btn(screen, _L["btn_run"], "Run", bg=GREEN, fg=WHITE,
             hov=_is_hov(_L["btn_run"]), pressed=_is_p(_L["btn_run"]))
    _rib_grp("Run", x0, _L["_g1r"])
    _rib_div(_L["_g1r"] + 7)

    # ── Group 2: Edit ───────────────────────────────────────────────────
    x0 = _L["_g1r"] + 14
    _btn(screen, _L["btn_clr"], "Clear Path",    font=FXS,
         hov=_is_hov(_L["btn_clr"]), pressed=_is_p(_L["btn_clr"]))
    _btn(screen, _L["btn_maz"], "Generate Maze", font=FXS,
         hov=_is_hov(_L["btn_maz"]), pressed=_is_p(_L["btn_maz"]))
    _btn(screen, _L["btn_rst"], "Reset All",     font=FXS, bg=RED, fg=WHITE,
         hov=_is_hov(_L["btn_rst"]), pressed=_is_p(_L["btn_rst"]))
    _rib_grp("Edit", x0, _L["_g2r"])
    _rib_div(_L["_g2r"] + 7)

    # ── Group 3: Speed ──────────────────────────────────────────────────
    x0 = _L["_g2r"] + 14
    spd_cx = _L["_spd_x"] + (28+4+150+4+28) // 2
    _tc(screen, f"Speed \u2014 {state.speed}", FXS, GRAY1,
        spd_cx, _L["_spd_lbl_y"] + 8)
    _btn(screen, _L["btn_sm"], "\u2212", r=8,
         hov=_is_hov(_L["btn_sm"]), pressed=_is_p(_L["btn_sm"]))
    sl = _L["slider"]
    pygame.draw.rect(screen, GRAY3, sl, border_radius=7)
    fw = max(8, int(sl.w * state.speed / MAX_SPEED))
    pygame.draw.rect(screen, ACCENT, pygame.Rect(sl.x, sl.y, fw, sl.h), border_radius=7)
    _btn(screen, _L["btn_sp"], "+", r=8,
         hov=_is_hov(_L["btn_sp"]), pressed=_is_p(_L["btn_sp"]))
    _rib_grp("Speed", x0, _L["_g3r"])
    _rib_div(_L["_g3r"] + 7)

    # ── Group 4: Grid ───────────────────────────────────────────────────
    x0 = _L["_g3r"] + 14
    gx = _L["_grid_x"]
    _tl(screen, "Rows", FXS, GRAY1, gx + 2, _L["btn_rm"].centery)
    _tl(screen, "Cols", FXS, GRAY1, gx + 2, _L["btn_cm"].centery)
    for k in ("btn_rm", "btn_rp", "btn_cm", "btn_cp"):
        _btn(screen, _L[k], "\u2212" if k.endswith("m") else "+", font=FB, r=6,
             hov=_is_hov(_L[k]), pressed=_is_p(_L[k]))
    for field, rk, val in [("rows", "inp_r", state.rows), ("cols", "inp_c", state.cols)]:
        r2 = _L[rk]
        if _edit == field:
            pygame.draw.rect(screen, WHITE, r2, border_radius=5)
            pygame.draw.rect(screen, ACCENT, r2, 2, border_radius=5)
            _tc(screen, _etext + "|", FXS, BLACK, r2.centerx, r2.centery)
        else:
            pygame.draw.rect(screen, (248, 248, 252), r2, border_radius=5)
            pygame.draw.rect(screen, BORDER, r2, 1, border_radius=5)
            _tc(screen, str(val), FXS, BLACK, r2.centerx, r2.centery)
    _rib_grp("Grid", x0, _L["_g4r"])
    _rib_div(_L["_g4r"] + 7)

    # ── Group 5: Points ─────────────────────────────────────────────────
    x0 = _L["_g4r"] + 14
    _btn(screen, _L["btn_ss"], "Set Start [S]", font=FXS,
         selected=(state.set_mode == "start"),
         hov=_is_hov(_L["btn_ss"]), pressed=_is_p(_L["btn_ss"]))
    _btn(screen, _L["btn_se"], "Set End [E]",   font=FXS,
         selected=(state.set_mode == "end"),
         hov=_is_hov(_L["btn_se"]), pressed=_is_p(_L["btn_se"]))
    _rib_grp("Points", x0, _L["_g5r"])
    _rib_div(_L["_g5r"] + 7)

    # ── Group 6: Statistics ─────────────────────────────────────────────
    x0 = _L["_g5r"] + 14
    sx = _L["_stats_x"];  sy = _L["_stats_y"]
    st = state.stats
    pairs = [("Nodes", str(st["nodes"])), ("Path", str(st["path"])),
             ("Cost",  str(st["cost"])), ("Time", f"{st['time']*1000:.1f} ms")]
    cw = 85
    for i, (lbl, val) in enumerate(pairs):
        cx2 = sx + i*cw + cw//2
        _tc(screen, lbl, FXS, GRAY1, cx2, sy + 10)
        _tc(screen, val, FX,  BLACK,  cx2, sy + 30)
    found = st["found"]
    if state.running:     stxt, scol = "Running...", ORANGE
    elif found is True:   stxt, scol = "Path Found", GREEN
    elif found is False:  stxt, scol = "No Path",    RED
    else:                 stxt, scol = "",            GRAY1
    if stxt:
        _tc(screen, stxt, FX, scol, sx + 4*cw + 50, sy + 20)
    _rib_grp("Statistics", x0, min(_ww - 130, sx + 4*cw + 100))

    # ── Show / Hide Tree button (far right of ribbon) ────────────────────
    btn = _show_tree_btn_rect()
    if btn:
        lbl = "Hide Tree" if _viz_show_tree else "Show Tree"
        bg2 = ORANGE if _viz_show_tree else ACCENT
        _btn(screen, btn, lbl, font=FXS, bg=bg2, fg=WHITE,
             hov=btn.collidepoint(mx2, my2), r=7)


def _rib_race_toggle_rects():
    """8 algorithm toggle rects inside the Race ribbon."""
    n = len(ALG_NAMES)
    bw = 115;  bh = _RIB_H - _RIB_TAB_H - 28;  gap = 6
    ry = _RIB_TAB_H + 10
    x  = 10
    return [pygame.Rect(x + i*(bw+gap), ry, bw, bh) for i in range(n)]


def _rib_race_run_rect():
    """Start/Stop Race button rect in the Race ribbon."""
    n   = len(ALG_NAMES)
    bw  = 115;  gap = 6
    bh  = _RIB_H - _RIB_TAB_H - 28
    ry  = _RIB_TAB_H + 10
    x   = 10 + n*(bw+gap) + 14 + 14   # after group + divider + padding
    return pygame.Rect(x, ry, 140, bh)


def _draw_ribbon_race():
    """Ribbon content for the Race tab."""
    mx2, my2 = pygame.mouse.get_pos()
    n    = len(ALG_NAMES)
    bw   = 115;  gap = 6
    rects = _rib_race_toggle_rects()

    # ── Group: Algorithms ───────────────────────────────────────────────
    for i, r in enumerate(rects):
        sel = i in set(_race_order)
        ci  = _BAR_PALETTE[i % len(_BAR_PALETTE)]
        hov = r.collidepoint(mx2, my2)
        if sel:
            pygame.draw.rect(screen, BTN_SH, r.move(0, 2), border_radius=8)
            pygame.draw.rect(screen, ci, r, border_radius=8)
            fg2 = WHITE
        else:
            _btn(screen, r, "", font=FXS, hov=hov, shadow=not sel)
            # colour accent bar at top of un-selected button
            pygame.draw.rect(screen, ci,
                             pygame.Rect(r.x+2, r.y+2, r.w-4, 5), border_radius=3)
            fg2 = BLACK
        # Wrap name onto 2 lines
        words = ALG_NAMES[i].split()
        mid   = (len(words) + 1) // 2
        l1    = " ".join(words[:mid]);  l2 = " ".join(words[mid:])
        cy2   = r.centery + (0 if not l2 else -9)
        _tc(screen, l1, FXS, fg2, r.centerx, cy2)
        if l2:
            _tc(screen, l2, FXS, fg2, r.centerx, cy2 + 18)

    alg_right = 10 + n*(bw+gap)
    _rib_grp("Algorithms", 10, alg_right)
    _rib_div(alg_right + 7)

    # ── Group: Race ─────────────────────────────────────────────────────
    rb = _rib_race_run_rect()
    if _race_running:
        _btn(screen, rb, "Stop Race", bg=RED, fg=WHITE, font=FXS,
             hov=rb.collidepoint(mx2, my2))
    elif len(_race_order) >= 2:
        lbl = f"Start Race ({len(_race_order)})"
        _btn(screen, rb, lbl, bg=GREEN, fg=WHITE, font=FXS,
             hov=rb.collidepoint(mx2, my2))
    else:
        pygame.draw.rect(screen, GRAY3, rb, border_radius=8)
        _tc(screen, "Select 2+ algos", FXS, GRAY1, rb.centerx, rb.centery)
    _rib_grp("Race", rb.x, rb.right + 6)



def _draw_ribbon():
    """Draw the full MS-Word-style ribbon (tab row + body)."""
    # Ribbon background
    pygame.draw.rect(screen, WHITE, (0, 0, _ww, _RIB_H))
    # Bottom shadow line
    pygame.draw.line(screen, BORDER, (0, _RIB_H),   (_ww, _RIB_H),   2)
    pygame.draw.line(screen, GRAY4,  (0, _RIB_H+1), (_ww, _RIB_H+1), 1)

    # ── Tab row ──────────────────────────────────────────────────────────
    tx = 10
    for i, name in enumerate(_TAB_NAMES):
        tw = max(90, FB.size(name)[0] + 24) if hasattr(FB, 'size') else 100
        r  = pygame.Rect(tx, 3, tw, _RIB_TAB_H - 4)
        if i == _tab:
            pygame.draw.rect(screen, ACCENT, r, border_radius=6)
            _tc(screen, name, FB, WHITE, r.centerx, r.centery)
        else:
            hov = r.collidepoint(pygame.mouse.get_pos())
            if hov:
                pygame.draw.rect(screen, HOVER_C, r, border_radius=6)
            _tc(screen, name, FB, ACCENT if hov else BLACK, r.centerx, r.centery)
        tx += tw + 4

    # ── Separator between tab row and ribbon body ─────────────────────────
    pygame.draw.line(screen, GRAY4, (0, _RIB_TAB_H), (_ww, _RIB_TAB_H), 1)

    # ── Ribbon body (tab-specific) ────────────────────────────────────────
    if _tab == 0:
        _draw_ribbon_viz()
    elif _tab == 1:
        _draw_ribbon_race()


# kept as no-op so draw_all() call still compiles
def _draw_panel():
    pass



# ─────────────────────────────────────────────
# DRAW: DROPDOWN
# ─────────────────────────────────────────────
def _draw_dd():
    if not dd_open:
        return
    dr = _L["dd"]
    n  = len(ALG_NAMES)
    ih = 42
    cont = pygame.Rect(dr.x, dr.bottom + 4, dr.w, n * ih)
    sh = pygame.Surface((cont.w + 20, cont.h + 20), pygame.SRCALPHA)
    for i in range(5):
        sp = 5 - i; a = 4 + i * 3
        pygame.draw.rect(sh, (0, 0, 0, a),
                         (10 - sp, 11 + i - sp, cont.w + sp*2, cont.h + sp*2),
                         border_radius=10 + sp)
    screen.blit(sh, (cont.x - 10, cont.y - 10))
    pygame.draw.rect(screen, WHITE, cont, border_radius=10)
    pygame.draw.rect(screen, BORDER, cont, 1, border_radius=10)
    mx, my = pygame.mouse.get_pos()
    for i in range(n):
        iy = cont.y + i * ih
        ir = pygame.Rect(cont.x, iy, cont.w, ih)
        if ir.collidepoint(mx, my):
            pygame.draw.rect(screen, HOVER_C,
                             pygame.Rect(cont.x + 1, iy, cont.w - 2, ih))
        _tl(screen, ALG_NAMES[i], FN, BLACK, ir.x + 14, ir.centery)
        if i == state.cur_alg:
            pygame.draw.circle(screen, ACCENT, (ir.right - 18, ir.centery), 4)
        if i < n - 1:
            pygame.draw.line(screen, BORDER,
                             (ir.x + 12, ir.bottom),
                             (ir.right - 12, ir.bottom), 1)


# ─────────────────────────────────────────────
# DRAW: TABS
# ─────────────────────────────────────────────
_TAB_NAMES = ("Visualize", "Race")

def _tab_rects():
    """Old tab rects — now tabs live in the ribbon; kept so old references compile."""
    tx = 10
    rects = []
    for name in _TAB_NAMES:
        tw2 = max(90, FB.size(name)[0] + 24) if hasattr(FB, 'size') else 100
        rects.append(pygame.Rect(tx, 3, tw2, _RIB_TAB_H - 4))
        tx += tw2 + 4
    return rects

def _draw_tabs():
    pass   # tabs are now drawn inside _draw_ribbon()


# ─────────────────────────────────────────────
# RACE TAB
# ─────────────────────────────────────────────
_RACE_TOOLBAR_H = 0     # toolbar moved to ribbon; kept for layout arithmetic
_RACE_GAP       = 8
_RACE_NAME_H    = 30    # header inside each maze panel
_RACE_TREE_H    = 200   # height of tree panel below each maze (when shown)


def _race_panel_layout():
    """Returns (panel_rects, tree_rects, grid_bottom).
    panel_rects: maze panel rects for each runner in _race_order
    tree_rects:  tree panel rects (or None if not show_trees)
    grid_bottom: y coordinate where panels end
    """
    ax, ay, aw, ah = _ga()
    n = len(_race_order)
    if n == 0:
        return [], [], ay + _RACE_TOOLBAR_H

    cols = min(n, 4)
    rows = (n + cols - 1) // cols
    gap  = _RACE_GAP
    pw   = (aw - gap*(cols + 1)) // cols

    # Maze panel height: split the remaining space
    avail = ah - _RACE_TOOLBAR_H - gap
    if _race_show_trees:
        maze_h = max(100, (avail - rows*(gap + _RACE_TREE_H) - gap) // rows)
    else:
        maze_h = max(100, (avail - gap*(rows + 1)) // rows)

    cell_h = maze_h + (_RACE_TREE_H + gap if _race_show_trees else 0)

    panel_rects = []
    tree_rects  = []
    for i, idx in enumerate(_race_order):
        row = i // cols
        col = i % cols
        x = ax + gap + col*(pw + gap)
        y = ay + _RACE_TOOLBAR_H + gap + row*(cell_h + gap) - _race_scroll

        scale = _race_scales.get(idx, 0.0)
        if scale < 0.99:
            cw = max(4, int(pw   * scale))
            ch = max(4, int(maze_h * scale))
            panel_rects.append(pygame.Rect(x + (pw - cw)//2,
                                           y + (maze_h - ch)//2, cw, ch))
        else:
            panel_rects.append(pygame.Rect(x, y, pw, maze_h))

        if _race_show_trees and scale >= 0.99:
            tree_rects.append(pygame.Rect(x, y + maze_h + gap, pw, _RACE_TREE_H))
        else:
            tree_rects.append(None)

    grid_bottom = (ay + _RACE_TOOLBAR_H + gap
                   + rows*(cell_h + gap))
    return panel_rects, tree_rects, grid_bottom


def _draw_race_mini_maze(surf, rect, runner, alg_idx=None):
    """Draw a mini maze panel for one runner (supports zoom/pan).
    When no runner exists but alg_idx is given, shows a static maze preview.
    Uses rounded corners via SRCALPHA masking.
    """
    if rect.w < 10 or rect.h < 10:
        return

    _cr = 14  # corner radius

    # Determine algorithm index
    idx = None
    if runner and "idx" in runner:
        idx = runner["idx"]
    elif alg_idx is not None:
        idx = alg_idx

    if idx is None:
        pygame.draw.rect(surf, WHITE, rect, border_radius=_cr)
        pygame.draw.rect(surf, BORDER, rect, 1, border_radius=_cr)
        return

    alpha = int(_race_scales.get(idx, 1.0) * 255)
    tmp = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    tmp.fill((*BG, 255))

    rows, cols = state.rows, state.cols
    base_cell = max(1, min((rect.w) // cols, (rect.h - _RACE_NAME_H) // rows))

    # Runner has zoom/pan; static preview just centres
    if runner and "idx" in runner:
        mz   = runner.get("maze_zoom", 1.0)
        cell = max(1, int(base_cell * mz))
        gw   = cols * cell
        gh   = rows * cell
        if runner.get("maze_ox") is None:
            runner["maze_ox"] = float((rect.w - gw) // 2)
            runner["maze_oy"] = float((_RACE_NAME_H + (rect.h - _RACE_NAME_H - gh) // 2))
        ox_m = int(runner["maze_ox"])
        oy_m = int(runner["maze_oy"])
        ps    = set(runner.get("path", []))
        vis   = runner.get("vis",   set())
        front = runner.get("front", set())
    else:
        cell = base_cell
        gw   = cols * cell
        gh   = rows * cell
        ox_m = (rect.w - gw) // 2
        oy_m = _RACE_NAME_H + (rect.h - _RACE_NAME_H - gh) // 2
        ps    = set()
        vis   = set()
        front = set()

    # Draw maze cells (skip header area)
    content_clip = pygame.Rect(0, _RACE_NAME_H, rect.w, rect.h - _RACE_NAME_H)
    tmp.set_clip(content_clip)
    for row in range(rows):
        for col in range(cols):
            cx = ox_m + col * cell
            cy = oy_m + row * cell
            if cx + cell < 0 or cx > rect.w or cy + cell < _RACE_NAME_H or cy > rect.h:
                continue
            cell_color = _ccolor(row, col, ps, vis=vis, front=front)
            cell_rect = pygame.Rect(cx, cy, cell, cell)
            pygame.draw.rect(tmp, (*cell_color, 255), cell_rect)
            if cell >= 4:
                pygame.draw.rect(tmp, (*BORDER, 255), cell_rect, 1)
    tmp.set_clip(None)

    # Header bar
    pygame.draw.rect(tmp, (30, 30, 30, 255), (0, 0, rect.w, _RACE_NAME_H))
    name = ALG_NAMES[idx]
    s = FS.render(name, True, WHITE)
    tmp.blit(s, s.get_rect(centerx=rect.w // 2, centery=_RACE_NAME_H // 2))

    # Stats badge at bottom if done
    if runner and runner.get("done") and runner.get("stats"):
        st = runner["stats"]
        if st.get("found"):
            badge_col = (52, 199, 89)
            badge_txt = f"Path: {st['path']}  |  {st['time']*1000:.0f} ms"
        else:
            badge_col = (255, 59, 48)
            badge_txt = "No path found"
        bw2 = min(rect.w - 8, 240)
        bh2 = 24
        br  = pygame.Rect((rect.w - bw2) // 2, rect.h - bh2 - 6, bw2, bh2)
        pygame.draw.rect(tmp, (*badge_col, 255), br, border_radius=6)
        bs = FX.render(badge_txt, True, WHITE)
        tmp.blit(bs, bs.get_rect(center=br.center))

    # Apply rounded corner mask
    mask = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    mask.fill((255, 255, 255, 0))
    pygame.draw.rect(mask, (255, 255, 255, alpha),
                     (0, 0, rect.w, rect.h), border_radius=_cr)
    tmp.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

    surf.blit(tmp, (rect.x, rect.y))
    pygame.draw.rect(surf, BORDER, rect, 1, border_radius=_cr)


def _race_chart_draw(x, y, w, h, title, key):
    card = pygame.Rect(x, y, w, h)
    ax2, ay2, aw2, ah2 = _ga()
    clip = pygame.Rect(ax2, ay2, aw2, ah2)
    if card.bottom < clip.top or card.top > clip.bottom:
        return
    _card(screen, card)
    screen.blit(FB.render(title, True, BLACK), (x + 16, y + 10))

    data = _race_results
    n    = len(data)
    if n == 0:
        return

    ml, mr, mt, mb = 55, 16, 38, 28
    ca_x = x + ml; ca_y = y + mt
    ca_w = w - ml - mr; ca_h = h - mt - mb
    vals = [d[key]*1000 if key == "time" else d[key] for d in data]
    mv   = max(vals) if vals else 1
    if mv == 0: mv = 1

    for i in range(5):
        gy = ca_y + ca_h - int(ca_h * i / 4)
        if i > 0:
            pygame.draw.line(screen, GRAY4, (ca_x, gy), (ca_x + ca_w, gy), 1)
        gv  = mv * i / 4
        lbl = f"{gv:.1f}" if key == "time" else f"{gv:.0f}"
        s   = FX.render(lbl, True, GRAY2)
        screen.blit(s, (ca_x - s.get_width() - 6, gy - s.get_height()//2))

    pygame.draw.line(screen, GRAY3, (ca_x, ca_y + ca_h), (ca_x + ca_w, ca_y + ca_h), 1)
    pygame.draw.line(screen, GRAY3, (ca_x, ca_y), (ca_x, ca_y + ca_h), 1)

    bw2 = max(20, min(55, (ca_w - (n + 1)*10) // n))
    sx2 = ca_x + (ca_w - (n*bw2 + (n-1)*10))//2
    for i, (d, v) in enumerate(zip(data, vals)):
        bh2 = max(3, int(ca_h * v / mv))
        bx2 = sx2 + i*(bw2 + 10)
        by2 = ca_y + ca_h - bh2
        col = _BAR_PALETTE[i % len(_BAR_PALETTE)]
        pygame.draw.rect(screen, col, (bx2, by2, bw2, bh2), border_radius=4)
        if bh2 > 4:
            pygame.draw.rect(screen, col, (bx2, by2 + bh2 - 4, bw2, 4))
        vs = f"{v:.1f}" if key == "time" else str(int(v))
        sv = FX.render(vs, True, BLACK)
        screen.blit(sv, sv.get_rect(centerx=bx2 + bw2//2, bottom=max(by2 - 3, ca_y)))
        sn = FX.render(d["name"][:6], True, GRAY1)
        screen.blit(sn, sn.get_rect(centerx=bx2 + bw2//2, top=ca_y + ca_h + 4))


def _draw_race():
    global _race_content_h
    if _tab != 1:
        return

    ax, ay, aw, ah = _ga()
    area = pygame.Rect(ax, ay, aw, ah)
    pygame.draw.rect(screen, BG, area)

    # ── Maze panels (toolbar is now in the ribbon) ──
    panel_rects, tree_rects, grid_bottom = _race_panel_layout()

    # Clip everything below toolbar
    clip_area = pygame.Rect(ax, ay + _RACE_TOOLBAR_H, aw,
                            ah - _RACE_TOOLBAR_H)
    screen.set_clip(clip_area)

    for i, idx in enumerate(_race_order):
        runner = _race_runners.get(idx, {})
        pr     = panel_rects[i]
        _draw_race_mini_maze(screen, pr, runner, alg_idx=idx)

        tr = tree_rects[i]
        if tr and runner.get("done") and runner.get("tree_pos") is not None:
            # Draw tree panel
            pygame.draw.rect(screen, TREE_BG, tr)
            pygame.draw.rect(screen, BORDER, tr, 1, border_radius=4)
            inner = pygame.Rect(tr.x + 1, tr.y + 1, tr.w - 2, tr.h - 2)

            if runner.get("tree_fit"):
                tz, tox, toy = _auto_fit(
                    runner["tree_pos"], runner["tree_bounds"], inner, padding=8)
                runner["tree_zoom"] = tz
                runner["tree_ox"]   = tox
                runner["tree_oy"]   = toy
                runner["tree_fit"]  = False
                runner["_panel_x"]  = inner.x
                runner["_panel_y"]  = inner.y
            else:
                # Adjust tree position when panel moves (e.g. scrolling)
                last_x = runner.get("_panel_x", inner.x)
                last_y = runner.get("_panel_y", inner.y)
                if last_x != inner.x or last_y != inner.y:
                    runner["tree_ox"] += inner.x - last_x
                    runner["tree_oy"] += inner.y - last_y
                    runner["_panel_x"] = inner.x
                    runner["_panel_y"] = inner.y

            _draw_tree_in(screen, inner, runner["tree_pos"], runner["tree_edges"],
                          state.start_cell, state.end_cell,
                          runner.get("path", []),
                          runner["tree_zoom"], runner["tree_ox"], runner["tree_oy"])

    screen.set_clip(None)

    # Show/Hide Trees button is now drawn in the ribbon (_draw_ribbon_race)

    # ── Content height for scrolling (always updated) ──
    base_content_h = max(0, grid_bottom - (ay + _RACE_TOOLBAR_H))

    # ── Charts (only when race completed) ──
    if not _race_results:
        _race_content_h = base_content_h
        return

    charts_info = [
        ("Nodes Visited", "nodes"),
        ("Path Length",   "path"),
        ("Cost",          "cost"),
        ("Time (ms)",     "time"),
    ]
    ch_h = 165; ch_gap = 12
    total_charts_h = len(charts_info) * (ch_h + ch_gap) - ch_gap + 16
    _race_content_h = base_content_h + total_charts_h + 32

    chart_top   = grid_bottom + 16
    charts_clip = pygame.Rect(ax, chart_top, aw, ay + ah - chart_top)
    screen.set_clip(charts_clip)
    cy = chart_top + 8 - _race_scroll
    for title, key in charts_info:
        _race_chart_draw(ax + 10, cy, aw - 20, ch_h, title, key)
        cy += ch_h + ch_gap
    screen.set_clip(None)




# ─────────────────────────────────────────────
# RACE LOGIC
# ─────────────────────────────────────────────
def _start_race():
    global _race_runners, _race_running, _race_done, _race_results
    global _race_show_trees, _race_scroll

    state.clear_search()
    _race_done      = False
    _race_show_trees = False
    _race_results   = []
    _race_scroll    = 0
    _race_runners   = {}

    for idx in _race_order:
        state._counter[0] = 0
        runner = {
            "idx":       idx,
            "gen":       ALGO_FUNCS[idx](),
            "vis":       set(),
            "front":     set(),
            "done":      False,
            "path":      [],
            "stats":     None,
            "came_from": {},
            # Maze pan/zoom sub-state (None = auto-centre on first draw)
            "maze_zoom": 1.0,
            "maze_ox":   None,
            "maze_oy":   None,
            # Tree sub-state
            "tree_pos":    None,
            "tree_edges":  None,
            "tree_bounds": (0, 0),
            "tree_zoom":   1.0,
            "tree_ox":     0.0,
            "tree_oy":     0.0,
            "tree_fit":    True,
        }
        _race_runners[idx] = runner

    state.clear_search()
    _race_running = True


def _advance_race():
    """Called once per frame; advances all running generators."""
    global _race_running, _race_done, _race_results

    if not _race_running:
        return

    all_done = True
    for idx in _race_order:
        runner = _race_runners.get(idx)
        if not runner or runner["done"]:
            continue
        all_done = False
        for _ in range(state.speed):
            try:
                vis, front = next(runner["gen"])
                runner["vis"]   = vis
                runner["front"] = front.copy() if hasattr(front, "copy") else set(front)
            except StopIteration:
                runner["done"]      = True
                runner["path"]      = list(state.path_cells)
                runner["stats"]     = dict(state.stats)
                runner["came_from"] = dict(state.came_from)
                state.clear_search()
                break
            except Exception as exc:
                print(f"[Race error] {ALG_NAMES[idx]}: {exc}")
                runner["done"]  = True
                runner["stats"] = {"nodes": 0, "path": 0, "cost": 0,
                                   "time": 0.0, "found": None}
                state.clear_search()
                break

    if all_done:
        _race_running = False
        _race_done    = True
        _race_results = [
            {"name": ALG_NAMES[idx], **_race_runners[idx]["stats"]}
            for idx in _race_order
            if _race_runners.get(idx) and _race_runners[idx].get("stats")
        ]


def _build_race_trees():
    """Compute tree layouts for all completed runners (called on Show Trees toggle)."""
    for idx in _race_order:
        runner = _race_runners.get(idx)
        if not runner or not runner.get("done"):
            continue
        if runner.get("tree_pos") is not None:
            continue   # already built
        pos, edges, bnd = _compute_tree_layout(
            runner["came_from"], state.start_cell, runner["path"])
        runner["tree_pos"]    = pos
        runner["tree_edges"]  = edges
        runner["tree_bounds"] = bnd
        runner["tree_fit"]    = True


def _update_race_scales():
    """Smooth panel fade-in / fade-out animation."""
    order_set = set(_race_order)
    for idx in list(_race_scales.keys()):
        target  = 1.0 if idx in order_set else 0.0
        current = _race_scales[idx]
        diff    = target - current
        if abs(diff) < 0.01:
            _race_scales[idx] = target
        else:
            _race_scales[idx] = current + diff * 0.18


# ─────────────────────────────────────────────
# DRAW ALL
# ─────────────────────────────────────────────
def draw_all():
    screen.fill(BG)
    _draw_grid()
    _draw_viz_tree()
    _draw_race()
    _draw_ribbon()   # draws tab row + ribbon body (replaces old panel + tabs)
    _draw_dd()
    pygame.display.flip()


# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────
def run():
    global dd_open, _last_fin, _ww, _wh, screen
    global _tab, _pressed, _edit, _etext
    global _last_alg_name
    global _viz_show_tree, _viz_tree_zoom, _viz_tree_ox, _viz_tree_oy
    global _viz_tree_drag, _viz_tree_fit
    global _race_order, _race_scales, _race_scroll, _race_running, _race_done
    global _race_show_trees, _race_drag
    global _maze_drag, _race_maze_drag, _dragging_wall, _dragging_slider
    global g_x, g_y, g_cell

    while True:
        # ── Advance single-algo ────────────────────────────────────────────
        if state.running and state.alg_gen and not state.finished:
            for _ in range(state.speed):
                try:
                    vis, front = next(state.alg_gen)
                    state.vis_cells   = vis
                    state.front_cells = front
                except StopIteration:
                    state.running = False
                    break
                except Exception as exc:
                    print(f"[Algo error] {exc}")
                    state.running = False
                    break

        # ── Advance race ───────────────────────────────────────────────────
        _advance_race()
        _update_race_scales()

        # ── Save to history ────────────────────────────────────────────────
        if state.finished and not _last_fin:
            if state.stats["found"] is not None:
                state.run_history.append({
                    "name":  ALG_NAMES[state.cur_alg],
                    "nodes": state.stats["nodes"],
                    "path":  state.stats["path"],
                    "cost":  state.stats["cost"],
                    "time":  state.stats["time"],
                })
        _last_fin = state.finished

        # ── Events ────────────────────────────────────────────────────────
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                return

            elif ev.type == pygame.VIDEORESIZE:
                _ww, _wh = ev.size
                screen = pygame.display.set_mode((_ww, _wh), pygame.RESIZABLE)
                recalc_grid()
                _viz_tree_fit = True

            elif ev.type == pygame.MOUSEBUTTONDOWN:
                ex, ey = ev.pos
                btn_ev = ev.button

                # Track pressed button (Visualize ribbon buttons only)
                _pressed = None
                if _tab == 0:
                    for k in ("btn_run", "btn_clr", "btn_maz", "btn_rst",
                              "btn_sm", "btn_sp", "btn_rm", "btn_rp",
                              "btn_cm", "btn_cp", "btn_ss", "btn_se", "dd"):
                        if _L[k].collidepoint(ex, ey):
                            _pressed = _L[k]
                            break

                # Dropdown intercept
                if dd_open:
                    dr = _L["dd"]
                    ih = 42
                    cont = pygame.Rect(dr.x, dr.bottom + 4,
                                       dr.w, len(ALG_NAMES)*ih)
                    if cont.collidepoint(ex, ey):
                        idx = (ey - cont.y) // ih
                        if 0 <= idx < len(ALG_NAMES):
                            if state.running: state.clear_search()
                            state.cur_alg = idx
                    dd_open = False
                    continue

                # Tab switching
                for i, tr in enumerate(_tab_rects()):
                    if tr.collidepoint(ex, ey):
                        if i != _tab:
                            _tab = i
                            recalc_grid()
                        break

                # Click outside input → apply
                if _edit:
                    if not _L["inp_r"].collidepoint(ex, ey) and \
                       not _L["inp_c"].collidepoint(ex, ey):
                        _apply_edit()

                # ── Visualize ribbon buttons (tab 0 only) ──────────────────
                if _tab == 0:
                  if _L["dd"].collidepoint(ex, ey):
                    dd_open = True

                  elif _L["btn_run"].collidepoint(ex, ey):
                    if state.running:
                        state.running = False
                    else:
                        if state.finished:
                            state.clear_search()
                            _viz_show_tree = False
                            recalc_grid()
                        state.start_algorithm(ALGO_FUNCS[state.cur_alg])
                        _last_alg_name = ALG_NAMES[state.cur_alg]
                        _last_fin = False

                  elif _L["btn_clr"].collidepoint(ex, ey):
                    state.clear_search()
                    _last_fin = False
                    _viz_show_tree = False
                    recalc_grid()

                  elif _L["btn_maz"].collidepoint(ex, ey):
                    state.clear_search()
                    _last_fin = False
                    _viz_show_tree = False
                    recalc_grid()
                    generate_maze()

                  elif _L["btn_rst"].collidepoint(ex, ey):
                    state.clear_search()
                    _last_fin = False
                    state.walls.clear()
                    _viz_show_tree = False
                    recalc_grid()

                  elif _L["btn_rm"].collidepoint(ex, ey):
                    _change_grid(-1, 0)
                  elif _L["btn_rp"].collidepoint(ex, ey):
                    _change_grid(1, 0)
                  elif _L["btn_cm"].collidepoint(ex, ey):
                    _change_grid(0, -1)
                  elif _L["btn_cp"].collidepoint(ex, ey):
                    _change_grid(0, 1)

                  elif _L["inp_r"].collidepoint(ex, ey):
                    _edit = "rows"; _etext = str(state.rows)
                  elif _L["inp_c"].collidepoint(ex, ey):
                    _edit = "cols"; _etext = str(state.cols)

                  elif _L["btn_sm"].collidepoint(ex, ey):
                    state.speed = max(1, state.speed - 5)
                  elif _L["btn_sp"].collidepoint(ex, ey):
                    state.speed = min(MAX_SPEED, state.speed + 5)
                  elif _L["slider"].collidepoint(ex, ey):
                    ratio = (ex - _L["slider"].x) / _L["slider"].w
                    state.speed = max(1, min(MAX_SPEED, int(ratio * MAX_SPEED)))
                    _dragging_slider = True

                  elif _L["btn_ss"].collidepoint(ex, ey):
                    state.set_mode = None if state.set_mode == "start" else "start"
                  elif _L["btn_se"].collidepoint(ex, ey):
                    state.set_mode = None if state.set_mode == "end" else "end"

                  else:
                    # ── Visualize: non-ribbon clicks ─────────────────────────
                    # Show / Hide Tree toggle (ribbon button, right side)
                    if state.finished and state.came_from:
                        btn = _show_tree_btn_rect()
                        if btn and btn.collidepoint(ex, ey):
                            _viz_show_tree = not _viz_show_tree
                            _viz_tree_fit  = True
                            recalc_grid()
                            continue

                    # Tree pan in split view
                    if _viz_show_tree:
                        vax, vay, vaw, vah = _ga_viz_tree()
                        if pygame.Rect(vax, vay, vaw, vah).collidepoint(ex, ey):
                            _viz_tree_drag = (ex, ey, _viz_tree_ox, _viz_tree_oy)
                            continue
                        # Click in maze half → pan the maze
                        maz_x, maz_y, maz_w, maz_h = _ga_maze()
                        if pygame.Rect(maz_x, maz_y, maz_w, maz_h).collidepoint(ex, ey):
                            _maze_drag = (ex, ey, g_x, g_y)
                            continue

                    # Grid interaction (wall drawing disabled in show-tree mode)
                    gc = _gpos(ex, ey)
                    if gc is not None:
                        r, c = gc
                        if state.set_mode == "start":
                            state.start_cell = (r, c)
                            state.set_mode   = None
                        elif state.set_mode == "end":
                            state.end_cell = (r, c)
                            state.set_mode = None
                        elif not state.running and not _viz_show_tree:
                            if btn_ev == 1:
                                if (r, c) not in (state.start_cell, state.end_cell):
                                    state.walls.add((r, c))
                                _dragging_wall = True
                            elif btn_ev == 3:
                                state.walls.discard((r, c))
                                _dragging_wall = False

                elif _tab == 1:
                        # Run/Stop button (in ribbon)
                        rb = _rib_race_run_rect()
                        if rb.collidepoint(ex, ey):
                            if _race_running:
                                _race_running = False
                                _race_done    = True
                                _race_results = [
                                    {"name": ALG_NAMES[i],
                                     **_race_runners[i]["stats"]}
                                    for i in _race_order
                                    if _race_runners.get(i) and
                                       _race_runners[i].get("stats")
                                ]
                            elif len(_race_order) >= 2:
                                _start_race()
                            continue

                        # Toggle algorithm buttons (in ribbon)
                        for i, rect in enumerate(_rib_race_toggle_rects()):
                            if rect.collidepoint(ex, ey) and not _race_running:
                                if i in set(_race_order):
                                    _race_order.remove(i)
                                else:
                                    if len(_race_order) < 8:
                                        _race_order.append(i)
                                        _race_scales[i] = 0.0
                                break

                        # Click on a race maze panel → start maze pan
                        p_rects_m, _, _ = _race_panel_layout()
                        for i, idx in enumerate(_race_order):
                            pr = p_rects_m[i] if i < len(p_rects_m) else None
                            runner = _race_runners.get(idx)
                            if pr and runner and "idx" in runner and pr.collidepoint(ex, ey):
                                if runner.get("maze_ox") is None:
                                    rows_c, cols_c = state.rows, state.cols
                                    bc = max(1, min(pr.w // cols_c, pr.h // rows_c))
                                    mz = runner.get("maze_zoom", 1.0)
                                    cell_c = max(1, int(bc * mz))
                                    runner["maze_ox"] = float((pr.w - cols_c * cell_c) // 2)
                                    runner["maze_oy"] = float((pr.h - rows_c * cell_c) // 2)
                                _race_maze_drag = (idx, ex, ey,
                                                   runner["maze_ox"],
                                                   runner["maze_oy"])
                                break

                        # Click on a race tree panel → start tree pan
                        if _race_show_trees:
                            _, tree_rects, _ = _race_panel_layout()
                            for i, idx in enumerate(_race_order):
                                tr = tree_rects[i]
                                runner = _race_runners.get(idx)
                                if tr and runner and runner.get("tree_pos") is not None:
                                    if tr.collidepoint(ex, ey):
                                        _race_drag = (idx, ex, ey,
                                                      runner["tree_ox"],
                                                      runner["tree_oy"])
                                        break

            elif ev.type == pygame.MOUSEBUTTONUP:
                _dragging_wall   = None
                _dragging_slider = False
                _pressed         = None
                _viz_tree_drag   = None
                _maze_drag       = None
                _race_drag       = None
                _race_maze_drag  = None

            elif ev.type == pygame.MOUSEMOTION:
                if _viz_tree_drag is not None:
                    dx = ev.pos[0] - _viz_tree_drag[0]
                    dy = ev.pos[1] - _viz_tree_drag[1]
                    _viz_tree_ox = _viz_tree_drag[2] + dx
                    _viz_tree_oy = _viz_tree_drag[3] + dy

                elif _race_drag is not None:
                    ridx, smx, smy, sox, soy = _race_drag
                    dx = ev.pos[0] - smx
                    dy = ev.pos[1] - smy
                    runner = _race_runners.get(ridx)
                    if runner:
                        runner["tree_ox"] = sox + dx
                        runner["tree_oy"] = soy + dy

                elif _race_maze_drag is not None:
                    ridx, smx, smy, sox, soy = _race_maze_drag
                    dx = ev.pos[0] - smx
                    dy = ev.pos[1] - smy
                    runner = _race_runners.get(ridx)
                    if runner and "idx" in runner:
                        runner["maze_ox"] = sox + dx
                        runner["maze_oy"] = soy + dy

                elif _maze_drag is not None:
                    dx = ev.pos[0] - _maze_drag[0]
                    dy = ev.pos[1] - _maze_drag[1]
                    g_x = _maze_drag[2] + dx
                    g_y = _maze_drag[3] + dy

                elif _dragging_slider:
                    ratio = (ev.pos[0] - _L["slider"].x) / _L["slider"].w
                    ratio = max(0.0, min(1.0, ratio))
                    state.speed = max(1, min(MAX_SPEED, int(ratio * MAX_SPEED)))

                elif _dragging_wall is not None and not state.running and not _viz_show_tree:
                    gc = _gpos(*ev.pos)
                    if gc is not None:
                        r, c = gc
                        if (r, c) not in (state.start_cell, state.end_cell):
                            if _dragging_wall:
                                state.walls.add((r, c))
                            else:
                                state.walls.discard((r, c))

            elif ev.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                ax, ay, aw, ah = _ga()
                in_right = ax <= mx <= ax + aw and ay <= my <= ay + ah

                if not in_right:
                    continue

                factor = 1.12 if ev.y > 0 else 0.88

                if _tab == 0 and _viz_show_tree:
                    vax, vay, vaw, vah = _ga_viz_tree()
                    if vax <= mx <= vax + vaw and vay <= my <= vay + vah:
                        # Zoom the tree panel
                        old_z = _viz_tree_zoom
                        new_z = max(0.05, min(8.0, old_z * factor))
                        _viz_tree_ox = mx - (mx - _viz_tree_ox) * new_z / old_z
                        _viz_tree_oy = my - (my - _viz_tree_oy) * new_z / old_z
                        _viz_tree_zoom = new_z
                    else:
                        # Zoom the maze itself
                        old_c = g_cell
                        new_c = max(2.0, old_c * factor)
                        g_x = int(mx - (mx - g_x) * new_c / old_c)
                        g_y = int(my - (my - g_y) * new_c / old_c)
                        g_cell = max(2, min(80, int(round(new_c))))

                elif _tab == 1:
                    # 1) Check maze panels first
                    p_rects_w, _, _ = _race_panel_layout()
                    hit_maze = False
                    for i, idx in enumerate(_race_order):
                        pr = p_rects_w[i] if i < len(p_rects_w) else None
                        runner = _race_runners.get(idx)
                        if pr and runner and "idx" in runner and pr.collidepoint(mx, my):
                            if runner.get("maze_ox") is None:
                                rows_c, cols_c = state.rows, state.cols
                                bc = max(1, min(pr.w // cols_c, pr.h // rows_c))
                                mz0 = runner.get("maze_zoom", 1.0)
                                cell0 = max(1, int(bc * mz0))
                                runner["maze_ox"] = float((pr.w - cols_c * cell0) // 2)
                                runner["maze_oy"] = float((pr.h - rows_c * cell0) // 2)
                            old_mz = runner.get("maze_zoom", 1.0)
                            new_mz = max(0.25, min(8.0, old_mz * factor))
                            # Zoom anchored to mouse within panel
                            rel_x = mx - pr.x; rel_y = my - pr.y
                            runner["maze_ox"] = rel_x - (rel_x - runner["maze_ox"]) * new_mz / old_mz
                            runner["maze_oy"] = rel_y - (rel_y - runner["maze_oy"]) * new_mz / old_mz
                            runner["maze_zoom"] = new_mz
                            hit_maze = True
                            break

                    if not hit_maze:
                        # 2) Check tree panels
                        hit_tree = False
                        if _race_show_trees:
                            _, tree_rects, _ = _race_panel_layout()
                            for i, idx in enumerate(_race_order):
                                tr = tree_rects[i]
                                runner = _race_runners.get(idx)
                                if tr and runner and runner.get("tree_pos") is not None:
                                    if tr.collidepoint(mx, my):
                                        old_z = runner["tree_zoom"]
                                        new_z = max(0.05, min(8.0, old_z * factor))
                                        runner["tree_ox"] = mx - (mx - runner["tree_ox"]) * new_z / old_z
                                        runner["tree_oy"] = my - (my - runner["tree_oy"]) * new_z / old_z
                                        runner["tree_zoom"] = new_z
                                        hit_tree = True
                                        break

                        # 3) Fall back to scrolling
                        if not hit_tree:
                            max_sc = max(0, _race_content_h - (ah - _RACE_TOOLBAR_H))
                            _race_scroll = max(0, min(max_sc, _race_scroll - ev.y * 25))

            elif ev.type == pygame.KEYDOWN:
                if dd_open:
                    dd_open = False
                    continue

                if _edit:
                    if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        _apply_edit()
                    elif ev.key == pygame.K_ESCAPE:
                        _edit = None; _etext = ""
                    elif ev.key == pygame.K_BACKSPACE:
                        _etext = _etext[:-1]
                    elif ev.unicode.isdigit() and len(_etext) < 3:
                        _etext += ev.unicode
                    continue

                k = ev.key
                if k == pygame.K_s:
                    state.set_mode = None if state.set_mode == "start" else "start"
                elif k == pygame.K_e:
                    state.set_mode = None if state.set_mode == "end" else "end"
                elif k == pygame.K_SPACE:
                    if state.running:
                        state.running = False
                    else:
                        if state.finished:
                            state.clear_search()
                            _viz_show_tree = False
                            recalc_grid()
                        state.start_algorithm(ALGO_FUNCS[state.cur_alg])
                        _last_alg_name = ALG_NAMES[state.cur_alg]
                        _last_fin = False
                elif k == pygame.K_r:
                    state.clear_search()
                    _last_fin = False
                    state.walls.clear()
                    _viz_show_tree = False
                    recalc_grid()
                elif k == pygame.K_t and _tab == 0:
                    # T key toggles tree in Visualize tab
                    if state.finished and state.came_from:
                        _viz_show_tree = not _viz_show_tree
                        _viz_tree_fit  = True
                        recalc_grid()

        draw_all()
        clock.tick(60)
