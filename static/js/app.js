/* ═══════════════════════════════════════════════════════════════
   Maze Pathfinding Visualizer — Frontend
   ═══════════════════════════════════════════════════════════════ */

// ── Constants ────────────────────────────────────────────────
const CELL_C = [
  '#FFFFFF',   // 0 empty
  '#1C1C1E',   // 1 wall
  '#34C759',   // 2 start
  '#FF3B30',   // 3 end
  '#007AFF',   // 4 visited
  '#5856D6',   // 5 frontier
  '#FF9500',   // 6 path
  '#FFD60A',   // 7 checkpoint
  '#1B6CA8',   // 8 deep water  (cost ×10)
  '#8B5E3C',   // 9 swamp       (cost ×5)
  '#8BC34A',   // 10 grass      (cost ×2)
];
const BAR_PAL = [
  '#007AFF','#34C759','#FF9500','#FF3B30',
  '#5856D6','#AF52DE','#00C7BE','#FFCC00',
];
const NODE_GAP = 38, LEVEL_GAP = 80;

// ── State ────────────────────────────────────────────────────
let tab = 'visualize';
let viz = null;        // latest /api/state response
let race = null;       // latest /api/race response
let treeData = null;   // latest /api/tree response

// Grid interaction
let mDown = false, mBtn = 0;
let gInfo = { rows:0, cols:0, cell:0, ox:0, oy:0 };

// Tree pan/zoom
let tZoom = 1, tOx = 0, tOy = 0, tDrag = null, tFit = true;

// Dropdown
let ddOpen = false;

// Race panel canvases cache
let racePanelOrder = [];

// Grid pan/zoom
let gZoom = 1, gOffX = 0, gOffY = 0, gPanDrag = null;
let lastVizRows = 0, lastVizCols = 0;

// Start/end drag
let dragType = null, dragCell = null, lastDragSent = null;

// Path animation only
let prevGrid = null;
const animCells = new Map(); // key "r,c" → {startTime, duration}  (path cells only)

// ── DOM ──────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const gridCanvas = $('grid-canvas');
const gridCtx    = gridCanvas.getContext('2d');
const treeCanvas = $('tree-canvas');
const treeCtx    = treeCanvas.getContext('2d');

// ── Canvas HiDPI ─────────────────────────────────────────────
function fitCanvas(canvas, parent) {
  const dpr = devicePixelRatio || 1;
  const w = parent.clientWidth, h = parent.clientHeight;
  canvas.width  = w * dpr;
  canvas.height = h * dpr;
  canvas.style.width  = w + 'px';
  canvas.style.height = h + 'px';
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return ctx;
}

// ── API ──────────────────────────────────────────────────────
async function act(data) {
  try {
    await fetch('/api/action', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data),
    });
  } catch(_) {}
}

// ── Tab switching ────────────────────────────────────────────
function switchTab(t) {
  tab = t;
  document.querySelectorAll('.tab').forEach(b =>
    b.classList.toggle('active', b.dataset.tab === t));
  $('ribbon-viz').classList.toggle('hidden', t !== 'visualize');
  $('ribbon-race').classList.toggle('hidden', t !== 'race');
  $('content-viz').classList.toggle('hidden', t !== 'visualize');
  $('content-race').classList.toggle('hidden', t !== 'race');
  if (t === 'visualize') onResize();
}
document.querySelectorAll('.tab').forEach(b =>
  b.addEventListener('click', () => switchTab(b.dataset.tab)));

// ── Dropdown ─────────────────────────────────────────────────
function buildAlgoList() {
  const list = $('algo-list');
  list.innerHTML = '';
  ALG_NAMES.forEach((name, i) => {
    const d = document.createElement('div');
    d.className = 'dd-item';
    d.innerHTML = `<span>${name}</span>`;
    d.addEventListener('click', () => {
      act({action:'select_algo', idx:i});
      ddOpen = false;
      list.classList.add('hidden');
    });
    list.appendChild(d);
  });
}
buildAlgoList();

$('algo-btn').addEventListener('click', () => {
  ddOpen = !ddOpen;
  $('algo-list').classList.toggle('hidden', !ddOpen);
});
document.addEventListener('click', e => {
  if (ddOpen && !$('algo-dd').contains(e.target)) {
    ddOpen = false;
    $('algo-list').classList.add('hidden');
  }
});

// ── Button handlers ──────────────────────────────────────────
$('btn-run').addEventListener('click',      () => act({action:'run'}));
$('btn-step-back').addEventListener('click', () => act({action:'step_back'}));
$('btn-step-fwd').addEventListener('click',  () => act({action:'step'}));
$('btn-cancel').addEventListener('click',    () => act({action:'cancel_algo'}));
$('btn-clear').addEventListener('click',     () => act({action:'clear'}));
$('btn-maze').addEventListener('click',          () => act({action:'maze'}));
$('btn-weighted-maze').addEventListener('click', () => act({action:'weighted_maze'}));
$('btn-reset').addEventListener('click',         () => act({action:'reset'}));
$('btn-tree').addEventListener('click',      () => { act({action:'toggle_tree'}); tFit = true; });

