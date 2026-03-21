/* Visualize tab logic */

window.VisualizePage = (() => {
  const CELL_C = [
    '#FFFFFF',
    '#1C1C1E',
    '#34C759',
    '#FF3B30',
    '#007AFF',
    '#5856D6',
    '#FF9500',
    '#FFD60A',
    '#1B6CA8',
    '#8B5E3C',
    '#8BC34A',
  ];
  const NODE_GAP = 38;
  const LEVEL_GAP = 80;

  let gridCanvas;
  let gridCtx;
  let treeCanvas;
  let treeCtx;

  let mDown = false;
  let mBtn = 0;
  let gInfo = { rows:0, cols:0, cell:0, ox:0, oy:0 };

  let tZoom = 1;
  let tOx = 0;
  let tOy = 0;
  let tDrag = null;
  let tFit = true;
  let tFocusRoot = false;

  let ddOpen = false;

  let lastVizRows = 0;
  let lastVizCols = 0;

  let dragType = null;
  let dragCell = null;
  let lastDragSent = null;

  let cpPlaceMode = false;
  let terrainBrush = 0;

  let prevGrid = null;
  const animCells = new Map();
  let lastTreeVisible = false;

  const { $, act, fitCanvas, state } = window.App;

  function vizState() {
    return state.viz;
  }

  function treeState() {
    return state.treeData;
  }

  function setTerrainBrush(type) {
    terrainBrush = terrainBrush === type ? 0 : type;
    if (terrainBrush) cpPlaceMode = false;
    document.querySelectorAll('.btn-terrain').forEach(button => {
      button.classList.toggle('btn-selected', +button.dataset.terrain === terrainBrush);
    });
  }

  function buildAlgoList() {
    const list = $('algo-list');
    list.innerHTML = '';
    ALG_NAMES.forEach((name, i) => {
      const item = document.createElement('div');
      item.className = 'dd-item';
      item.innerHTML = `<span>${name}</span>`;
      item.addEventListener('click', () => {
        act({action:'select_algo', idx:i});
        ddOpen = false;
        list.classList.add('hidden');
      });
      list.appendChild(item);
    });
  }

  function updateAnimations(newGrid, rows, cols) {
    if (!prevGrid || prevGrid.length !== newGrid.length) {
      prevGrid = newGrid.slice();
      return;
    }
    const now = performance.now();
    const pathIdx = new Map();
    (vizState()?.path_cells || []).forEach(([r, c], i) => pathIdx.set(`${r},${c}`, i));

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const i = r * cols + c;
        const oldT = prevGrid[i];
        const newT = newGrid[i];
        if (oldT === newT) continue;
        const key = `${r},${c}`;
        if (newT === 6) {
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
    const viz = vizState();
    if (!viz) return;
    const { rows, cols, grid } = viz;
    const cw = gridCanvas.clientWidth;
    const ch = gridCanvas.clientHeight;
    const baseCellRaw = Math.min(cw / cols, ch / rows);
    const cell = Math.max(1, Math.floor(baseCellRaw));
    const gw = cols * cell;
    const gh = rows * cell;
    const ox = Math.floor((cw - gw) / 2);
    const oy = Math.floor((ch - gh) / 2);
    gInfo = { rows, cols, cell, ox, oy };

    gridCtx.fillStyle = '#F2F2F7';
    gridCtx.fillRect(0, 0, cw, ch);

    const now = performance.now();
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        let t = grid[r * cols + c];
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

        const x = ox + c * cell;
        const y = oy + r * cell;
        const key = `${r},${c}`;
        const anim = t === 6 ? animCells.get(key) : null;

        if (anim && cell >= 4 && now >= anim.startTime) {
          const elapsed = now - anim.startTime;
          const progress = Math.min(elapsed / anim.duration, 1);
          if (progress >= 1) animCells.delete(key);
          const c1 = 1.70158;
          const c3 = c1 + 1;
          const scale = Math.max(0, 1 + c3 * Math.pow(progress - 1, 3) + c1 * Math.pow(progress - 1, 2));

          gridCtx.fillStyle = CELL_C[4];
          gridCtx.fillRect(x, y, cell, cell);

          if (scale > 0) {
            const s = cell * scale;
            const bx = x + (cell - s) / 2;
            const by = y + (cell - s) / 2;
            gridCtx.save();
            gridCtx.beginPath();
            gridCtx.rect(x, y, cell, cell);
            gridCtx.clip();
            gridCtx.fillStyle = CELL_C[6];
            const rad = s * 0.22;
            gridCtx.beginPath();
            gridCtx.roundRect(bx, by, s, s, rad);
            gridCtx.fill();
            gridCtx.restore();
          }
        } else {
          gridCtx.fillStyle = anim ? CELL_C[4] : (CELL_C[t] || CELL_C[0]);
          gridCtx.fillRect(x, y, cell, cell);
        }

        if (cell >= 6) {
          gridCtx.strokeStyle = '#E5E5EA';
          gridCtx.lineWidth = 0.5;
          gridCtx.strokeRect(x + 0.25, y + 0.25, cell - 0.5, cell - 0.5);
        }
        if (dragCell && r === dragCell.r && c === dragCell.c && dragType) {
          gridCtx.strokeStyle = 'rgba(255,255,255,0.75)';
          gridCtx.lineWidth = Math.max(1.5, cell * 0.12);
          gridCtx.strokeRect(x + 1.5, y + 1.5, cell - 3, cell - 3);
        }

        if (viz.show_tree && cell >= 12) {
          const fontSize = Math.max(6, Math.floor(cell * 0.28));
          gridCtx.font = `${fontSize}px var(--font, sans-serif)`;
          gridCtx.textAlign = 'center';
          gridCtx.textBaseline = 'middle';
          const isLight = t === 0 || t === 10;
          gridCtx.fillStyle = isLight ? 'rgba(0,0,0,0.45)' : 'rgba(255,255,255,0.55)';
          gridCtx.fillText(`${r},${c}`, x + cell / 2, y + cell / 2);
        }
      }
    }
  }

  function gridPos(e) {
    const rect = gridCanvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const { rows, cols, cell, ox, oy } = gInfo;
    const c = Math.floor((mx - ox) / cell);
    const r = Math.floor((my - oy) / cell);
    return (r >= 0 && r < rows && c >= 0 && c < cols) ? { r, c } : null;
  }

  function autoFitTree(data, w, h) {
    if (!data || !data.bounds) return;
    const [bw, bh] = data.bounds;
    if (bw <= 0 || bh <= 0) return;
    const pad = 28;
    const tw = bw * NODE_GAP;
    const th = bh * LEVEL_GAP;
    tZoom = Math.min((w - pad * 2) / Math.max(tw, 1), (h - pad * 2) / Math.max(th, 1), 2.5);
    tZoom = Math.max(tZoom, 0.08);
    tOx = (w - tw * tZoom) / 2;
    tOy = pad;
  }

  function focusTreeRoot(data, w, h) {
    if (!data || !data.positions?.length) return;
    const root = data.positions.find(pos =>
      pos.node[0] === data.start[0] && pos.node[1] === data.start[1]
    ) || data.positions[0];
    if (!root) return;
    tZoom = Math.max(1, Math.min((w - 80) / (NODE_GAP * 8), 2.2));
    tOx = w / 2 - root.x * NODE_GAP * tZoom;
    tOy = 46 - root.y * LEVEL_GAP * tZoom;
  }

  function drawTree() {
    const treeData = treeState();
    if (!treeData || !treeData.positions.length) return;
    const w = treeCanvas.clientWidth;
    const h = treeCanvas.clientHeight;

    if (tFocusRoot) {
      focusTreeRoot(treeData, w, h);
      tFocusRoot = false;
      tFit = false;
    } else if (tFit) {
      autoFitTree(treeData, w, h);
      tFit = false;
    }

    treeCtx.fillStyle = '#F8F9FC';
    treeCtx.fillRect(0, 0, w, h);

    const nodes = {};
    for (const pos of treeData.positions) {
      const key = pos.node.join(',');
      nodes[key] = {
        x: tOx + pos.x * NODE_GAP * tZoom,
        y: tOy + pos.y * LEVEL_GAP * tZoom,
        ip: pos.ip,
        node: pos.node,
      };
    }
    const startK = treeData.start.join(',');
    const endK = treeData.end.join(',');
    const baseR = Math.max(12, 18 * tZoom);
    const specR = Math.max(16, 22 * tZoom);

    for (const edge of treeData.edges) {
      const a = nodes[edge.from.join(',')];
      const b = nodes[edge.to.join(',')];
      if (!a || !b) continue;
      treeCtx.beginPath();
      treeCtx.moveTo(a.x, a.y);
      treeCtx.lineTo(b.x, b.y);
      treeCtx.strokeStyle = edge.ip ? '#FF9500' : '#D2DEF0';
      treeCtx.lineWidth = edge.ip ? Math.max(2, 3 * tZoom) : Math.max(1, 1.2 * tZoom);
      treeCtx.stroke();
    }

    for (const [key, node] of Object.entries(nodes)) {
      const isS = key === startK;
      const isE = key === endK;
      const radius = (isS || isE) ? specR : baseR;
      treeCtx.beginPath();
      treeCtx.arc(node.x, node.y, radius, 0, Math.PI * 2);
      if (isS) treeCtx.fillStyle = '#34C759';
      else if (isE) treeCtx.fillStyle = '#FF3B30';
      else if (node.ip) treeCtx.fillStyle = '#FF9500';
      else treeCtx.fillStyle = '#AFC8F0';
      treeCtx.fill();
      treeCtx.strokeStyle = '#fff';
      treeCtx.lineWidth = 1;
      treeCtx.stroke();

      const size = Math.max(10, 13 * tZoom);
      treeCtx.font = `600 ${size}px -apple-system, sans-serif`;
      treeCtx.textAlign = 'center';
      treeCtx.textBaseline = 'middle';
      treeCtx.fillStyle = (node.ip || isS || isE) ? '#fff' : '#28284A';
      treeCtx.fillText(node.node.join(','), node.x, node.y);
    }

    $('tree-info').textContent =
      `Tree: ${treeData.algo}  •  ${treeData.shown}` +
      (treeData.shown < treeData.total ? ` / ${treeData.total}` : '') +
      ' nodes';
    $('tree-hint').textContent = `Scroll=zoom  Drag=pan  (${tZoom.toFixed(2)}x)`;
  }

  function updateUI() {
    const viz = vizState();
    if (!viz) return;

    const runButton = $('btn-run');
    const isActive = viz.running || viz.paused;
    if (viz.running) {
      runButton.textContent = 'Pause';
      runButton.className = 'btn btn-run pausing';
    } else if (viz.paused && !viz.finished) {
      runButton.textContent = 'Continue';
      runButton.className = 'btn btn-run btn-continue';
    } else {
      runButton.textContent = 'Run';
      runButton.className = 'btn btn-run';
    }
    $('btn-step-back').disabled = (viz.step_ptr ?? -1) < 1 || viz.finished;
    $('btn-step-fwd').disabled = viz.running || viz.finished || viz.maze_running;
    $('btn-cancel').classList.toggle('hidden', !isActive && !viz.finished);

    $('btn-maze').textContent = viz.maze_running ? 'Generating…' : 'Generate Maze';
    $('btn-maze').disabled = !!viz.maze_running;

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

    $('st-nodes').textContent = viz.stats.nodes;
    $('st-path').textContent = viz.stats.path;
    $('st-cost').textContent = viz.stats.cost;
    $('st-time').textContent = `${(viz.stats.time * 1000).toFixed(1)} ms`;

    const status = $('st-status');
    if (viz.running) {
      status.textContent = 'Running...';
      status.style.color = '#FF9500';
    } else if (viz.stats.found === true) {
      status.textContent = 'Path Found';
      status.style.color = '#34C759';
    } else if (viz.stats.found === false) {
      status.textContent = 'No Path';
      status.style.color = '#FF3B30';
    } else {
      status.textContent = '';
    }

    $('speed-val').textContent = viz.speed;
    $('speed-slider').value = viz.speed;
    $('race-speed-val').textContent = viz.speed;
    $('race-speed-slider').value = viz.speed;

    if (document.activeElement !== $('inp-rows')) $('inp-rows').value = viz.rows;
    if (document.activeElement !== $('inp-cols')) $('inp-cols').value = viz.cols;

    $('algo-name').textContent = ALG_NAMES[viz.cur_alg];

    document.querySelectorAll('.dd-item').forEach((item, i) => {
      item.classList.toggle('selected', i === viz.cur_alg);
      if (i === viz.cur_alg && !item.querySelector('.check')) {
        item.innerHTML += '<span class="check"></span>';
      } else if (i !== viz.cur_alg) {
        const check = item.querySelector('.check');
        if (check) check.remove();
      }
    });

    const treeButton = $('btn-tree');
    const treeCloseButton = $('btn-tree-close');
    const sidebar = $('viz-sidebar');
    if (viz.has_tree) {
      treeButton.classList.remove('hidden');
      treeButton.textContent = viz.show_tree ? 'Hide Tree' : 'Show Tree';
      treeButton.classList.toggle('active-tree', viz.show_tree);
    } else {
      treeButton.classList.add('hidden');
    }
    treeCloseButton.classList.toggle('hidden', !viz.show_tree);

    $('grid-area').classList.toggle('split', !!viz.show_tree);
    $('tree-area').classList.toggle('hidden', !viz.show_tree);
    sidebar.classList.toggle('hidden-tree', !!viz.show_tree);
    sidebar.classList.toggle('expanded-stats', !viz.show_tree && (viz.finished || viz.stats.found !== null));

    if (viz.show_tree && !lastTreeVisible) {
      tFocusRoot = true;
      tFit = false;
    }
    lastTreeVisible = !!viz.show_tree;

  }

  async function poll() {
    if (state.tab !== 'visualize') return;
    try {
      state.viz = await (await fetch('/api/state')).json();
      if (state.viz.rows !== lastVizRows || state.viz.cols !== lastVizCols) {
        lastVizRows = state.viz.rows;
        lastVizCols = state.viz.cols;
        prevGrid = null;
        animCells.clear();
      }
      if (state.viz.grid) updateAnimations(state.viz.grid, state.viz.rows, state.viz.cols);
      updateUI();

      if (state.viz.show_tree) {
        const td = await (await fetch('/api/tree')).json();
        if (td) state.treeData = td;
      } else {
        state.treeData = null;
      }
    } catch (_) {}
  }

  function render() {
    if (state.tab === 'visualize') {
      fitCanvas(gridCanvas, $('grid-area'));
      drawGrid();
      if (vizState()?.show_tree && treeState()) {
        fitCanvas(treeCanvas, treeCanvas.parentElement);
        drawTree();
      }
    }
    requestAnimationFrame(render);
  }

  function onResize() {
    if (state.tab === 'visualize') {
      fitCanvas(gridCanvas, $('grid-area'));
      if (vizState()?.show_tree) {
        fitCanvas(treeCanvas, treeCanvas.parentElement);
        tFocusRoot = true;
      }
    }
  }

  function bindUI() {
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

    $('btn-run').addEventListener('click', () => act({action:'run'}));
    $('btn-step-back').addEventListener('click', () => act({action:'step_back'}));
    $('btn-step-fwd').addEventListener('click', () => act({action:'step'}));
    $('btn-cancel').addEventListener('click', () => act({action:'cancel_algo'}));
    $('btn-clear').addEventListener('click', () => act({action:'clear'}));
    $('btn-maze').addEventListener('click', () => act({action:'maze'}));
    $('btn-weighted-maze').addEventListener('click', () => act({action:'weighted_maze'}));
    $('btn-reset').addEventListener('click', () => act({action:'reset'}));
    $('btn-tree').addEventListener('click', () => {
      act({action:'toggle_tree'});
      tFocusRoot = true;
    });
    $('btn-tree-close').addEventListener('click', () => {
      act({action:'toggle_tree'});
    });

    $('btn-cp-toggle').addEventListener('click', () => {
      if (vizState()?.checkpoint) {
        act({action:'remove_checkpoint'});
      } else {
        cpPlaceMode = !cpPlaceMode;
        if (cpPlaceMode) setTerrainBrush(0);
        $('btn-cp-toggle').classList.toggle('btn-selected', cpPlaceMode);
      }
    });

    document.querySelectorAll('.btn-terrain').forEach(button => {
      button.addEventListener('click', () => setTerrainBrush(+button.dataset.terrain));
    });

    $('btn-spd-down').addEventListener('click', () => {
      const v = Math.max(1, (vizState()?.speed || 20) - 5);
      $('speed-val').textContent = v;
      $('speed-slider').value = v;
      act({action:'speed', value:v});
    });
    $('btn-spd-up').addEventListener('click', () => {
      const v = Math.min(200, (vizState()?.speed || 20) + 5);
      $('speed-val').textContent = v;
      $('speed-slider').value = v;
      act({action:'speed', value:v});
    });
    $('speed-slider').addEventListener('input', e => {
      $('speed-val').textContent = e.target.value;
      act({action:'speed', value:+e.target.value});
    });

    $('btn-row-dn').addEventListener('click', () => act({action:'change_grid', dr:-1, dc:0}));
    $('btn-row-up').addEventListener('click', () => act({action:'change_grid', dr:1, dc:0}));
    $('btn-col-dn').addEventListener('click', () => act({action:'change_grid', dr:0, dc:-1}));
    $('btn-col-up').addEventListener('click', () => act({action:'change_grid', dr:0, dc:1}));

    ['inp-rows', 'inp-cols'].forEach(id => {
      $(id).addEventListener('keydown', e => {
        if (e.key === 'Enter') {
          const rows = +$('inp-rows').value || vizState()?.rows || 28;
          const cols = +$('inp-cols').value || vizState()?.cols || 40;
          act({action:'set_grid', rows, cols});
          e.target.blur();
        }
      });
    });

    document.addEventListener('keydown', e => {
      if (e.target.tagName === 'INPUT') return;
      if (e.key === ' ') {
        e.preventDefault();
        act({action:'run'});
      }
      if (e.key === '.' && state.tab === 'visualize') act({action:'step'});
      if (e.key === ',' && state.tab === 'visualize') act({action:'step_back'});
      if (e.key === 'r' && state.tab === 'visualize') act({action:'reset'});
      if (e.key === 'Escape' && state.tab === 'visualize') act({action:'cancel_algo'});
      if (e.key === 't' && state.tab === 'visualize') {
        act({action:'toggle_tree'});
        tFit = true;
      }
    });

    gridCanvas.addEventListener('mousedown', e => {
      const viz = vizState();
      const p = gridPos(e);
      if (terrainBrush > 0 && p && !viz?.running) {
        mDown = true;
        mBtn = e.button;
        act({action:'set_terrain', r:p.r, c:p.c, terrain: e.button === 2 ? 0 : terrainBrush});
        return;
      }
      if (e.button === 0 && p && !viz?.running) {
        const t = viz?.grid?.[p.r * (viz?.cols ?? 0) + p.c];
        if (t === 2) {
          dragType = 'start';
          dragCell = { ...p };
          lastDragSent = { ...p };
          document.body.style.cursor = 'grabbing';
          return;
        }
        if (t === 3) {
          dragType = 'end';
          dragCell = { ...p };
          lastDragSent = { ...p };
          document.body.style.cursor = 'grabbing';
          return;
        }
        if (t === 7) {
          dragType = 'checkpoint';
          dragCell = { ...p };
          lastDragSent = { ...p };
          document.body.style.cursor = 'grabbing';
          return;
        }
      }
      if (e.button === 0 && (e.shiftKey || cpPlaceMode) && p && !viz?.running) {
        const t = viz?.grid?.[p.r * (viz?.cols ?? 0) + p.c];
        if (t === 7) act({action:'remove_checkpoint'});
        else if (t !== 2 && t !== 3) act({action:'set_checkpoint', r:p.r, c:p.c});
        if (cpPlaceMode) {
          cpPlaceMode = false;
          $('btn-cp-toggle').classList.remove('btn-selected');
        }
        return;
      }
      if (viz?.show_tree) {
        return;
      }
      if (!p) {
        return;
      }
      mDown = true;
      mBtn = e.button;
      act({action:'grid_cell', r:p.r, c:p.c, remove: e.button === 2});
    });

    gridCanvas.addEventListener('mousemove', e => {
      const viz = vizState();
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
      dragType = null;
      dragCell = null;
      lastDragSent = null;
      document.body.style.cursor = '';
      mDown = false;
      tDrag = null;
    });
    gridCanvas.addEventListener('contextmenu', e => e.preventDefault());

    treeCanvas.addEventListener('wheel', e => {
      e.preventDefault();
      const f = e.deltaY < 0 ? 1.12 : 0.88;
      const rect = treeCanvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const nz = Math.max(0.05, Math.min(8, tZoom * f));
      tOx = mx - (mx - tOx) * nz / tZoom;
      tOy = my - (my - tOy) * nz / tZoom;
      tZoom = nz;
    }, {passive: false});

    treeCanvas.addEventListener('mousedown', e => {
      tDrag = { sx: e.clientX, sy: e.clientY, ox: tOx, oy: tOy };
    });

    document.addEventListener('mousemove', e => {
      if (dragType) {
        const p = gridPos(e);
        if (p && (p.r !== lastDragSent?.r || p.c !== lastDragSent?.c)) {
          dragCell = { ...p };
          lastDragSent = { ...p };
          const actionMap = { start:'set_start', end:'set_end', checkpoint:'set_checkpoint' };
          act({ action: actionMap[dragType], r: p.r, c: p.c });
        }
      }
      if (tDrag) {
        tOx = tDrag.ox + e.clientX - tDrag.sx;
        tOy = tDrag.oy + e.clientY - tDrag.sy;
      }
    });
  }

  function init() {
    gridCanvas = $('grid-canvas');
    treeCanvas = $('tree-canvas');
    gridCtx = gridCanvas.getContext('2d');
    treeCtx = treeCanvas.getContext('2d');

    bindUI();

    window.addEventListener('resize', onResize);
    window.App.onTabChange(tab => {
      if (tab === 'visualize') onResize();
    });

    onResize();
    poll();
    setInterval(poll, 40);
    requestAnimationFrame(render);
  }

  return { init };
})();
