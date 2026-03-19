"""
gui.py — Pygame Rendering + Main Event Loop  (Light Theme)
"""

import pygame
from config import W, H, ROWS, COLS, CELL, GX, GY, PX, PW, state
from grid import in_bounds, generate_maze
from algorithms import ALGO_FUNCS, ALG_NAMES, ALG_FULL

# ─────────────────────────────────────────────
# INIT
# ─────────────────────────────────────────────
pygame.init()
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Maze Pathfinding Visualizer")
clock  = pygame.time.Clock()

FS  = pygame.font.SysFont("Segoe UI",  13)
FM  = pygame.font.SysFont("Segoe UI",  14, bold=True)
FL  = pygame.font.SysFont("Segoe UI",  16, bold=True)
FSM = pygame.font.SysFont("Segoe UI",  11)
FV  = pygame.font.SysFont("Consolas",  13)

# ─────────────────────────────────────────────
# COLOUR PALETTE  (light theme)
# ─────────────────────────────────────────────
BG_MAIN      = (242, 244, 250)
PANEL_BG     = (255, 255, 255)
PANEL_BORDER = (208, 213, 228)
DIVIDER      = (225, 228, 238)

TEXT_DARK    = ( 22,  28,  46)
TEXT_MED     = ( 75,  85, 110)
TEXT_LIGHT   = (155, 162, 182)

# Grid
GRID_EMPTY   = (255, 255, 255)
GRID_WALL    = ( 36,  40,  60)
GRID_LINE    = (215, 218, 230)
COL_START    = ( 34, 197, 100)
COL_END      = (218,  55,  55)
COL_VISITED  = ( 90, 160, 225)
COL_FRONTIER = (155,  95, 215)
COL_PATH     = (240, 185,  20)

# Buttons — algo selector
ALGA_DEF = (230, 234, 248)
ALGA_HOV = (208, 216, 242)
ALGA_SEL = ( 50, 118, 210)
ALGA_TXT = (255, 255, 255)

# Buttons — control row
BRUN_C   = ( 38, 172,  82)
BRUN_H   = ( 30, 148,  68)
BPAUSE_C = (208,  90,  36)
BCLR_C   = (230, 234, 248)
BCLR_H   = (208, 216, 242)
BRST_C   = (205,  58,  52)
BRST_H   = (178,  44,  40)

SLIDER_BG   = (218, 222, 238)
SLIDER_FILL = ( 50, 118, 210)

COL_FOUND    = ( 28, 158,  78)
COL_NOTFOUND = (195,  48,  48)
COL_RUNNING  = (155, 125,  28)

PAD       = 14
BTN_H     = 30
SEC_H     = 22        # height of a section-header block
MAX_SPEED = 200


# ─────────────────────────────────────────────
# DRAW HELPERS
# ─────────────────────────────────────────────

def _txt_c(surf, text, font, color, cx, cy):
    s = font.render(str(text), True, color)
    surf.blit(s, s.get_rect(center=(cx, cy)))