// Checkpoint / Options panel
let cpPlaceMode = false;
$('btn-cp-toggle').addEventListener('click', () => {
  if (viz?.checkpoint) {
    act({action:'remove_checkpoint'});
  } else {
    cpPlaceMode = !cpPlaceMode;
    if (cpPlaceMode) setTerrainBrush(0);  // deactivate terrain when entering cp mode
    $('btn-cp-toggle').classList.toggle('btn-selected', cpPlaceMode);
  }
});

// Terrain brushes
let terrainBrush = 0;
function setTerrainBrush(type) {
  terrainBrush = (terrainBrush === type) ? 0 : type;
  if (terrainBrush) cpPlaceMode = false;  // deactivate cp mode
  document.querySelectorAll('.btn-terrain').forEach(b => {
    b.classList.toggle('btn-selected', +b.dataset.terrain === terrainBrush);
  });
}
document.querySelectorAll('.btn-terrain').forEach(b => {
  b.addEventListener('click', () => setTerrainBrush(+b.dataset.terrain));
});

$('btn-spd-down').addEventListener('click', () => {
  const v = Math.max(1, (viz?.speed || 20) - 5);
  $('speed-val').textContent = v; $('speed-slider').value = v;
  act({action:'speed', value:v});
});
$('btn-spd-up').addEventListener('click', () => {
  const v = Math.min(200, (viz?.speed || 20) + 5);
  $('speed-val').textContent = v; $('speed-slider').value = v;
  act({action:'speed', value:v});
});
$('speed-slider').addEventListener('input', e => {
  $('speed-val').textContent = e.target.value;
  act({action:'speed', value: +e.target.value});
});

// Race speed (same state.speed on backend)
$('race-btn-spd-dn').addEventListener('click', () => {
  const v = Math.max(1, (viz?.speed || 20) - 5);
  $('race-speed-val').textContent = v; $('race-speed-slider').value = v;
  act({action:'speed', value:v});
});
$('race-btn-spd-up').addEventListener('click', () => {
  const v = Math.min(200, (viz?.speed || 20) + 5);
  $('race-speed-val').textContent = v; $('race-speed-slider').value = v;
  act({action:'speed', value:v});
});
$('race-speed-slider').addEventListener('input', e => {
  $('race-speed-val').textContent = e.target.value;
  act({action:'speed', value: +e.target.value});
});

// Race step / cancel
$('race-btn-step-back').addEventListener('click', () => act({action:'race_step_back'}));
$('race-btn-step-fwd').addEventListener('click',  () => act({action:'race_step'}));
$('race-btn-cancel').addEventListener('click',    () => act({action:'race_cancel'}));

$('btn-row-dn').addEventListener('click', () => act({action:'change_grid', dr:-1, dc:0}));
$('btn-row-up').addEventListener('click', () => act({action:'change_grid', dr:1,  dc:0}));
$('btn-col-dn').addEventListener('click', () => act({action:'change_grid', dr:0,  dc:-1}));
$('btn-col-up').addEventListener('click', () => act({action:'change_grid', dr:0,  dc:1}));

['inp-rows','inp-cols'].forEach(id => {
  $(id).addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      const rows = +$('inp-rows').value || viz?.rows || 28;
      const cols = +$('inp-cols').value || viz?.cols || 40;
      act({action:'set_grid', rows, cols});
      e.target.blur();
    }
  });
});

// Keyboard shortcuts
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT') return;
  if (e.key === ' ') { e.preventDefault(); act({action:'run'}); }
  if (e.key === '.') act({action:'step'});
  if (e.key === ',') act({action:'step_back'});
  if (e.key === 'r') act({action:'reset'});
  if (e.key === 'Escape') act({action:'cancel_algo'});
  if (e.key === 't' && tab === 'visualize') { act({action:'toggle_tree'}); tFit = true; }
});


// ═══════════════════════════════════════════════════════════════
// GRID CANVAS
// ═══════════════════════════════════════════════════════════════
function updateAnimations(newGrid, rows, cols) {
  if (!prevGrid || prevGrid.length !== newGrid.length) {
    prevGrid = newGrid.slice();
    return;
  }
  const now = performance.now();
  // Build path-index lookup for sequential reveal (start→end)
  const pathIdx = new Map();
  (viz?.path_cells || []).forEach(([r, c], i) => pathIdx.set(`${r},${c}`, i));

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const i = r * cols + c;
      const oldT = prevGrid[i], newT = newGrid[i];
      if (oldT === newT) continue;
      const key = `${r},${c}`;
      if (newT === 6) {
        // Sequential path reveal start→end
        const delay = (pathIdx.get(key) ?? 0) * 18;
        animCells.set(key, { startTime: now + delay, duration: 320 });
      } else {
        animCells.delete(key);
      }
    }
  }
  prevGrid = newGrid.slice();
}

