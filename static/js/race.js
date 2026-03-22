/* Race tab logic */

window.RacePage = (() => {
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
  const BAR_PAL = [
    '#4B83E0', '#2EBF8A', '#F5A623', '#E05C5C',
    '#9B6FE0', '#1AB8C4', '#E87D4A', '#6BB87A',
  ];

  let racePanelOrder = [];
  const prevRaceGrids = new Map();
  const raceAnimCells = new Map();
  let raceRafId = null;

  const { $, act, state } = window.App;

  function raceState() {
    return state.race;
  }

  async function ensureVizState() {
    if (!state.viz) {
      try {
        state.viz = await (await fetch('/api/state')).json();
      } catch (_) {}
    }
  }

  function updateRaceAnimations(idx, grid, path, gridCols) {
    const prev = prevRaceGrids.get(idx);
    if (!prev || prev.length !== grid.length) {
      prevRaceGrids.set(idx, grid.slice());
      return;
    }
    const now = performance.now();
    let animMap = raceAnimCells.get(idx);
    if (!animMap) { animMap = new Map(); raceAnimCells.set(idx, animMap); }

    const pathIdx = new Map();
    (path || []).forEach(([r, c], i) => pathIdx.set(`${r},${c}`, i));

    for (let i = 0; i < grid.length; i++) {
      if (prev[i] !== 6 && grid[i] === 6) {
        const r = Math.floor(i / gridCols);
        const c = i % gridCols;
        const key = `${r},${c}`;
        const delay = (pathIdx.get(key) ?? 0) * 18;
        animMap.set(key, { startTime: now + delay, duration: 320 });
      }
    }
    prevRaceGrids.set(idx, grid.slice());
  }

  function renderRace() {
    raceRafId = null;
    if (state.tab !== 'race') return;
    const race = raceState();
    if (!race || race.order.length === 0) return;

    const container = $('race-panels');
    race.order.forEach((idx, i) => {
      const panel = container.children[i];
      if (!panel) return;
      const canvas = panel.querySelector('.panel-canvas');
      const runnerData = race.runners[idx];
      if (canvas && runnerData) drawMiniMaze(canvas, runnerData, idx);
    });

    // Keep loop alive while running or any animation is still in progress.
    let cont = race.running;
    if (!cont) {
      const now = performance.now();
      outer: for (const animMap of raceAnimCells.values()) {
        for (const anim of animMap.values()) {
          if (now < anim.startTime + anim.duration) { cont = true; break outer; }
        }
      }
    }
    if (cont) raceRafId = requestAnimationFrame(renderRace);
  }

  function buildRaceToggles() {
    const container = $('race-algos');
    container.innerHTML = '';
    ALG_NAMES.forEach((name, i) => {
      const button = document.createElement('button');
      button.className = 'race-toggle';
      button.dataset.idx = i;
      button.textContent = name;
      button.addEventListener('click', () => act({action:'race_toggle', idx:i}));
      container.appendChild(button);
    });
  }

  function drawMiniMaze(canvas, runnerData, idx) {
    if (!runnerData || !runnerData.grid) return;
    const dpr = devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    if (!w || !h) return;

    const tw = Math.round(w * dpr);
    const th = Math.round(h * dpr);
    if (canvas.width !== tw || canvas.height !== th) {
      canvas.width = tw;
      canvas.height = th;
    }
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const rows = state.viz?.rows || 28;
    const cols = state.viz?.cols || 40;
    const cell = Math.max(2, Math.min(Math.floor(w / cols), Math.floor(h / rows)));
    const gw = cols * cell;
    const gh = rows * cell;
    const ox = Math.floor((w - gw) / 2);
    const oy = Math.floor((h - gh) / 2);

    ctx.fillStyle = '#F2F2F7';
    ctx.fillRect(0, 0, w, h);

    const now = performance.now();
    const animMap = idx !== undefined ? raceAnimCells.get(idx) : null;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const t = runnerData.grid[r * cols + c];
        const x = ox + c * cell;
        const y = oy + r * cell;
        const key = `${r},${c}`;
        const anim = (t === 6 && animMap) ? animMap.get(key) : null;

        if (anim && cell >= 4 && now >= anim.startTime) {
          const elapsed = now - anim.startTime;
          const progress = Math.min(elapsed / anim.duration, 1);
          if (progress >= 1) animMap.delete(key);
          const c1 = 1.70158;
          const c3 = c1 + 1;
          const scale = Math.max(0, 1 + c3 * Math.pow(progress - 1, 3) + c1 * Math.pow(progress - 1, 2));

          ctx.fillStyle = CELL_C[4];
          ctx.fillRect(x, y, cell, cell);
          if (scale > 0) {
            const s = cell * scale;
            const bx = x + (cell - s) / 2;
            const by = y + (cell - s) / 2;
            ctx.save();
            ctx.beginPath();
            ctx.rect(x, y, cell, cell);
            ctx.clip();
            ctx.fillStyle = CELL_C[6];
            ctx.beginPath();
            ctx.roundRect(bx, by, s, s, s * 0.22);
            ctx.fill();
            ctx.restore();
          }
        } else {
          ctx.fillStyle = anim ? CELL_C[4] : (CELL_C[t] || CELL_C[0]);
          ctx.fillRect(x, y, cell, cell);
        }

        if (cell >= 4) {
          ctx.strokeStyle = '#E5E5EA';
          ctx.lineWidth = 0.3;
          ctx.strokeRect(x + 0.15, y + 0.15, cell - 0.3, cell - 0.3);
        }
      }
    }
  }

  function drawChart(canvas, data, key, title) {
    if (!data || !data.length) return;
    const dpr = devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    ctx.fillStyle = '#FAFBFF';
    ctx.fillRect(0, 0, w, h);

    ctx.font = '700 11px -apple-system, BlinkMacSystemFont, sans-serif';
    ctx.fillStyle = '#8E8E93';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'alphabetic';
    ctx.fillText(title.toUpperCase(), 16, 21);

    const ml = 116;
    const mr = 76;
    const mt = 32;
    const mb = 10;
    const cw = w - ml - mr;
    const ch = h - mt - mb;
    const n = data.length;
    const vals = data.map(item => key === 'time' ? item[key] * 1000 : item[key]);
    const mx = Math.max(...vals) || 1;

    const gap = 8;
    const barH = Math.min(24, Math.max(14, (ch - (n - 1) * gap) / n));
    const startY = mt + (ch - (n * barH + (n - 1) * gap)) / 2;

    for (let i = 0; i < n; i++) {
      const bw = Math.max(4, cw * vals[i] / mx);
      const by = startY + i * (barH + gap);
      const color = BAR_PAL[(data[i].alg_idx ?? i) % BAR_PAL.length];

      // background track
      ctx.fillStyle = '#ECEEF5';
      ctx.beginPath();
      ctx.roundRect(ml, by, cw, barH, 5);
      ctx.fill();

      // colored bar
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.roundRect(ml, by, bw, barH, 5);
      ctx.fill();

      // name label
      ctx.font = '600 12px -apple-system, BlinkMacSystemFont, sans-serif';
      ctx.fillStyle = '#3A3A3C';
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      ctx.fillText(data[i].name.substring(0, 15), ml - 8, by + barH / 2);

      // value label
      let valueLabel;
      if (key === 'time') {
        valueLabel = vals[i] < 1 ? vals[i].toFixed(2) + ' ms' : vals[i].toFixed(1) + ' ms';
      } else {
        valueLabel = `${Math.round(vals[i])}`;
      }
      ctx.font = '600 12px -apple-system, BlinkMacSystemFont, sans-serif';
      ctx.fillStyle = '#5D6778';
      ctx.textAlign = 'left';
      ctx.fillText(valueLabel, ml + bw + 8, by + barH / 2);
    }
    ctx.textBaseline = 'alphabetic';
  }

  function buildRacePanels() {
    const race = raceState();
    const container = $('race-panels');
    const order = race.order;
    const n = order.length;

    if (n === 0) {
      container.innerHTML = '';
      racePanelOrder = [];
      return;
    }

    const cols = n <= 2 ? n : n <= 4 ? 2 : n <= 6 ? 3 : 4;
    const rows = Math.ceil(n / cols);
    container.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;

    const contentEl = $('content-race');
    const panelsSectionH = contentEl.clientHeight - 6;
    container.style.height = `${panelsSectionH}px`;
    container.style.flexShrink = '0';
    const gapTotal = (rows - 1) * 10;
    const panelH = Math.max(120, Math.floor((panelsSectionH - gapTotal) / rows));
    const canvasH = panelH - 24;

    const key = order.join(',');
    if (key === racePanelOrder.join(',')) {
      order.forEach((idx, i) => {
        const panel = container.children[i];
        if (!panel) return;
        const canvas = panel.querySelector('.panel-canvas');
        const runnerData = race.runners[idx];
        if (canvas) canvas.style.height = `${canvasH}px`;
        if (runnerData) updateRaceAnimations(idx, runnerData.grid, runnerData.path,
          state.viz?.cols || 40);
        const badge = panel.querySelector('.panel-badge');
        if (badge && runnerData && runnerData.done && runnerData.stats) {
          if (runnerData.stats.found) {
            badge.textContent = `Path: ${runnerData.stats.path}  |  ${(runnerData.stats.time * 1000).toFixed(0)} ms`;
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
    prevRaceGrids.clear();
    raceAnimCells.clear();
    racePanelOrder = [...order];

    container.innerHTML = '';
    order.forEach(idx => {
      const runnerData = race.runners[idx];
      if (!runnerData) return;
      const panel = document.createElement('div');
      panel.className = 'race-panel';
      panel.style.borderTop = `3px solid ${BAR_PAL[idx % BAR_PAL.length]}`;

      const header = document.createElement('div');
      header.className = 'panel-header';
      header.textContent = runnerData.name;

      const canvas = document.createElement('canvas');
      canvas.className = 'panel-canvas';
      canvas.style.height = `${canvasH}px`;

      const badge = document.createElement('div');
      badge.className = 'panel-badge';

      panel.appendChild(header);
      panel.appendChild(canvas);
      panel.appendChild(badge);
      container.appendChild(panel);

      updateRaceAnimations(idx, runnerData.grid, runnerData.path,
        state.viz?.rows || 28, state.viz?.cols || 40);
      drawMiniMaze(canvas, runnerData, idx);

      if (runnerData.done && runnerData.stats) {
        if (runnerData.stats.found) {
          badge.textContent = `Path: ${runnerData.stats.path}  |  ${(runnerData.stats.time * 1000).toFixed(0)} ms`;
          badge.style.background = '#34C759';
        } else {
          badge.textContent = 'No path found';
          badge.style.background = '#FF3B30';
        }
        badge.style.display = 'block';
      }
    });
  }

  function updateUI() {
    const race = raceState();
    if (!race) return;

    const selected = new Set(race.order);
    document.querySelectorAll('.race-toggle').forEach(button => {
      const i = +button.dataset.idx;
      const color = BAR_PAL[i % BAR_PAL.length];
      if (selected.has(i)) {
        button.classList.add('selected');
        button.style.background = color;
      } else {
        button.classList.remove('selected');
        button.style.background = '';
      }
    });

    const runButton = $('btn-race');
    if (race.running) {
      runButton.textContent = 'Pause';
      runButton.className = 'btn btn-run pausing';
      runButton.disabled = false;
    } else if (race.paused && !race.done) {
      runButton.textContent = 'Continue';
      runButton.className = 'btn btn-run btn-continue';
      runButton.disabled = false;
    } else if (race.order.length >= 2) {
      runButton.textContent = 'Race';
      runButton.className = 'btn btn-run';
      runButton.disabled = false;
    } else {
      runButton.textContent = 'Race';
      runButton.className = 'btn btn-run';
      runButton.disabled = true;
    }

    const raceActive = race.running || (race.paused && !race.done);
    $('race-btn-step-back').disabled = (race.step_ptr ?? -1) < 1 || race.done || race.running;
    $('race-btn-step-fwd').disabled = race.running || race.done;
    $('race-btn-cancel').classList.toggle('hidden', !raceActive && !race.done);

    buildRacePanels();

    if (race.results) {
      $('race-charts').classList.remove('hidden');
      drawChart($('chart-nodes'), race.results, 'nodes', 'Nodes Visited');
      drawChart($('chart-path'), race.results, 'path', 'Path Length');
      drawChart($('chart-cost'), race.results, 'cost', 'Cost');
      drawChart($('chart-time'), race.results, 'time', 'Time (ms)');
    } else {
      $('race-charts').classList.add('hidden');
    }
  }

  async function poll() {
    if (state.tab !== 'race') return;
    try {
      state.race = await (await fetch('/api/race')).json();
      await ensureVizState();
      updateUI();
      if (!raceRafId) raceRafId = requestAnimationFrame(renderRace);
    } catch (_) {}
  }

  function bindUI() {
    buildRaceToggles();

    $('btn-race').addEventListener('click', () => {
      if (!raceState()) return;
      act({action:'race_start'});
    });
    $('race-btn-step-back').addEventListener('click', () => act({action:'race_step_back'}));
    $('race-btn-step-fwd').addEventListener('click', () => act({action:'race_step'}));
    $('race-btn-cancel').addEventListener('click', () => act({action:'race_cancel'}));

    $('race-btn-spd-dn').addEventListener('click', () => {
      const v = Math.max(1, (state.viz?.speed || 20) - 1);
      $('race-speed-val').textContent = v;
      $('race-speed-slider').value = v;
      act({action:'speed', value:v});
    });
    $('race-btn-spd-up').addEventListener('click', () => {
      const v = Math.min(400, (state.viz?.speed || 20) + 1);
      $('race-speed-val').textContent = v;
      $('race-speed-slider').value = v;
      act({action:'speed', value:v});
    });
    $('race-speed-slider').addEventListener('input', e => {
      $('race-speed-val').textContent = e.target.value;
      act({action:'speed', value:+e.target.value});
    });
  }

  function init() {
    bindUI();
    poll();
    setInterval(poll, 40);
  }

  return { init };
})();
