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
$('btn-run').addEventListener('click',   () => act({action:'run'}));
$('btn-clear').addEventListener('click', () => act({action:'clear'}));
$('btn-maze').addEventListener('click',  () => act({action:'maze'}));
$('btn-reset').addEventListener('click', () => act({action:'reset'}));
$('btn-tree').addEventListener('click',  () => { act({action:'toggle_tree'}); tFit = true; });

$('btn-spd-down').addEventListener('click', () => {
  const v = Math.max(1, (viz?.speed || 20) - 5);
  act({action:'speed', value:v});
});
$('btn-spd-up').addEventListener('click', () => {
  const v = Math.min(200, (viz?.speed || 20) + 5);
  act({action:'speed', value:v});
});
$('speed-slider').addEventListener('input', e =>
  act({action:'speed', value: +e.target.value}));

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

$('btn-ss').addEventListener('click', () => act({action:'set_mode', mode:'start'}));
$('btn-se').addEventListener('click', () => act({action:'set_mode', mode:'end'}));

// Keyboard shortcuts
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT') return;
  if (e.key === 's') act({action:'set_mode', mode:'start'});
  if (e.key === 'e') act({action:'set_mode', mode:'end'});
  if (e.key === ' ') { e.preventDefault(); act({action:'run'}); }
  if (e.key === 'r') act({action:'reset'});
  if (e.key === 't' && tab === 'visualize') { act({action:'toggle_tree'}); tFit = true; }
});


// ═══════════════════════════════════════════════════════════════
// GRID CANVAS
// ═══════════════════════════════════════════════════════════════
function drawGrid() {
  if (!viz) return;
  const { rows, cols, grid } = viz;
  const cw = gridCanvas.clientWidth, ch = gridCanvas.clientHeight;
  const cell = Math.max(4, Math.min(Math.floor(cw / cols), Math.floor(ch / rows)));
  const gw = cols * cell, gh = rows * cell;
  const ox = Math.floor((cw - gw) / 2), oy = Math.floor((ch - gh) / 2);
  gInfo = { rows, cols, cell, ox, oy };

  const ctx = gridCtx;
  ctx.fillStyle = '#F2F2F7';
  ctx.fillRect(0, 0, cw, ch);

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const t = grid[r * cols + c];
      const x = ox + c * cell, y = oy + r * cell;
      ctx.fillStyle = CELL_C[t];
      ctx.fillRect(x, y, cell, cell);
      if (cell >= 6) {
        ctx.strokeStyle = '#E5E5EA';
        ctx.lineWidth = .5;
        ctx.strokeRect(x + .25, y + .25, cell - .5, cell - .5);
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
  const p = gridPos(e);
  if (!p) return;
  mDown = true; mBtn = e.button;
  act({action:'grid_cell', r:p.r, c:p.c, remove: e.button === 2});
});
gridCanvas.addEventListener('mousemove', e => {
  if (!mDown) return;
  const p = gridPos(e);
  if (p) act({action:'grid_cell', r:p.r, c:p.c, remove: mBtn === 2});
});
document.addEventListener('mouseup', () => { mDown = false; });
gridCanvas.addEventListener('contextmenu', e => e.preventDefault());


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
  if (!tDrag) return;
  tOx = tDrag.ox + e.clientX - tDrag.sx;
  tOy = tDrag.oy + e.clientY - tDrag.sy;
});
document.addEventListener('mouseup', () => { tDrag = null; });


// ═══════════════════════════════════════════════════════════════
// UI UPDATE — VISUALIZE
// ═══════════════════════════════════════════════════════════════
function updateVizUI() {
  if (!viz) return;

  // Run button
  const rb = $('btn-run');
  rb.textContent = viz.running ? 'Pause' : 'Run';
  rb.className = 'btn btn-run' + (viz.running ? ' pausing' : '');

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

  // Speed
  $('speed-val').textContent = viz.speed;
  $('speed-slider').value = viz.speed;

  // Grid size
  if (document.activeElement !== $('inp-rows')) $('inp-rows').value = viz.rows;
  if (document.activeElement !== $('inp-cols')) $('inp-cols').value = viz.cols;

  // Algo
  $('algo-name').textContent = ALG_NAMES[viz.cur_alg];
  $('algo-full').textContent = ALG_FULL[viz.cur_alg];

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

  // Set Start/End selection
  $('btn-ss').classList.toggle('btn-selected', viz.set_mode === 'start');
  $('btn-se').classList.toggle('btn-selected', viz.set_mode === 'end');

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
  if (race.running) act({action:'race_stop'});
  else if (race.order.length >= 2) act({action:'race_start'});
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

  // Race button
  const rb = $('btn-race');
  if (race.running) {
    rb.textContent = 'Stop Race';
    rb.className = 'btn btn-race stop';
    rb.disabled = false;
  } else if (race.order.length >= 2) {
    rb.textContent = `Start Race (${race.order.length})`;
    rb.className = 'btn btn-race ready';
    rb.disabled = false;
  } else {
    rb.textContent = 'Select 2+ algos';
    rb.className = 'btn btn-race';
    rb.disabled = true;
  }

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

  // Calculate panel canvas height to fill available space
  const contentEl = $('content-race');
  const availH = contentEl.clientHeight - 16;
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