function drawGrid() {
  if (!viz) return;
  const { rows, cols, grid } = viz;
  const cw = gridCanvas.clientWidth, ch = gridCanvas.clientHeight;
  const baseCellRaw = Math.min(cw / cols, ch / rows);
  const cell = Math.max(1, Math.floor(baseCellRaw * gZoom));
  const gw = cols * cell, gh = rows * cell;
  const ox = Math.floor((cw - gw) / 2) + gOffX, oy = Math.floor((ch - gh) / 2) + gOffY;
  gInfo = { rows, cols, cell, ox, oy };

  const ctx = gridCtx;
  ctx.fillStyle = '#F2F2F7';
  ctx.fillRect(0, 0, cw, ch);

  const now = performance.now();
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      let t = grid[r * cols + c];
      // Drag overlay
      if (dragType === 'start') {
        if (t === 2) t = 0;
        if (dragCell && r === dragCell.r && c === dragCell.c) t = 2;
      } else if (dragType === 'end') {
        if (t === 3) t = 0;
        if (dragCell && r === dragCell.r && c === dragCell.c) t = 3;
      } else if (dragType === 'checkpoint') {
        if (t === 7) t = 0;
        if (dragCell && r === dragCell.r && c === dragCell.c) t = 7;
      }

      const x = ox + c * cell, y = oy + r * cell;
      const key = `${r},${c}`;
      const anim = t === 6 ? animCells.get(key) : null;

      if (anim && cell >= 4 && now >= anim.startTime) {
        // Path cell animating: back ease-out (grow → slight overshoot → settle)
        const elapsed  = now - anim.startTime;
        const progress = Math.min(elapsed / anim.duration, 1);
        if (progress >= 1) { animCells.delete(key); }
        const c1 = 1.70158, c3 = c1 + 1;
        const scale = Math.max(0, 1 + c3 * Math.pow(progress - 1, 3) + c1 * Math.pow(progress - 1, 2));

        ctx.fillStyle = CELL_C[4]; // visited blue background
        ctx.fillRect(x, y, cell, cell);

        if (scale > 0) {
          const s  = cell * scale;
          const bx = x + (cell - s) / 2, by = y + (cell - s) / 2;
          ctx.save();
          ctx.beginPath(); ctx.rect(x, y, cell, cell); ctx.clip();
          ctx.fillStyle = CELL_C[6];
          const rad = s * 0.22;
          ctx.beginPath();
          ctx.roundRect(bx, by, s, s, rad);
          ctx.fill();
          ctx.restore();
        }
      } else {
        // Pending path animation → show visited blue while waiting
        ctx.fillStyle = (anim) ? CELL_C[4] : (CELL_C[t] || CELL_C[0]);
        ctx.fillRect(x, y, cell, cell);
      }

      if (cell >= 6) {
        ctx.strokeStyle = '#E5E5EA';
        ctx.lineWidth = .5;
        ctx.strokeRect(x + .25, y + .25, cell - .5, cell - .5);
      }
      // Glow ring on dragged marker
      if (dragCell && r === dragCell.r && c === dragCell.c && dragType) {
        ctx.strokeStyle = 'rgba(255,255,255,0.75)';
        ctx.lineWidth = Math.max(1.5, cell * 0.12);
        ctx.strokeRect(x + 1.5, y + 1.5, cell - 3, cell - 3);
      }

      // Cell coordinates when tree panel is open
      if (viz.show_tree && cell >= 12) {
        const fontSize = Math.max(6, Math.floor(cell * 0.28));
        ctx.font = `${fontSize}px var(--font, sans-serif)`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const isLight = (t === 0 || t === 10);
        ctx.fillStyle = isLight ? 'rgba(0,0,0,0.45)' : 'rgba(255,255,255,0.55)';
        ctx.fillText(`${r},${c}`, x + cell / 2, y + cell / 2);
      }
    }
  }
}

// Grid mouse
function gridPos(e) {
  const rect = gridCanvas.getBoundingClientRect();
  const mx = e.clientX - rect.left, my = e.clientY - rect.top;
  const { rows, cols, cell, ox, oy } = gInfo;
  const c = Math.floor((mx - ox) / cell), r = Math.floor((my - oy) / cell);
  return (r >= 0 && r < rows && c >= 0 && c < cols) ? { r, c } : null;
}

