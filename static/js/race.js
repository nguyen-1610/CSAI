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
    '#007AFF', '#34C759', '#FF9500', '#FF3B30',
    '#5856D6', '#AF52DE', '#00C7BE', '#FFCC00',
  ];

  let racePanelOrder = [];

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

  function buildRaceToggles() {
    const container = $('race-algos');
    container.innerHTML = '';
    ALG_NAMES.forEach((name, i) => {
      const button = document.createElement('button');
      button.className = 'race-toggle';
      button.dataset.idx = i;
      const color = BAR_PAL[i % BAR_PAL.length];
      button.innerHTML = `<span class="color-bar" style="background:${color}"></span>${name}`;
      button.addEventListener('click', () => act({action:'race_toggle', idx:i}));
      container.appendChild(button);
    });
  }

  function drawMiniMaze(canvas, runnerData) {
    if (!runnerData || !runnerData.grid) return;
    const dpr = devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
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

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const t = runnerData.grid[r * cols + c];
        ctx.fillStyle = CELL_C[t] || '#FFF';
        ctx.fillRect(ox + c * cell, oy + r * cell, cell, cell);
        if (cell >= 4) {
          ctx.strokeStyle = '#E5E5EA';
          ctx.lineWidth = 0.3;
          ctx.strokeRect(ox + c * cell + 0.15, oy + r * cell + 0.15, cell - 0.3, cell - 0.3);
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

    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, w, h);

    ctx.font = '600 16px -apple-system, sans-serif';
    ctx.fillStyle = '#000';
    ctx.textAlign = 'left';
    ctx.fillText(title, 16, 24);

    const ml = 110;
    const mr = 60;
    const mt = 38;
    const mb = 12;
    const cw = w - ml - mr;
    const ch = h - mt - mb;
    const n = data.length;
    const vals = data.map(item => key === 'time' ? item[key] * 1000 : item[key]);
    const mx = Math.max(...vals) || 1;

    const gap = 5;
    const barH = Math.min(20, Math.max(12, (ch - (n - 1) * gap) / n));
    const startY = mt + (ch - (n * barH + (n - 1) * gap)) / 2;

    for (let i = 0; i < n; i++) {
      const bw = Math.max(4, cw * vals[i] / mx);
      const by = startY + i * (barH + gap);
      const color = BAR_PAL[i % BAR_PAL.length];

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.roundRect(ml, by, bw, barH, 4);
      ctx.fill();

      ctx.strokeStyle = 'rgba(0,0,0,0.75)';
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.roundRect(ml, by, bw, barH, 4);
      ctx.stroke();

      ctx.font = '600 13px -apple-system, sans-serif';
      ctx.fillStyle = '#000';
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      ctx.fillText(data[i].name.substring(0, 14), ml - 10, by + barH / 2);

      const valueLabel = key === 'time' ? vals[i].toFixed(1) : `${Math.round(vals[i])}`;
      ctx.textAlign = 'left';
      ctx.fillStyle = '#555';
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
    const panelsSectionH = contentEl.clientHeight - 16;
    container.style.height = `${panelsSectionH}px`;
    container.style.flexShrink = '0';
    const gapTotal = (rows - 1) * 10;
    const panelH = Math.max(120, Math.floor((panelsSectionH - gapTotal) / rows));
    const canvasH = panelH - 36;

    const key = order.join(',');
    if (key === racePanelOrder.join(',')) {
      order.forEach((idx, i) => {
        const panel = container.children[i];
        if (!panel) return;
        const canvas = panel.querySelector('.panel-canvas');
        const runnerData = race.runners[idx];
        if (canvas) canvas.style.height = `${canvasH}px`;
        if (canvas && runnerData) drawMiniMaze(canvas, runnerData);
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
    racePanelOrder = [...order];

    container.innerHTML = '';
    order.forEach(idx => {
      const runnerData = race.runners[idx];
      if (!runnerData) return;
      const panel = document.createElement('div');
      panel.className = 'race-panel';

      const header = document.createElement('div');
      header.className = 'panel-header';
      header.textContent = runnerData.name;
      header.style.background = BAR_PAL[idx % BAR_PAL.length];

      const canvas = document.createElement('canvas');
      canvas.className = 'panel-canvas';
      canvas.style.height = `${canvasH}px`;

      const badge = document.createElement('div');
      badge.className = 'panel-badge';

      panel.appendChild(header);
      panel.appendChild(canvas);
      panel.appendChild(badge);
      container.appendChild(panel);

      drawMiniMaze(canvas, runnerData);

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