def _txt_l(surf, text, font, color, x, cy):
    s = font.render(str(text), True, color)
    surf.blit(s, (x, cy - s.get_height() // 2))

def _txt_r(surf, text, font, color, rx, cy):
    s = font.render(str(text), True, color)
    surf.blit(s, (rx - s.get_width(), cy - s.get_height() // 2))

def _btn(surf, rect, label, font, bg, fg=TEXT_DARK, r=7):
    pygame.draw.rect(surf, bg, rect, border_radius=r)
    s = font.render(str(label), True, fg)
    surf.blit(s, s.get_rect(center=rect.center))

def _sec(surf, text, x, y, w):
    """Section header: label + divider line. Returns y of first content row."""
    s = FSM.render(text.upper(), True, TEXT_LIGHT)
    surf.blit(s, (x, y + 2))
    line_y = y + s.get_height() + 5
    pygame.draw.line(surf, DIVIDER, (x, line_y), (x + w, line_y), 1)
    return line_y + 7          # ← caller should start content here

def _grid_pos(mx, my):
    c = (mx - GX) // CELL
    r = (my - GY) // CELL
    return (r, c) if in_bounds(r, c) else None


# ─────────────────────────────────────────────
# CELL COLOUR
# ─────────────────────────────────────────────

def _cell_color(r, c, path_set):
    pos = (r, c)
    if pos == state.start_cell:  return COL_START
    if pos == state.end_cell:    return COL_END
    if pos in state.walls:       return GRID_WALL
    if pos in path_set:          return COL_PATH
    if pos in state.front_cells: return COL_FRONTIER
    if pos in state.vis_cells:   return COL_VISITED
    return GRID_EMPTY


# ─────────────────────────────────────────────
# LAYOUT  (computed once at startup)
# ─────────────────────────────────────────────
#
# Panel occupies x in [PX, W], full height [0, H].
# Content x0 = PX + PAD,  usable width pw = PW - 2*PAD.
#
# y positions below are absolute screen coords.

def _build_layout():
    L  = {}
    x0 = PX + PAD
    pw = PW - 2 * PAD
    y  = 8

    # ── ALGORITHMS section ────────────────────
    L["alg_sec_y"] = y          # section header draws here
    y += SEC_H                  # content starts after header

    col_w = (pw - 6) // 2
    alg_rects = []
    for i in range(8):
        col = i % 2
        row = i // 2
        bx  = x0 + col * (col_w + 6)
        by  = y  + row * (BTN_H + 5)
        alg_rects.append(pygame.Rect(bx, by, col_w, BTN_H))
    L["alg_rects"]  = alg_rects
    y += 4 * (BTN_H + 5) - 5   # end of last row

    # full-name label (centred, below grid)
    y += 8
    L["full_name_y"] = y + 8    # vertical centre of label
    y += 20

    # ── CONTROLS section ──────────────────────
    y += 10
    L["ctrl_sec_y"] = y
    y += SEC_H

    L["btn_run"]   = pygame.Rect(x0, y, pw, BTN_H + 4)
    y += BTN_H + 8
    L["btn_clear"] = pygame.Rect(x0, y, pw, BTN_H)
    y += BTN_H + 5
    L["btn_maze"]  = pygame.Rect(x0, y, pw, BTN_H)
    y += BTN_H + 5
    L["btn_reset"] = pygame.Rect(x0, y, pw, BTN_H)
    y += BTN_H + 10

    # ── SPEED section ─────────────────────────
    y += 6
    L["spd_sec_y"] = y
    y += SEC_H

    mini = BTN_H
    sw   = pw - 2 * (mini + 5)
    L["btn_minus"]  = pygame.Rect(x0,               y, mini, BTN_H)
    L["slider_bg"]  = pygame.Rect(x0 + mini + 5,   y, sw,   BTN_H)
    L["btn_plus"]   = pygame.Rect(x0 + mini + 5 + sw + 5, y, mini, BTN_H)
    y += BTN_H + 10

    # ── SET POINTS section ────────────────────
    y += 6
    L["set_sec_y"] = y
    y += SEC_H

    half = (pw - 6) // 2
    L["btn_set_s"] = pygame.Rect(x0,          y, half, BTN_H)
    L["btn_set_e"] = pygame.Rect(x0 + half + 6, y, pw - half - 6, BTN_H)
    y += BTN_H + 10

    # ── STATISTICS section ────────────────────
    y += 6
    L["stats_sec_y"] = y
    y += SEC_H

    L["stats_y"] = y
    y += 4 * 20 + 26    # 4 rows (20px each) + status line

    # ── LEGEND section ────────────────────────
    y += 6
    L["leg_sec_y"] = y
    y += SEC_H
    L["leg_y"] = y

    return L


_L = _build_layout()


# ─────────────────────────────────────────────
# DRAW ALL
# ─────────────────────────────────────────────

def draw_all(hover=None):
    screen.fill(BG_MAIN)

    # ── Grid ──────────────────────────────────
    path_set = set(state.path_cells)
    for r in range(ROWS):
        for c in range(COLS):
            rect  = pygame.Rect(GX + c * CELL, GY + r * CELL, CELL, CELL)
            color = _cell_color(r, c, path_set)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, GRID_LINE, rect, 1)

    # ── Panel background (LEFT side) ──────────
    pygame.draw.rect(screen, PANEL_BG, pygame.Rect(0, 0, GX - 4, H))
    pygame.draw.line(screen, PANEL_BORDER, (GX - 4, 0), (GX - 4, H), 2)

    x0 = PX + PAD
    pw = PW - 2 * PAD
    cx = PX + PW // 2         # horizontal centre of panel

    # ── Title (above grid, left side) ─────────
    grid_cx = GX + (COLS * CELL) // 2
    _txt_c(screen, "Maze Pathfinding Visualizer", FL, TEXT_DARK, grid_cx, GY // 2)

    # ── ALGORITHMS ────────────────────────────
    _sec(screen, "Algorithms", x0, _L["alg_sec_y"], pw)

    for i, rect in enumerate(_L["alg_rects"]):
        sel = (i == state.cur_alg)
        hov = (rect == hover and not sel)
        bg  = ALGA_SEL if sel else (ALGA_HOV if hov else ALGA_DEF)
        fg  = ALGA_TXT if sel else TEXT_DARK
        _btn(screen, rect, ALG_NAMES[i], FS, bg, fg)

    # selected algo full name
    full = ALG_FULL[state.cur_alg] if state.cur_alg < len(ALG_FULL) else ""
    s = FSM.render(full, True, TEXT_MED)
    screen.blit(s, s.get_rect(centerx=cx, centery=_L["full_name_y"]))

    # ── CONTROLS ──────────────────────────────
    _sec(screen, "Controls", x0, _L["ctrl_sec_y"], pw)

    run_lbl = "⏸  Pause" if state.running else "▶   Run"
    run_bg  = BPAUSE_C if state.running else (BRUN_H if _L["btn_run"] == hover else BRUN_C)
    _btn(screen, _L["btn_run"],   run_lbl,     FM, run_bg,                                 (255,255,255))
    _btn(screen, _L["btn_clear"], "Clear Path", FS, BCLR_H if _L["btn_clear"]==hover else BCLR_C)
    _btn(screen, _L["btn_maze"],  "Gen Maze",   FS, BCLR_H if _L["btn_maze"] ==hover else BCLR_C)
    _btn(screen, _L["btn_reset"], "Reset All",  FS, BRST_H if _L["btn_reset"]==hover else BRST_C, (255,255,255))

    # ── SPEED ─────────────────────────────────
    _sec(screen, f"Speed — {state.speed} steps/frame", x0, _L["spd_sec_y"], pw)

    _btn(screen, _L["btn_minus"], "−", FM, ALGA_HOV)
    _btn(screen, _L["btn_plus"],  "+", FM, ALGA_HOV)

    sbg = _L["slider_bg"]
    pygame.draw.rect(screen, SLIDER_BG, sbg, border_radius=5)
    fw = max(6, int(sbg.width * state.speed / MAX_SPEED))
    pygame.draw.rect(screen, SLIDER_FILL,
                     pygame.Rect(sbg.x, sbg.y, fw, sbg.height), border_radius=5)

    # ── SET POINTS ────────────────────────────
    _sec(screen, "Set Points", x0, _L["set_sec_y"], pw)

    s_act = state.set_mode == "start"
    e_act = state.set_mode == "end"
    _btn(screen, _L["btn_set_s"], "Set Start  [S]", FS,
         ALGA_SEL if s_act else (ALGA_HOV if _L["btn_set_s"]==hover else ALGA_DEF),
         ALGA_TXT if s_act else TEXT_DARK)
    _btn(screen, _L["btn_set_e"], "Set End   [E]", FS,
         ALGA_SEL if e_act else (ALGA_HOV if _L["btn_set_e"]==hover else ALGA_DEF),
         ALGA_TXT if e_act else TEXT_DARK)

    # ── STATISTICS ────────────────────────────
    _sec(screen, "Statistics", x0, _L["stats_sec_y"], pw)

    st   = state.stats
    ly   = _L["stats_y"]
    rx   = x0 + pw          # right edge for right-aligned values
    rows = [
        ("Nodes visited", str(st["nodes"])),
        ("Path length",   str(st["path"])),
        ("Cost",          str(st["cost"])),
        ("Time",          f"{st['time']*1000:.1f} ms"),
    ]
    for label, val in rows:
        _txt_l(screen, label + ":", FS, TEXT_MED,  x0, ly + 10)
        _txt_r(screen, val,         FV, TEXT_DARK,  rx, ly + 10)
        ly += 20

    # status badge
    found = st["found"]
    if state.running:
        stxt, scol = "Running...", COL_RUNNING
    elif found is True:
        stxt, scol = "Found  ✓",   COL_FOUND
    elif found is False:
        stxt, scol = "Not Found  ✗", COL_NOTFOUND
    else:
        stxt, scol = "", TEXT_LIGHT

    if stxt:
        ss = FM.render(stxt, True, scol)
        screen.blit(ss, ss.get_rect(centerx=cx, centery=ly + 12))

    # ── LEGEND ────────────────────────────────
    _sec(screen, "Legend", x0, _L["leg_sec_y"], pw)

    items = [
        (COL_START,    "Start"),
        (COL_END,      "End"),
        (COL_VISITED,  "Visited"),
        (COL_FRONTIER, "Frontier"),
        (COL_PATH,     "Path"),
        (GRID_WALL,    "Wall"),
    ]
    lx, lgy = x0, _L["leg_y"]
    for color, label in items:
        pygame.draw.rect(screen, color, pygame.Rect(lx, lgy, 13, 13), border_radius=3)
        ls = FSM.render(label, True, TEXT_MED)
        screen.blit(ls, (lx + 16, lgy + 1))
        lx += 16 + ls.get_width() + 12
        if lx + 60 > PX + PW - PAD:
            lx   = x0
            lgy += 18

    pygame.display.flip()


# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────

def run():
    dragging_wall = None    # True = add walls, False = erase

    while True:
        # ── Advance algorithm ──────────────────
        if state.running and state.alg_gen is not None and not state.finished:
            for _ in range(state.speed):
                try:
                    vis, front = next(state.alg_gen)
                    state.vis_cells   = vis
                    state.front_cells = front
                except StopIteration:
                    state.running = False
                    break
                except Exception as exc:
                    print(f"[Algorithm error] {exc}")
                    state.running = False
                    break

        # ── Hover ─────────────────────────────
        mx, my = pygame.mouse.get_pos()
        hover = None
        for key in ("btn_run", "btn_clear", "btn_maze", "btn_reset",
                    "btn_minus", "btn_plus", "btn_set_s", "btn_set_e"):
            if _L[key].collidepoint(mx, my):
                hover = _L[key]
                break
        if hover is None:
            for r in _L["alg_rects"]:
                if r.collidepoint(mx, my):
                    hover = r
                    break

        # ── Events ────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            elif event.type == pygame.MOUSEBUTTONDOWN:
                ex, ey  = event.pos
                btn_btn = event.button

                if _L["btn_run"].collidepoint(ex, ey):
                    if state.running:
                        state.running = False          # pause
                    else:
                        if state.finished:
                            state.clear_search()
                        state.start_algorithm(ALGO_FUNCS[state.cur_alg])

                elif _L["btn_clear"].collidepoint(ex, ey):
                    state.clear_search()

                elif _L["btn_maze"].collidepoint(ex, ey):
                    state.clear_search()
                    generate_maze()

                elif _L["btn_reset"].collidepoint(ex, ey):
                    state.clear_search()
                    state.walls.clear()

                elif _L["btn_minus"].collidepoint(ex, ey):
                    state.speed = max(1, state.speed - 5)

                elif _L["btn_plus"].collidepoint(ex, ey):
                    state.speed = min(MAX_SPEED, state.speed + 5)

                elif _L["btn_set_s"].collidepoint(ex, ey):
                    state.set_mode = None if state.set_mode == "start" else "start"

                elif _L["btn_set_e"].collidepoint(ex, ey):
                    state.set_mode = None if state.set_mode == "end" else "end"

                else:
                    # Algo selector buttons
                    hit_algo = False
                    for i, rect in enumerate(_L["alg_rects"]):
                        if rect.collidepoint(ex, ey):
                            if state.running:           # stop current run first
                                state.clear_search()
                            state.cur_alg = i
                            hit_algo = True
                            break

                    if not hit_algo:
                        # Grid interaction
                        gc = _grid_pos(ex, ey)
                        if gc is not None:
                            r, c = gc
                            if state.set_mode == "start":
                                state.start_cell = (r, c)
                                state.set_mode   = None
                            elif state.set_mode == "end":
                                state.end_cell = (r, c)
                                state.set_mode = None
                            elif btn_btn == 1:
                                if (r, c) not in (state.start_cell, state.end_cell):
                                    state.walls.add((r, c))
                                dragging_wall = True
                            elif btn_btn == 3:
                                state.walls.discard((r, c))
                                dragging_wall = False

            elif event.type == pygame.MOUSEBUTTONUP:
                dragging_wall = None

            elif event.type == pygame.MOUSEMOTION:
                if dragging_wall is not None:
                    gc = _grid_pos(*event.pos)
                    if gc is not None:
                        r, c = gc
                        if (r, c) not in (state.start_cell, state.end_cell):
                            if dragging_wall:
                                state.walls.add((r, c))
                            else:
                                state.walls.discard((r, c))

            elif event.type == pygame.KEYDOWN:
                k = event.key
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
                        state.start_algorithm(ALGO_FUNCS[state.cur_alg])
                elif k == pygame.K_r:
                    state.clear_search()
                    state.walls.clear()

        draw_all(hover)
        clock.tick(60)