gridCanvas.addEventListener('mousedown', e => {
  if (e.button === 1) {
    gPanDrag = { sx: e.clientX, sy: e.clientY, ox: gOffX, oy: gOffY };
    e.preventDefault();
    return;
  }
  const p = gridPos(e);
  // Terrain paint mode — left click paints, right click erases
  if (terrainBrush > 0 && p && !viz?.running) {
    mDown = true; mBtn = e.button;
    act({action:'set_terrain', r:p.r, c:p.c, terrain: e.button === 2 ? 0 : terrainBrush});
    return;
  }
  // Drag start / end / checkpoint — takes priority
  if (e.button === 0 && p && !viz?.running) {
    const t = viz?.grid?.[p.r * (viz?.cols ?? 0) + p.c];
    if (t === 2) {
      dragType = 'start'; dragCell = { ...p }; lastDragSent = { ...p };
      document.body.style.cursor = 'grabbing'; return;
    }
    if (t === 3) {
      dragType = 'end'; dragCell = { ...p }; lastDragSent = { ...p };
      document.body.style.cursor = 'grabbing'; return;
    }
    if (t === 7) {
      dragType = 'checkpoint'; dragCell = { ...p }; lastDragSent = { ...p };
      document.body.style.cursor = 'grabbing'; return;
    }
  }
  // Shift+click or cpPlaceMode: place or remove checkpoint
  if (e.button === 0 && (e.shiftKey || cpPlaceMode) && p && !viz?.running) {
    const t = viz?.grid?.[p.r * (viz?.cols ?? 0) + p.c];
    if (t === 7) { act({action:'remove_checkpoint'}); }
    else if (t !== 2 && t !== 3) { act({action:'set_checkpoint', r:p.r, c:p.c}); }
    if (cpPlaceMode) { cpPlaceMode = false; $('btn-cp-toggle').classList.remove('btn-selected'); }
    return;
  }
  if (viz?.show_tree) {
    if (e.button === 0) gPanDrag = { sx: e.clientX, sy: e.clientY, ox: gOffX, oy: gOffY };
    return;
  }
  // Outside grid area → pan
  if (!p) {
    if (e.button === 0) gPanDrag = { sx: e.clientX, sy: e.clientY, ox: gOffX, oy: gOffY };
    return;
  }
  mDown = true; mBtn = e.button;
  act({action:'grid_cell', r:p.r, c:p.c, remove: e.button === 2});
});
gridCanvas.addEventListener('mousemove', e => {
  // Update hover cursor (grab over start/end cells)
  if (!mDown && !dragType && !viz?.show_tree) {
    const p = gridPos(e);
    if (p && viz?.grid && !viz.running) {
      const t = viz.grid[p.r * viz.cols + p.c];
      gridCanvas.style.cursor = (t === 2 || t === 3 || t === 7) ? 'grab' : '';
    } else {
      gridCanvas.style.cursor = '';
    }
  }
  if (!mDown) return;
  const p = gridPos(e);
  if (!p) return;
  if (terrainBrush > 0) {
    act({action:'set_terrain', r:p.r, c:p.c, terrain: mBtn === 2 ? 0 : terrainBrush});
  } else {
    act({action:'grid_cell', r:p.r, c:p.c, remove: mBtn === 2});
  }
});
document.addEventListener('mouseup', () => {
  dragType = null; dragCell = null; lastDragSent = null;
  document.body.style.cursor = '';
  mDown = false; gPanDrag = null; tDrag = null;
});
gridCanvas.addEventListener('contextmenu', e => e.preventDefault());

gridCanvas.addEventListener('wheel', e => {
  if (tab !== 'visualize') return;
  e.preventDefault();
  const f = e.deltaY < 0 ? 1.12 : 0.88;
  const rect = gridCanvas.getBoundingClientRect();
  const mx = e.clientX - rect.left, my = e.clientY - rect.top;
  const { cell: oldCell, ox: oldOx, oy: oldOy, cols, rows } = gInfo;
  if (!oldCell || !cols) return;
  const cw = gridCanvas.clientWidth, ch = gridCanvas.clientHeight;
  const newZoom = Math.max(0.3, Math.min(20, gZoom * f));
  const baseCellRaw = Math.min(cw / cols, ch / rows);
  const newCell = Math.max(1, Math.floor(baseCellRaw * newZoom));
  const newCenterOx = Math.floor((cw - cols * newCell) / 2);
  const newCenterOy = Math.floor((ch - rows * newCell) / 2);
  gOffX = Math.round(mx - (mx - oldOx) * newCell / oldCell) - newCenterOx;
  gOffY = Math.round(my - (my - oldOy) * newCell / oldCell) - newCenterOy;
  gZoom = newZoom;
}, { passive: false });

gridCanvas.addEventListener('dblclick', () => { gZoom = 1; gOffX = 0; gOffY = 0; });


// ═══════════════════════════════════════════════════════════════
// TREE CANVAS
// ═══════════════════════════════════════════════════════════════
function autoFitTree(data, w, h) {
  if (!data || !data.bounds) return;
  const [bw, bh] = data.bounds;
  if (bw <= 0 || bh <= 0) return;
  const pad = 28;
  const tw = bw * NODE_GAP, th = bh * LEVEL_GAP;
  tZoom = Math.min((w - pad*2) / Math.max(tw,1),
                   (h - pad*2) / Math.max(th,1), 2.5);
  tZoom = Math.max(tZoom, 0.08);
  tOx = (w - tw * tZoom) / 2;
  tOy = pad;
}

function drawTree() {
  if (!treeData || !treeData.positions.length) return;
  const canvas = treeCanvas;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  const ctx = treeCtx;

  if (tFit) { autoFitTree(treeData, w, h); tFit = false; }

  ctx.fillStyle = '#F8F9FC';
  ctx.fillRect(0, 0, w, h);

  const nodes = {};
  for (const p of treeData.positions) {
    const k = p.node.join(',');
    nodes[k] = {
      x: tOx + p.x * NODE_GAP * tZoom,
      y: tOy + p.y * LEVEL_GAP * tZoom,
      ip: p.ip, node: p.node,
    };
  }
  const startK = treeData.start.join(',');
  const endK   = treeData.end.join(',');
  const baseR  = Math.max(12, 18 * tZoom);
  const specR  = Math.max(16, 22 * tZoom);

  // Edges
  for (const e of treeData.edges) {
    const a = nodes[e.from.join(',')], b = nodes[e.to.join(',')];
    if (!a || !b) continue;
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
    ctx.strokeStyle = e.ip ? '#FF9500' : '#D2DEF0';
    ctx.lineWidth = e.ip ? Math.max(2, 3*tZoom) : Math.max(1, 1.2*tZoom);
    ctx.stroke();
  }

  // Nodes
  for (const [k, n] of Object.entries(nodes)) {
    const isS = k === startK, isE = k === endK;
    const r = (isS || isE) ? specR : baseR;
    ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, Math.PI*2);
    if (isS) ctx.fillStyle = '#34C759';
    else if (isE) ctx.fillStyle = '#FF3B30';
    else if (n.ip) ctx.fillStyle = '#FF9500';
    else ctx.fillStyle = '#AFC8F0';
    ctx.fill();
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 1; ctx.stroke();

    // Label
    const sz = Math.max(10, 13 * tZoom);
    ctx.font = `600 ${sz}px -apple-system, sans-serif`;
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillStyle = (n.ip || isS || isE) ? '#fff' : '#28284A';
    ctx.fillText(n.node.join(','), n.x, n.y);
  }

  // Info header
  $('tree-info').textContent =
    `Tree: ${treeData.algo}  •  ${treeData.shown}` +
    (treeData.shown < treeData.total ? ` / ${treeData.total}` : '') +
    ' nodes';
  $('tree-hint').textContent = `Scroll=zoom  Drag=pan  (${tZoom.toFixed(2)}x)`;
}

// Tree pan/zoom
treeCanvas.addEventListener('wheel', e => {
  e.preventDefault();
  const f = e.deltaY < 0 ? 1.12 : 0.88;
  const rect = treeCanvas.getBoundingClientRect();
  const mx = e.clientX - rect.left, my = e.clientY - rect.top;
  const nz = Math.max(0.05, Math.min(8, tZoom * f));
  tOx = mx - (mx - tOx) * nz / tZoom;
  tOy = my - (my - tOy) * nz / tZoom;
  tZoom = nz;
}, {passive: false});

treeCanvas.addEventListener('mousedown', e => {
  tDrag = { sx: e.clientX, sy: e.clientY, ox: tOx, oy: tOy };
});
document.addEventListener('mousemove', e => {
  // Drag start/end marker
  if (dragType) {
    const p = gridPos(e);
    if (p && (p.r !== lastDragSent?.r || p.c !== lastDragSent?.c)) {
      dragCell = { ...p };
      lastDragSent = { ...p };
      const actionMap = { start:'set_start', end:'set_end', checkpoint:'set_checkpoint' };
      act({ action: actionMap[dragType], r: p.r, c: p.c });
    }
  }
  if (gPanDrag) {
    gOffX = gPanDrag.ox + e.clientX - gPanDrag.sx;
    gOffY = gPanDrag.oy + e.clientY - gPanDrag.sy;
  }
  if (tDrag) {
    tOx = tDrag.ox + e.clientX - tDrag.sx;
    tOy = tDrag.oy + e.clientY - tDrag.sy;
  }
});


// ═══════════════════════════════════════════════════════════════
// UI UPDATE — VISUALIZE
// ═══════════════════════════════════════════════════════════════
function updateVizUI() {
  if (!viz) return;

  // Run button state
  const rb = $('btn-run');
  const isActive = viz.running || viz.paused;
  if (viz.running) {
    rb.textContent = 'Pause'; rb.className = 'btn btn-run pausing';
  } else if (viz.paused && !viz.finished) {
    rb.textContent = 'Continue'; rb.className = 'btn btn-run btn-continue';
  } else {
    rb.textContent = 'Run'; rb.className = 'btn btn-run';
  }
  $('btn-step-back').disabled = (viz.step_ptr ?? -1) < 1 || viz.finished;
  $('btn-step-fwd').disabled  = viz.running || viz.finished || viz.maze_running;
  $('btn-cancel').classList.toggle('hidden', !isActive && !viz.finished);

  // Maze button
  $('btn-maze').textContent = viz.maze_running ? 'Generating…' : 'Generate Maze';
  $('btn-maze').disabled = !!viz.maze_running;

  // Options panel — checkpoint toggle button
  const hasCp = !!viz.checkpoint;
  $('cp-label').textContent = hasCp ? 'Cancel Checkpoint' : 'Checkpoint';
  $('btn-cp-toggle').style.cssText = hasCp
    ? 'background:#FFF3CD;border-color:#FFD60A;color:#7A5F00'
    : '';
  if (hasCp) {
    $('btn-cp-toggle').classList.remove('btn-selected');
    cpPlaceMode = false;
  } else {
    $('btn-cp-toggle').classList.toggle('btn-selected', cpPlaceMode);
  }

  // Stats
  $('st-nodes').textContent = viz.stats.nodes;
  $('st-path').textContent  = viz.stats.path;
  $('st-cost').textContent  = viz.stats.cost;
  $('st-time').textContent  = (viz.stats.time * 1000).toFixed(1) + ' ms';

  const st = $('st-status');
  if (viz.running)               { st.textContent = 'Running...'; st.style.color = '#FF9500'; }
  else if (viz.stats.found===true)  { st.textContent = 'Path Found'; st.style.color = '#34C759'; }
  else if (viz.stats.found===false) { st.textContent = 'No Path';    st.style.color = '#FF3B30'; }
  else st.textContent = '';

  // Speed (sync both ribbons)
  $('speed-val').textContent = viz.speed;
  $('speed-slider').value = viz.speed;
  $('race-speed-val').textContent = viz.speed;
  $('race-speed-slider').value = viz.speed;

  // Grid size
  if (document.activeElement !== $('inp-rows')) $('inp-rows').value = viz.rows;
  if (document.activeElement !== $('inp-cols')) $('inp-cols').value = viz.cols;

  // Algo
  $('algo-name').textContent = ALG_NAMES[viz.cur_alg];

  // Dropdown selected indicator
  document.querySelectorAll('.dd-item').forEach((d, i) => {
    d.classList.toggle('selected', i === viz.cur_alg);
    if (i === viz.cur_alg && !d.querySelector('.check'))
      d.innerHTML += '<span class="check"></span>';
    else if (i !== viz.cur_alg) {
      const ck = d.querySelector('.check');
      if (ck) ck.remove();
    }
  });

  // Tree button
  const tb = $('btn-tree');
  if (viz.has_tree) {
    tb.classList.remove('hidden');
    tb.textContent = viz.show_tree ? 'Hide Tree' : 'Show Tree';
    tb.classList.toggle('active-tree', viz.show_tree);
  } else {
    tb.classList.add('hidden');
  }

  // Split view
  $('grid-area').classList.toggle('split', !!viz.show_tree);
  $('tree-area').classList.toggle('hidden', !viz.show_tree);

  // Move legend: grid-area when normal, tree-area when tree is open
  const legend = document.querySelector('.grid-legend');
  if (legend) {
    const target = viz.show_tree ? $('tree-area') : $('grid-area');
    if (legend.parentElement !== target) target.appendChild(legend);
  }

  // Pan cursor when tree is shown (wall drawing disabled)
  gridCanvas.classList.toggle('pan-mode', !!viz.show_tree);
}


// ═══════════════════════════════════════════════════════════════
// RACE
// ═══════════════════════════════════════════════════════════════
function buildRaceToggles() {
  const cont = $('race-algos');
  cont.innerHTML = '';
  ALG_NAMES.forEach((name, i) => {
    const b = document.createElement('button');
    b.className = 'race-toggle';
    b.dataset.idx = i;
    const col = BAR_PAL[i % BAR_PAL.length];
    b.innerHTML = `<span class="color-bar" style="background:${col}"></span>${name}`;
    b.addEventListener('click', () => act({action:'race_toggle', idx:i}));
    cont.appendChild(b);
  });
}
buildRaceToggles();

$('btn-race').addEventListener('click', () => {
  if (!race) return;
  act({action:'race_start'});
});

function updateRaceUI() {
  if (!race) return;

  // Toggle buttons
  const sel = new Set(race.order);
  document.querySelectorAll('.race-toggle').forEach(b => {
    const i = +b.dataset.idx;
    const col = BAR_PAL[i % BAR_PAL.length];
    if (sel.has(i)) {
      b.classList.add('selected');
      b.style.background = col;
    } else {
      b.classList.remove('selected');
      b.style.background = '';
    }
  });

  // Race button (mirrors Visualize Run button)
  const rb = $('btn-race');
  if (race.running) {
    rb.textContent = 'Pause'; rb.className = 'btn btn-run pausing'; rb.disabled = false;
  } else if (race.paused && !race.done) {
    rb.textContent = 'Continue'; rb.className = 'btn btn-run btn-continue'; rb.disabled = false;
  } else if (race.order.length >= 2) {
    rb.textContent = 'Race'; rb.className = 'btn btn-run'; rb.disabled = false;
  } else {
    rb.textContent = 'Race'; rb.className = 'btn btn-run'; rb.disabled = true;
  }
  const raceActive = race.running || (race.paused && !race.done);
  $('race-btn-step-back').disabled = (race.step_ptr ?? -1) < 1 || race.done || race.running;
  $('race-btn-step-fwd').disabled  = race.running || race.done;
  $('race-btn-cancel').classList.toggle('hidden', !raceActive && !race.done);

  // Panels
  buildRacePanels();

  // Charts
  if (race.results) {
    $('race-charts').classList.remove('hidden');
    drawChart($('chart-nodes'), race.results, 'nodes', 'Nodes Visited');
    drawChart($('chart-path'),  race.results, 'path',  'Path Length');
    drawChart($('chart-cost'),  race.results, 'cost',  'Cost');
    drawChart($('chart-time'),  race.results, 'time',  'Time (ms)');
  } else {
    $('race-charts').classList.add('hidden');
  }
}

function buildRacePanels() {
  const cont = $('race-panels');
  const order = race.order;
  const n = order.length;

  if (n === 0) { cont.innerHTML = ''; racePanelOrder = []; return; }

  // Dynamic grid: fill the screen
  const cols = n <= 2 ? n : n <= 4 ? 2 : n <= 6 ? 3 : 4;
  const rows = Math.ceil(n / cols);
  cont.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;

  // Fix panel section height to viewport so charts don't crop panels
  const contentEl = $('content-race');
  const panelsSectionH = contentEl.clientHeight - 16;
  cont.style.height = panelsSectionH + 'px';
  cont.style.flexShrink = '0';
  const availH = panelsSectionH;
  const hdrH = 36;  // panel header height
  const gapTotal = (rows - 1) * 10;
  const panelH = Math.max(120, Math.floor((availH - gapTotal) / rows));
  const canvasH = panelH - hdrH;

  // Check if rebuild needed
  const key = order.join(',');
  if (key === racePanelOrder.join(',')) {
    // Just redraw + resize canvases
    order.forEach((idx, i) => {
      const panel = cont.children[i];
      if (!panel) return;
      const cv = panel.querySelector('.panel-canvas');
      const rd = race.runners[idx];
      if (cv) { cv.style.height = canvasH + 'px'; }
      if (cv && rd) drawMiniMaze(cv, rd);
      // Update badge
      const badge = panel.querySelector('.panel-badge');
      if (badge && rd && rd.done && rd.stats) {
        if (rd.stats.found) {
          badge.textContent = `Path: ${rd.stats.path}  |  ${(rd.stats.time*1000).toFixed(0)} ms`;
          badge.style.background = '#34C759';
        } else {
          badge.textContent = 'No path found';
          badge.style.background = '#FF3B30';
        }
        badge.style.display = 'block';
      }
    });
    return;
  }
  racePanelOrder = [...order];

  // Rebuild
  cont.innerHTML = '';
  order.forEach(idx => {
    const rd = race.runners[idx];
    if (!rd) return;
    const panel = document.createElement('div');
    panel.className = 'race-panel';

    const hdr = document.createElement('div');
    hdr.className = 'panel-header';
    hdr.textContent = rd.name;
    const col = BAR_PAL[idx % BAR_PAL.length];
    hdr.style.background = col;

    const cv = document.createElement('canvas');
    cv.className = 'panel-canvas';
    cv.style.height = canvasH + 'px';

    const badge = document.createElement('div');
    badge.className = 'panel-badge';

    panel.appendChild(hdr);
    panel.appendChild(cv);
    panel.appendChild(badge);
    cont.appendChild(panel);

    drawMiniMaze(cv, rd);

    if (rd.done && rd.stats) {
      if (rd.stats.found) {
        badge.textContent = `Path: ${rd.stats.path}  |  ${(rd.stats.time*1000).toFixed(0)} ms`;
        badge.style.background = '#34C759';
      } else {
        badge.textContent = 'No path found';
        badge.style.background = '#FF3B30';
      }
      badge.style.display = 'block';
    }
  });
}

function drawMiniMaze(canvas, rd) {
  if (!rd || !rd.grid) return;
  const dpr = devicePixelRatio || 1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * dpr; canvas.height = h * dpr;
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const rows = viz?.rows || 28, cols = viz?.cols || 40;
  const cell = Math.max(2, Math.min(Math.floor(w / cols), Math.floor(h / rows)));
  const gw = cols * cell, gh = rows * cell;
  const ox = Math.floor((w - gw) / 2), oy = Math.floor((h - gh) / 2);

  ctx.fillStyle = '#F2F2F7';
  ctx.fillRect(0, 0, w, h);

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const t = rd.grid[r * cols + c];
      ctx.fillStyle = CELL_C[t] || '#FFF';
      ctx.fillRect(ox + c*cell, oy + r*cell, cell, cell);
      if (cell >= 4) {
        ctx.strokeStyle = '#E5E5EA';
        ctx.lineWidth = .3;
        ctx.strokeRect(ox + c*cell + .15, oy + r*cell + .15, cell - .3, cell - .3);
      }
    }
  }
}


// ═══════════════════════════════════════════════════════════════
// CHARTS
// ═══════════════════════════════════════════════════════════════
function drawChart(canvas, data, key, title) {
  if (!data || !data.length) return;
  const dpr = devicePixelRatio || 1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * dpr; canvas.height = h * dpr;
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  // Background
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, w, h);

  // Title
  ctx.font = '600 16px -apple-system, sans-serif';
  ctx.fillStyle = '#000';
  ctx.textAlign = 'left';
  ctx.fillText(title, 16, 24);

  // Horizontal bar chart
  const ml = 110, mr = 60, mt = 38, mb = 12;
  const cw = w - ml - mr, ch = h - mt - mb;
  const n = data.length;
  const vals = data.map(d => key === 'time' ? d[key] * 1000 : d[key]);
  const mx = Math.max(...vals) || 1;

  const gap = 5;
  const barH = Math.min(28, Math.max(14, (ch - (n - 1) * gap) / n));
  const startY = mt + (ch - (n * barH + (n - 1) * gap)) / 2;

  for (let i = 0; i < n; i++) {
    const bw = Math.max(4, cw * vals[i] / mx);
    const by = startY + i * (barH + gap);
    const col = BAR_PAL[i % BAR_PAL.length];

    // Bar
    ctx.fillStyle = col;
    ctx.beginPath();
    ctx.roundRect(ml, by, bw, barH, 4);
    ctx.fill();

    // Algorithm name (left)
    ctx.font = '600 13px -apple-system, sans-serif';
    ctx.fillStyle = '#000';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    ctx.fillText(data[i].name.substring(0, 14), ml - 10, by + barH / 2);

    // Value (right of bar)
    const vl = key === 'time' ? vals[i].toFixed(1) : Math.round(vals[i]) + '';
    ctx.textAlign = 'left';
    ctx.fillStyle = '#555';
    ctx.fillText(vl, ml + bw + 8, by + barH / 2);
  }
  ctx.textBaseline = 'alphabetic';
}


// ═══════════════════════════════════════════════════════════════
// POLLING
// ═══════════════════════════════════════════════════════════════
async function poll() {
  try {
    if (tab === 'visualize') {
      viz = await (await fetch('/api/state')).json();
      if (viz.rows !== lastVizRows || viz.cols !== lastVizCols) {
        gZoom = 1; gOffX = 0; gOffY = 0;
        lastVizRows = viz.rows; lastVizCols = viz.cols;
        prevGrid = null; animCells.clear();
      }
      if (viz.grid) updateAnimations(viz.grid, viz.rows, viz.cols);
      updateVizUI();

      if (viz.show_tree) {
        const td = await (await fetch('/api/tree')).json();
        if (td) { treeData = td; }
      }
    } else {
      race = await (await fetch('/api/race')).json();
      // Also fetch viz for grid dimensions
      if (!viz) viz = await (await fetch('/api/state')).json();
      updateRaceUI();
    }
  } catch(_) {}
}

setInterval(poll, 40); // ~25fps polling


// ═══════════════════════════════════════════════════════════════
// RENDER LOOP
// ═══════════════════════════════════════════════════════════════
function render() {
  if (tab === 'visualize') {
    fitCanvas(gridCanvas, $('grid-area'));
    drawGrid();
    if (viz?.show_tree && treeData) {
      fitCanvas(treeCanvas, treeCanvas.parentElement);
      drawTree();
    }
  }
  requestAnimationFrame(render);
}

function onResize() {
  if (tab === 'visualize') {
    fitCanvas(gridCanvas, $('grid-area'));
    if (viz?.show_tree) {
      fitCanvas(treeCanvas, treeCanvas.parentElement);
      tFit = true;
    }
  }
}
window.addEventListener('resize', onResize);


// ═══════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════
onResize();
poll();
requestAnimationFrame(render);
