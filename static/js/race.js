/* Race tab logic */

window.RacePage = (() => {
  const CELL_C = [
    "#FDFBF7",
    "#1F2A36",
    "#0E7490",
    "#A44A3F",
    "#6F85A5",
    "#8D6C52",
    "#C59B49",
    "#D8B56A",
    "#4A86B8",
    "#725B67",
    "#9BB74A",
  ];
  const BAR_PAL = [
    "#2E5B9A",
    "#2E8B57",
    "#C65B3A",
    "#A07A1E",
    "#6B5CA5",
    "#8A5A44",
    "#2C98A0",
    "#B35D8A",
  ];
  const ALG_SHORT = {
    "Breadth-First Search": "BFS",
    "Depth-First Search": "DFS",
    "Uniform Cost Search": "UCS",
    "A* Search": "A*",
    "Iterative Deepening DFS": "IDDFS",
    "Bidirectional BFS": "Bi-BFS",
    "Beam Search": "Beam",
    "IDA* Search": "IDA*",
  };
  const CANVAS_FONT = '"Aptos", "Segoe UI Variable", "Segoe UI", sans-serif';
  const CANVAS_SERIF =
    '"Palatino Linotype", "Book Antiqua", "Iowan Old Style", Georgia, serif';

  let racePanelOrder = [];
  const prevRaceGrids = new Map();
  const raceAnimCells = new Map();
  let raceRafId = null;
  let lastResultsSignature = null;
  let lastDpr = window.devicePixelRatio || 1;
  let pollTimerId = null;
  let pollInFlight = false;

  const PANEL_GAP = 12;
  const PANEL_MIN_VIEWPORT_H = 460;
  const PANEL_MIN_H = 190;
  const PANEL_HEADER_H = 32;
  const PANEL_BG = "#E9E0D4";
  const CHART_BG = "#F6F0E5";
  const TRACK_BG = "#E6DDD0";
  const GRID_LINE_MINOR = "rgba(31, 42, 54, 0.1)";
  const GRID_LINE_MAJOR = "rgba(39, 76, 119, 0.16)";
  const GRID_FRAME = "rgba(31, 42, 54, 0.16)";
  const MARKER_LINE = "rgba(255, 248, 240, 0.9)";
  const MARKER_FILL = "rgba(255, 248, 240, 0.96)";
  const BADGE_SUCCESS_BG = "#2F6B4F";
  const BADGE_FAILURE_BG = "#A44A3F";

  const { $, act, state, uiConfig } = window.App;

  function raceState() {
    return state.race;
  }

  function setText(id, value) {
    const el = $(id);
    if (el) el.textContent = value;
  }

  function shortAlgName(name) {
    return ALG_SHORT[name] || name;
  }

  function colorForAlgo(algIdx, fallbackIdx = 0) {
    return BAR_PAL[(algIdx ?? fallbackIdx) % BAR_PAL.length];
  }

  function getCanvasBox(canvas, { resizeAlways = false } = {}) {
    const dpr = devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    if (!w || !h) return null;

    const tw = Math.round(w * dpr);
    const th = Math.round(h * dpr);
    if (resizeAlways || canvas.width !== tw || canvas.height !== th) {
      canvas.width = tw;
      canvas.height = th;
    }

    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { ctx, w, h };
  }

  function easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
  }

  function drawMiniMazeOverlay(ctx, x, y, cell, color, progress) {
    const eased = easeOutCubic(progress);
    const scale = 0.56 + eased * 0.44;
    const size = cell * scale;
    const bx = x + (cell - size) / 2;
    const by = y + (cell - size) / 2;
    ctx.save();
    ctx.globalAlpha = 0.18 + eased * 0.82;
    ctx.fillStyle = color;
    if (cell >= 4) {
      ctx.beginPath();
      ctx.roundRect(bx, by, size, size, Math.max(2, size * 0.18));
      ctx.fill();
    } else {
      ctx.fillRect(bx, by, size, size);
    }
    ctx.restore();
  }

  function drawMarkerAccent(ctx, x, y, cell, type) {
    if (type !== 2 && type !== 3 && type !== 7) return;

    ctx.save();

    if (cell >= 8) {
      const inset = Math.max(0.9, cell * 0.16);
      const size = Math.max(2, cell - inset * 2);
      ctx.strokeStyle = MARKER_LINE;
      ctx.lineWidth = Math.max(0.9, cell * 0.06);
      ctx.beginPath();
      ctx.roundRect(
        x + inset,
        y + inset,
        size,
        size,
        Math.max(1.8, size * 0.2),
      );
      ctx.stroke();
    }

    if (cell >= 14) {
      const cx = x + cell / 2;
      const cy = y + cell / 2;
      const symbolSize = cell * 0.36;
      const half = symbolSize / 2;

      ctx.fillStyle = MARKER_FILL;
      ctx.beginPath();

      if (type === 2) {
        ctx.moveTo(cx - half * 0.55, cy - half);
        ctx.lineTo(cx - half * 0.55, cy + half);
        ctx.lineTo(cx + half * 0.9, cy);
        ctx.closePath();
      } else if (type === 3) {
        const inset = symbolSize * 0.1;
        const size = symbolSize - inset;
        ctx.roundRect(
          cx - size / 2,
          cy - size / 2,
          size,
          size,
          Math.max(1.4, size * 0.2),
        );
      } else {
        ctx.moveTo(cx, cy - half);
        ctx.lineTo(cx + half, cy);
        ctx.lineTo(cx, cy + half);
        ctx.lineTo(cx - half, cy);
        ctx.closePath();
      }

      ctx.fill();
    }

    ctx.restore();
  }

  function drawPaperBackdrop(ctx, w, h) {
    const wash = ctx.createLinearGradient(0, 0, 0, h);
    wash.addColorStop(0, "#EEE4D7");
    wash.addColorStop(1, PANEL_BG);
    ctx.fillStyle = wash;
    ctx.fillRect(0, 0, w, h);

    const coolGlow = ctx.createRadialGradient(
      w * 0.8,
      h * 0.18,
      0,
      w * 0.8,
      h * 0.18,
      Math.max(w, h) * 0.75,
    );
    coolGlow.addColorStop(0, "rgba(39, 76, 119, 0.06)");
    coolGlow.addColorStop(1, "rgba(39, 76, 119, 0)");
    ctx.fillStyle = coolGlow;
    ctx.fillRect(0, 0, w, h);
  }

  function drawMiniMazeGuides(ctx, rows, cols, cell, ox, oy) {
    const gw = cols * cell;
    const gh = rows * cell;

    ctx.save();
    ctx.strokeStyle = GRID_FRAME;
    ctx.lineWidth = 1;
    ctx.strokeRect(ox + 0.5, oy + 0.5, gw - 1, gh - 1);

    if (cell >= 9) {
      ctx.strokeStyle = GRID_LINE_MAJOR;
      ctx.lineWidth = 0.8;
      for (let r = 5; r < rows; r += 5) {
        const y = oy + r * cell + 0.5;
        ctx.beginPath();
        ctx.moveTo(ox, y);
        ctx.lineTo(ox + gw, y);
        ctx.stroke();
      }
      for (let c = 5; c < cols; c += 5) {
        const x = ox + c * cell + 0.5;
        ctx.beginPath();
        ctx.moveTo(x, oy);
        ctx.lineTo(x, oy + gh);
        ctx.stroke();
      }
    }
    ctx.restore();
  }

  function makeLowBadge(label, { avgFactor = 0.8 } = {}) {
    return (v, allVals) => {
      if (!(v > 0)) return null;
      const positives = allVals.filter((x) => x > 0);
      if (!positives.length) return null;
      const best = Math.min(...positives);
      const avg = positives.reduce((sum, x) => sum + x, 0) / positives.length;
      const tolerance = Math.max(0.001, best * 0.02);
      const isBest = Math.abs(v - best) <= tolerance;
      const standsOut = v <= avg * avgFactor;
      return isBest && standsOut ? label : null;
    };
  }

  function raceGridRows() {
    return raceState()?.rows || 22;
  }

  function raceGridCols() {
    return raceState()?.cols || 30;
  }

  function raceSpeed() {
    return raceState()?.speed || 20;
  }

  function resultsSignature(results) {
    if (!results) return null;
    return JSON.stringify(
      results.map((item) => [
        item.alg_idx,
        item.found,
        item.nodes,
        item.path,
        item.cost,
        item.time,
        item.iterations,
        item.peak_memory,
      ]),
    );
  }

  function refreshRaceViewport(force = false) {
    const dpr = window.devicePixelRatio || 1;
    if (!force && Math.abs(dpr - lastDpr) <= 0.001) return;
    lastDpr = dpr;
    racePanelOrder = [];
    lastResultsSignature = null;
    if (state.tab === "race" && state.race) {
      updateUI();
      if (!raceRafId) raceRafId = requestAnimationFrame(renderRace);
    }
  }

  function getRaceStatus(race) {
    if (!race) return "Idle";
    if (race.running) return "Running";
    if (race.paused && !race.done) return "Paused";
    if (race.done) return "Completed";
    if (race.order.length >= 2) return "Ready";
    return "Awaiting selection";
  }

  function getSelectionNote(race) {
    const selected = race.order.length;
    if (selected < 2) return "Select at least two algorithms to begin a race.";
    if (race.running) return `Race in progress across ${selected} runners.`;
    if (race.paused && !race.done)
      return "Race paused. Continue or use step controls to inspect progress.";
    if (race.done) return "Race finished. Comparative charts and tables are available below.";
    return `Ready to benchmark ${selected} algorithms on the active grid.`;
  }

  function updateRaceAnimations(idx, runnerData, gridCols = raceGridCols()) {
    if (!runnerData?.grid) return;

    const { grid, path } = runnerData;
    const prev = prevRaceGrids.get(idx);
    if (!prev || prev.length !== grid.length) {
      prevRaceGrids.set(idx, grid.slice());
      return;
    }
    const now = performance.now();
    let animMap = raceAnimCells.get(idx);
    if (!animMap) {
      animMap = new Map();
      raceAnimCells.set(idx, animMap);
    }

    const pathIdx = new Map();
    (path || []).forEach(([r, c], i) => pathIdx.set(`${r},${c}`, i));
    const changedCells = [];
    let pathDelayBase = Infinity;

    for (let i = 0; i < grid.length; i++) {
      if (prev[i] === grid[i]) continue;
      const r = Math.floor(i / gridCols);
      const c = i % gridCols;
      const key = `${r},${c}`;
      changedCells.push({ i, r, c, key });
      if (grid[i] === 6) {
        pathDelayBase = Math.min(pathDelayBase, pathIdx.get(key) ?? 0);
      }
    }

    if (!changedCells.length) {
      prevRaceGrids.set(idx, grid.slice());
      return;
    }

    changedCells.forEach(({ i, key }) => {
      if (grid[i] === 6) {
        const delay =
          Math.max(
            0,
            (pathIdx.get(key) ?? 0) -
              (Number.isFinite(pathDelayBase) ? pathDelayBase : 0),
          ) * uiConfig.pathAnimationStepDelayMs;
        animMap.set(key, {
          kind: "path",
          from: prev[i] === 0 ? 4 : prev[i],
          to: 6,
          startTime: now + delay,
          duration: uiConfig.pathAnimationDurationMs,
        });
        return;
      }

      if (grid[i] === 4 || grid[i] === 5) {
        animMap.set(key, {
          kind: "pulse",
          from: prev[i],
          to: grid[i],
          startTime: now,
          duration: 180,
        });
        return;
      }

      animMap.delete(key);
    });
    prevRaceGrids.set(idx, grid.slice());
  }

  function getRunnerBadgeState(runnerData) {
    if (!runnerData?.done || !runnerData.stats) return null;
    const timeMs = (runnerData.stats.time * 1000).toFixed(2);
    return {
      text: `Done / ${timeMs} ms`,
      background: runnerData.stats.found ? BADGE_SUCCESS_BG : BADGE_FAILURE_BG,
    };
  }

  function applyRunnerBadge(badge, runnerData) {
    if (!badge) return;

    const badgeState = getRunnerBadgeState(runnerData);
    if (!badgeState) {
      badge.textContent = "";
      badge.style.background = "";
      badge.style.display = "none";
      return;
    }

    badge.textContent = badgeState.text;
    badge.style.background = badgeState.background;
    badge.style.display = "block";
  }

  function getRacePanelLayout(count, containerWidth) {
    const cols =
      count >= 7 ? 4 : count >= 5 ? 3 : count >= 3 ? 2 : Math.max(count, 1);
    const safeWidth = Math.max(320, containerWidth || 0);
    const panelW = Math.max(
      220,
      Math.floor((safeWidth - PANEL_GAP * (cols - 1)) / cols),
    );
    const mazeAspect = raceGridRows() / raceGridCols();
    const maxCanvasH =
      count >= 7 ? 186 : count >= 5 ? 220 : count >= 3 ? 268 : 340;
    const canvasH = Math.max(
      count >= 7 ? 156 : 170,
      Math.min(maxCanvasH, Math.round(panelW * mazeAspect)),
    );

    return {
      cols,
      panelH: Math.max(PANEL_MIN_H, canvasH + PANEL_HEADER_H),
      canvasH,
    };
  }

  function syncRacePanel(panel, idx, runnerData, canvasH) {
    if (!panel) return;

    const canvas = panel.querySelector(".panel-canvas");
    const badge = panel.querySelector(".panel-badge");
    if (canvas) canvas.style.height = `${canvasH}px`;
    if (runnerData) updateRaceAnimations(idx, runnerData);
    applyRunnerBadge(badge, runnerData);
  }

  function createRacePanel(idx, runnerData, canvasH) {
    const color = colorForAlgo(idx, idx);
    const panel = document.createElement("div");
    panel.className = "race-panel";

    const header = document.createElement("div");
    header.className = "panel-header";
    header.style.backgroundColor = color;
    header.textContent = runnerData.name;

    const canvas = document.createElement("canvas");
    canvas.className = "panel-canvas";

    const badge = document.createElement("div");
    badge.className = "panel-badge";

    panel.appendChild(header);
    panel.appendChild(canvas);
    panel.appendChild(badge);

    syncRacePanel(panel, idx, runnerData, canvasH);
    drawMiniMaze(canvas, runnerData, idx);
    return panel;
  }

  function buildComparisonTable(results) {
    const el = $("race-comparison-table");
    if (!el || !results || !results.length) return;
    el.style.minHeight = `${Math.max(580, 184 + results.length * 62)}px`;

    const foundResults = results.filter((d) => d.found);
    const minCost = foundResults.length
      ? Math.min(...foundResults.map((d) => d.cost))
      : null;

    function isBestVal(vals, v) {
      if (!(v > 0)) return false;
      const pos = vals.filter((x) => x > 0);
      if (!pos.length) return false;
      const best = Math.min(...pos);
      const max = Math.max(...pos);
      if (Math.abs(max - best) <= Math.max(0.001, best * 0.02)) return false;
      return Math.abs(v - best) <= Math.max(0.001, best * 0.02);
    }

    function isOptimal(d) {
      if (!d.found || minCost === null) return false;
      return Math.abs(d.cost - minCost) <= Math.max(0.001, Math.abs(minCost) * 0.02);
    }

    function fmtTime(ms) {
      return ms < 1 ? `${ms.toFixed(2)} ms` : `${ms.toFixed(1)} ms`;
    }

    function cell(val, best) {
      return `<td${best ? ' class="cmp-best"' : ""}>${val}</td>`;
    }

    const foundNodes = foundResults.map((d) => d.nodes);
    const foundPath = foundResults.map((d) => d.path);
    const foundCost = foundResults.map((d) => d.cost);
    const foundTime = foundResults.map((d) => d.time * 1000);
    const foundIter = foundResults.map((d) => d.iterations);
    const foundMem = foundResults.map((d) => d.peak_memory);

    const rows = results.map((d, i) => {
      const color = BAR_PAL[(d.alg_idx ?? i) % BAR_PAL.length];
      const dot = `<span class="cmp-dot" style="background:${color}"></span>`;

      if (!d.found) {
        return `<tr>
          <td class="cmp-alg-cell">${dot}${shortAlgName(d.name)}</td>
          <td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td>
          <td class="cmp-optimal-na">-</td>
        </tr>`;
      }

      const timeMs = d.time * 1000;
      const optimal = isOptimal(d);

      return `<tr>
        <td class="cmp-alg-cell">${dot}${shortAlgName(d.name)}</td>
        ${cell(Math.round(d.nodes).toLocaleString(), isBestVal(foundNodes, d.nodes))}
        ${cell(d.path, isBestVal(foundPath, d.path))}
        ${cell(d.cost, isBestVal(foundCost, d.cost))}
        ${cell(fmtTime(timeMs), isBestVal(foundTime, timeMs))}
        ${cell(d.iterations, isBestVal(foundIter, d.iterations))}
        ${cell(
          d.peak_memory > 0 ? Math.round(d.peak_memory).toLocaleString() : "-",
          isBestVal(foundMem, d.peak_memory),
        )}
        <td class="${optimal ? "cmp-optimal-yes" : "cmp-optimal-no"}">${optimal ? "Yes" : "No"}</td>
      </tr>`;
    });

    el.innerHTML = `
      <div class="cmp-shell">
        <div class="cmp-header-row">
          <div>
            <p class="cmp-kicker">Comparative Summary</p>
            <h3>Result Matrix</h3>
          </div>
          <p class="cmp-note">
            Green cells indicate the best value among algorithms that reached the goal.
          </p>
        </div>
        <div class="cmp-scroll">
          <table class="cmp-table">
            <thead>
              <tr>
                <th>Algorithm</th>
                <th>Nodes</th>
                <th>Path Len</th>
                <th>Cost</th>
                <th>Time</th>
                <th>Iterations</th>
                <th>Peak Memory</th>
                <th>Optimal</th>
              </tr>
            </thead>
            <tbody>${rows.join("")}</tbody>
          </table>
        </div>
        <div class="cmp-footnote">
          Optimal means minimum path cost in this race. <span class="cmp-green">Green</span> marks the best value.
        </div>
      </div>
    `;
  }

  function drawRaceCharts(results) {
    const charts = [
      {
        id: "chart-nodes",
        key: "nodes",
        title: "Nodes Visited",
        opts: { badge: makeLowBadge("Efficient", { avgFactor: 0.88 }) },
      },
      {
        id: "chart-path",
        key: "path",
        title: "Path Length",
        opts: { badge: makeLowBadge("Shortest", { avgFactor: 0.9 }) },
      },
      {
        id: "chart-cost",
        key: "cost",
        title: "Path Cost",
        opts: { badge: makeLowBadge("Lowest Cost", { avgFactor: 0.9 }) },
      },
      {
        id: "chart-time",
        key: "time",
        title: "Execution Time (ms)",
        opts: { badge: makeLowBadge("Fastest", { avgFactor: 0.86 }) },
      },
      {
        id: "chart-iterations",
        key: "iterations",
        title: "Iterations",
        opts: {
          formatValue: (v) => `${Math.round(v)}`,
          badge: makeLowBadge("Fewest", { avgFactor: 0.8 }),
        },
      },
      {
        id: "chart-memory",
        key: "peak_memory",
        title: "Peak Memory (nodes)",
        opts: {
          formatValue: (v) => (v === 0 ? "-" : `${Math.round(v)}`),
          badge: makeLowBadge("Low Memory", { avgFactor: 0.75 }),
        },
      },
    ];

    buildComparisonTable(results);
    charts.forEach(({ id, key, title, opts }) => {
      drawChart($(id), results, key, title, opts);
    });
    drawRadarChart($("chart-radar"), results);
    drawFrontierChart($("chart-frontier"), results);
    drawTradeoffChart($("chart-tradeoff"), results);
    drawHeatmapChart($("chart-heatmap"), results);
  }

  function renderRace() {
    raceRafId = null;
    if (state.tab !== "race") return;
    const race = raceState();
    if (!race || race.order.length === 0) return;

    const container = $("race-panels");
    race.order.forEach((idx, i) => {
      const panel = container.children[i];
      if (!panel) return;
      const canvas = panel.querySelector(".panel-canvas");
      const runnerData = race.runners[idx];
      if (canvas && runnerData) drawMiniMaze(canvas, runnerData, idx);
    });

    let cont = race.running;
    if (!cont) {
      const now = performance.now();
      outer: for (const animMap of raceAnimCells.values()) {
        for (const anim of animMap.values()) {
          if (now < anim.startTime + anim.duration) {
            cont = true;
            break outer;
          }
        }
      }
    }
    if (cont) raceRafId = requestAnimationFrame(renderRace);
  }

  function buildRaceToggles() {
    const container = $("race-algos");
    container.innerHTML = "";
    ALG_NAMES.forEach((name, i) => {
      const button = document.createElement("button");
      button.className = "race-toggle";
      button.dataset.idx = i;
      button.title = name;

      const bar = document.createElement("span");
      bar.className = "color-bar";
      bar.style.background = colorForAlgo(i, i);

      const shortName = document.createElement("span");
      shortName.className = "race-toggle-name";
      shortName.textContent = shortAlgName(name);

      const fullName = document.createElement("span");
      fullName.className = "race-toggle-copy";
      fullName.textContent = name;

      button.appendChild(bar);
      button.appendChild(shortName);
      button.appendChild(fullName);
      button.addEventListener("click", () =>
        act({ action: "race_toggle", idx: i }),
      );
      container.appendChild(button);
    });
  }

  function drawMiniMaze(canvas, runnerData, idx) {
    if (!runnerData || !runnerData.grid) return;
    const canvasBox = getCanvasBox(canvas);
    if (!canvasBox) return;
    const { ctx, w, h } = canvasBox;

    const rows = raceGridRows();
    const cols = raceGridCols();
    const cell = Math.max(2, Math.min(Math.floor(w / cols), Math.floor(h / rows)));
    const gw = cols * cell;
    const gh = rows * cell;
    const ox = Math.floor((w - gw) / 2);
    const oy = Math.floor((h - gh) / 2);

    drawPaperBackdrop(ctx, w, h);

    const now = performance.now();
    const animMap = idx !== undefined ? raceAnimCells.get(idx) : null;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const t = runnerData.grid[r * cols + c];
        const x = ox + c * cell;
        const y = oy + r * cell;
        const key = `${r},${c}`;
        const anim = animMap ? animMap.get(key) : null;

        if (anim && cell >= 4) {
          const baseType = CELL_C[anim.from] ? anim.from : 0;
          if (now < anim.startTime) {
            ctx.fillStyle = CELL_C[baseType] || CELL_C[0];
            ctx.fillRect(x, y, cell, cell);
          } else {
            const elapsed = now - anim.startTime;
            const progress = Math.min(elapsed / anim.duration, 1);

            if (anim.kind === "path") {
              if (progress >= 1) animMap.delete(key);
              const c1 = 1.70158;
              const c3 = c1 + 1;
              const scale = Math.max(
                0,
                1 +
                  c3 * Math.pow(progress - 1, 3) +
                  c1 * Math.pow(progress - 1, 2),
              );

              ctx.fillStyle = CELL_C[baseType] || CELL_C[4];
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
                ctx.roundRect(bx, by, s, s, Math.max(2, s * 0.22));
                ctx.fill();
                ctx.restore();
              }
            } else {
              ctx.fillStyle = CELL_C[baseType] || CELL_C[0];
              ctx.fillRect(x, y, cell, cell);
              drawMiniMazeOverlay(
                ctx,
                x,
                y,
                cell,
                CELL_C[anim.to] || CELL_C[t] || CELL_C[0],
                progress,
              );
              if (progress >= 1) animMap.delete(key);
            }
          }
        } else {
          ctx.fillStyle = CELL_C[t] || CELL_C[0];
          ctx.fillRect(x, y, cell, cell);
        }

        drawMarkerAccent(ctx, x, y, cell, t);

        if (cell >= 4) {
          ctx.strokeStyle = GRID_LINE_MINOR;
          ctx.lineWidth = 0.32;
          ctx.strokeRect(x + 0.15, y + 0.15, cell - 0.3, cell - 0.3);
        }
      }
    }

    drawMiniMazeGuides(ctx, rows, cols, cell, ox, oy);
  }

  function drawRadarChart(canvas, data) {
    if (!data || data.length < 2) return;
    const canvasBox = getCanvasBox(canvas, { resizeAlways: true });
    if (!canvasBox) return;
    const { ctx, w, h } = canvasBox;

    ctx.fillStyle = CHART_BG;
    ctx.fillRect(0, 0, w, h);

    ctx.font = `700 10px ${CANVAS_FONT}`;
    ctx.fillStyle = "#8A908E";
    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";
    ctx.fillText("ALGORITHM PROFILE", 18, 22);
    ctx.font = `700 22px ${CANVAS_SERIF}`;
    ctx.fillStyle = "#1F2A36";
    ctx.fillText("Comparative Radar", 18, 46);

    const axes = [
      { key: "time", label: "Speed" },
      { key: "nodes", label: "Node Eff." },
      { key: "peak_memory", label: "Memory" },
      { key: "cost", label: "Path Cost" },
      { key: "iterations", label: "Iterations" },
      { key: "path", label: "Path Length" },
    ];
    const N = axes.length;
    const sideLegend = w >= 620;
    const legendCols = sideLegend && data.length > 4 ? 2 : 1;
    const legendRows = Math.ceil(data.length / legendCols);
    const legendItemW = sideLegend ? 108 : 124;
    const legendRowH = 22;
    const legendGapX = 10;
    const legendPad = 12;
    const legendBoxW =
      legendCols * legendItemW + (legendCols - 1) * legendGapX + legendPad * 2;
    const legendBoxH = legendRows * legendRowH + legendPad * 2 + 4;
    const topPad = 72;
    const leftPad = 56;
    const rightPad = sideLegend ? legendBoxW + 34 : 48;
    const bottomPad = sideLegend ? 34 : legendBoxH + 22;
    const chartW = Math.max(220, w - leftPad - rightPad);
    const chartH = Math.max(220, h - topPad - bottomPad);
    const cx = leftPad + chartW / 2;
    const cy = topPad + chartH / 2 + 4;
    const labelOffset = 24;
    const radius = Math.max(
      84,
      Math.min(chartW / 2 - labelOffset, chartH / 2 - labelOffset),
    );

    const rawVals = data.map((d) =>
      axes.map((ax) => {
        if (!d.found) return 0;
        const v = ax.key === "time" ? (d[ax.key] || 0) * 1000 : d[ax.key] || 0;
        return v;
      }),
    );

    const scores = rawVals.map((vals, di) => {
      if (!data[di].found) return axes.map(() => 0);
      return axes.map((_ax, ai) => {
        const v = vals[ai];
        if (v === 0) return 0;
        const allFound = rawVals
          .filter((_, i) => data[i].found)
          .map((rv) => rv[ai]);
        const nonZero = allFound.filter((x) => x > 0);
        if (!nonZero.length) return 0;
        const best = Math.min(...nonZero);
        return Math.min(1, best / v);
      });
    });

    const buildRadarPoints = (sc) =>
      sc.map((s, i) => {
        const angle = (Math.PI * 2 * i) / N - Math.PI / 2;
        const r = s * radius;
        return {
          x: cx + r * Math.cos(angle),
          y: cy + r * Math.sin(angle),
          score: s,
        };
      });

    const traceRadarPath = (points) => {
      if (!points.length) return;
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      for (let i = 1; i < points.length; i++) {
        ctx.lineTo(points[i].x, points[i].y);
      }
      ctx.lineTo(points[0].x, points[0].y);
      ctx.closePath();
    };

    const levels = 4;
    for (let l = levels; l >= 1; l--) {
      const r = (radius * l) / levels;
      ctx.beginPath();
      for (let i = 0; i < N; i++) {
        const angle = (Math.PI * 2 * i) / N - Math.PI / 2;
        const x = cx + r * Math.cos(angle);
        const y = cy + r * Math.sin(angle);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.strokeStyle = l === levels ? "#C7BFB0" : "#DED5C6";
      ctx.lineWidth = l === levels ? 2.2 : 1.35;
      ctx.stroke();
      if (l % 2 === 0) {
        ctx.fillStyle = "rgba(31, 42, 54, 0.02)";
        ctx.fill();
      }
    }

    axes.forEach((ax, i) => {
      const angle = (Math.PI * 2 * i) / N - Math.PI / 2;
      const ex = cx + radius * Math.cos(angle);
      const ey = cy + radius * Math.sin(angle);
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(ex, ey);
      ctx.strokeStyle = "#D3CABC";
      ctx.lineWidth = 1.4;
      ctx.stroke();

      const lx = cx + (radius + 22) * Math.cos(angle);
      const ly = cy + (radius + 22) * Math.sin(angle);
      const cosA = Math.cos(angle);
      const sinA = Math.sin(angle);
      ctx.font = `700 12px ${CANVAS_FONT}`;
      ctx.fillStyle = "#5D6672";
      ctx.textAlign = Math.abs(cosA) < 0.15 ? "center" : cosA > 0 ? "left" : "right";
      ctx.textBaseline = sinA < -0.4 ? "bottom" : sinA > 0.4 ? "top" : "middle";
      ctx.fillText(ax.label, lx, ly);
    });

    data.forEach((d, di) => {
      const sc = scores[di];
      const color = BAR_PAL[(d.alg_idx ?? di) % BAR_PAL.length];
      const points = buildRadarPoints(sc);

      traceRadarPath(points);
      ctx.save();
      ctx.globalAlpha = 0.14;
      ctx.fillStyle = color;
      ctx.fill();
      ctx.restore();

      traceRadarPath(points);
      ctx.save();
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      ctx.miterLimit = 2;
      ctx.strokeStyle = color;
      ctx.lineWidth = 3.4;
      ctx.stroke();
      ctx.restore();

      points.forEach(({ x, y, score }) => {
        if (score === 0) return;
        ctx.beginPath();
        ctx.arc(x, y, 4.6, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = "#FFFFFF";
        ctx.stroke();
      });
    });

    const legendStartX = sideLegend
      ? w - legendBoxW - 18 + legendPad
      : Math.max(18, Math.floor((w - legendBoxW) / 2) + legendPad);
    const legendStartY = sideLegend ? 20 + legendPad + 2 : h - legendBoxH + legendPad + 2;

    ctx.save();
    ctx.fillStyle = "rgba(255, 255, 255, 0.86)";
    ctx.strokeStyle = "rgba(31, 42, 54, 0.08)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(
      legendStartX - legendPad,
      legendStartY - legendPad - 2,
      legendBoxW,
      legendBoxH,
      14,
    );
    ctx.fill();
    ctx.stroke();
    ctx.restore();

    data.forEach((d, di) => {
      const color = BAR_PAL[(d.alg_idx ?? di) % BAR_PAL.length];
      const col = di % legendCols;
      const row = Math.floor(di / legendCols);
      const legX = legendStartX + col * (legendItemW + legendGapX);
      const legY = legendStartY + row * legendRowH;

      ctx.beginPath();
      ctx.roundRect(legX, legY - 5, 12, 10, 3);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.font = `700 11px ${CANVAS_FONT}`;
      ctx.fillStyle = d.found ? "#1F2A36" : "#8A908E";
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(shortAlgName(d.name), legX + 18, legY);
    });
  }

  function rectsOverlap(a, b) {
    return (
      a.x < b.x + b.w &&
      a.x + a.w > b.x &&
      a.y < b.y + b.h &&
      a.y + a.h > b.y
    );
  }

  function measureLabelRect(x, y, width, height, align, baseline, pad = 4) {
    const left =
      align === "right" ? x - width : align === "center" ? x - width / 2 : x;
    const top =
      baseline === "bottom"
        ? y - height
        : baseline === "middle"
          ? y - height / 2
          : y;
    return {
      x: left - pad,
      y: top - pad,
      w: width + pad * 2,
      h: height + pad * 2,
    };
  }

  function placeScatterLabel(x, y, r, textWidth, bounds, occupiedRects) {
    const labelH = 12;
    const candidates = [
      { align: "left", baseline: "bottom", x: x + r + 8, y: y - r - 8 },
      { align: "left", baseline: "top", x: x + r + 8, y: y + r + 8 },
      { align: "right", baseline: "bottom", x: x - r - 8, y: y - r - 8 },
      { align: "right", baseline: "top", x: x - r - 8, y: y + r + 8 },
      { align: "center", baseline: "bottom", x, y: y - r - 10 },
      { align: "center", baseline: "top", x, y: y + r + 10 },
    ];

    for (const candidate of candidates) {
      const rect = measureLabelRect(
        candidate.x,
        candidate.y,
        textWidth,
        labelH,
        candidate.align,
        candidate.baseline,
      );
      const insideBounds =
        rect.x >= bounds.left &&
        rect.x + rect.w <= bounds.right &&
        rect.y >= bounds.top &&
        rect.y + rect.h <= bounds.bottom;
      if (!insideBounds) continue;
      if (occupiedRects.some((box) => rectsOverlap(rect, box))) continue;
      return { ...candidate, rect };
    }

    const fallbackRect = {
      x: Math.min(
        Math.max(x - textWidth / 2 - 4, bounds.left),
        bounds.right - textWidth - 8,
      ),
      y: Math.min(
        Math.max(y + r + 8, bounds.top),
        bounds.bottom - labelH - 8,
      ),
      w: textWidth + 8,
      h: labelH + 8,
    };
    return {
      align: "left",
      baseline: "top",
      x: fallbackRect.x + 4,
      y: fallbackRect.y + 4,
      rect: fallbackRect,
    };
  }

  function drawFrontierChart(canvas, data) {
    if (!data || !data.length) return;
    const canvasBox = getCanvasBox(canvas, { resizeAlways: true });
    if (!canvasBox) return;
    const { ctx, w, h } = canvasBox;

    ctx.fillStyle = CHART_BG;
    ctx.fillRect(0, 0, w, h);

    ctx.font = `700 10px ${CANVAS_FONT}`;
    ctx.fillStyle = "#8A908E";
    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";
    ctx.fillText("TRADE-OFF VIEW", 18, 22);
    ctx.font = `700 22px ${CANVAS_SERIF}`;
    ctx.fillStyle = "#1F2A36";
    ctx.fillText("Efficiency Frontier", 18, 46);
    ctx.font = `600 12px ${CANVAS_FONT}`;
    ctx.fillStyle = "#5D6672";
    ctx.fillText("Lower-left is better. Bubble size reflects peak memory.", 18, 66);

    const scaleBox = {
      x: Math.max(18, w - 154),
      y: 16,
      w: 136,
      h: 52,
    };
    ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
    ctx.strokeStyle = "rgba(31, 42, 54, 0.08)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(scaleBox.x, scaleBox.y, scaleBox.w, scaleBox.h, 12);
    ctx.fill();
    ctx.stroke();

    ctx.font = `700 10px ${CANVAS_FONT}`;
    ctx.fillStyle = "#8A908E";
    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";
    ctx.fillText("MEMORY SCALE", scaleBox.x + 12, scaleBox.y + 18);

    [0.35, 0.68, 1].forEach((ratio, i) => {
      const cx = scaleBox.x + 38 + i * 34;
      const cy = scaleBox.y + 36;
      const rr = 4 + ratio * 8;
      ctx.save();
      ctx.globalAlpha = 0.16;
      ctx.fillStyle = "#5D6672";
      ctx.beginPath();
      ctx.arc(cx, cy, rr, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
      ctx.beginPath();
      ctx.arc(cx, cy, rr, 0, Math.PI * 2);
      ctx.strokeStyle = "#6D7681";
      ctx.lineWidth = 1.2;
      ctx.stroke();
    });

    const pts = data.map((d, i) => ({
      index: i,
      name: shortAlgName(d.name),
      color: colorForAlgo(d.alg_idx, i),
      found: d.found !== false,
      timeMs: Math.max(0.05, (d.time || 0) * 1000),
      nodes: Math.max(0, d.nodes || 0),
      memory: Math.max(0, d.peak_memory || 0),
    }));

    const ml = 64;
    const mr = 26;
    const mt = 92;
    const mb = 46;
    const cw = Math.max(220, w - ml - mr);
    const ch = Math.max(180, h - mt - mb);
    const left = ml;
    const top = mt;
    const right = left + cw;
    const bottom = top + ch;

    const xLogs = pts.map((p) => Math.log10(p.timeMs + 1));
    const yVals = pts.map((p) => p.nodes);
    const memVals = pts.map((p) => p.memory);
    const xMin = Math.min(...xLogs);
    const xMax = Math.max(...xLogs, xMin + 0.25);
    const yMin = Math.min(...yVals);
    const yMax = Math.max(...yVals, yMin + 1);
    const memMax = Math.max(...memVals, 1);

    const xPos = (timeMs) =>
      left +
      ((Math.log10(timeMs + 1) - xMin) / Math.max(0.001, xMax - xMin)) * cw;
    const yPos = (nodes) =>
      bottom -
      ((nodes - yMin) / Math.max(1, yMax - yMin)) * ch;
    const bubbleR = (memory) => 6 + (memory / memMax) * 10;

    ctx.fillStyle = "rgba(47, 107, 79, 0.05)";
    ctx.fillRect(left, top + ch * 0.55, cw * 0.42, ch * 0.45);

    for (let i = 0; i <= 4; i++) {
      const y = top + (ch * i) / 4;
      ctx.strokeStyle = i === 4 ? "#C7BFB0" : "#DED5C6";
      ctx.lineWidth = i === 4 ? 1.8 : 1;
      ctx.beginPath();
      ctx.moveTo(left, y);
      ctx.lineTo(right, y);
      ctx.stroke();

      const val = Math.round(yMax - ((yMax - yMin) * i) / 4);
      ctx.font = `600 11px ${CANVAS_FONT}`;
      ctx.fillStyle = "#68717C";
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(`${val}`, left - 10, y);
    }

    for (let i = 0; i <= 4; i++) {
      const t = xMin + ((xMax - xMin) * i) / 4;
      const x = left + (cw * i) / 4;
      ctx.strokeStyle = i === 0 ? "#C7BFB0" : "#E1D9CB";
      ctx.lineWidth = i === 0 ? 1.8 : 1;
      ctx.beginPath();
      ctx.moveTo(x, top);
      ctx.lineTo(x, bottom);
      ctx.stroke();

      const ms = Math.max(0, Math.pow(10, t) - 1);
      ctx.font = `600 11px ${CANVAS_FONT}`;
      ctx.fillStyle = "#68717C";
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillText(ms < 10 ? `${ms.toFixed(1)} ms` : `${Math.round(ms)} ms`, x, bottom + 10);
    }

    ctx.font = `700 11px ${CANVAS_FONT}`;
    ctx.fillStyle = "#5D6672";
    ctx.textAlign = "center";
    ctx.fillText("Execution Time", left + cw / 2, h - 12);

    ctx.save();
    ctx.translate(16, top + ch / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = "center";
    ctx.fillText("Nodes Visited", 0, 0);
    ctx.restore();

    const plottedPts = pts.map((p) => ({
      ...p,
      x: xPos(p.timeMs),
      y: yPos(p.nodes),
      r: bubbleR(p.memory),
    }));

    plottedPts.forEach((p) => {
      const { x, y, r } = p;

      ctx.save();
      ctx.globalAlpha = p.found ? 0.2 : 0.08;
      ctx.fillStyle = p.color;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.lineWidth = 2;
      ctx.strokeStyle = p.color;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(x, y, Math.max(2.8, r * 0.34), 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.fill();
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = "#FFFFFF";
      ctx.stroke();
    });

    ctx.font = `700 11px ${CANVAS_FONT}`;
    ctx.fillStyle = "#24313E";
    const labelBounds = {
      left: left + 4,
      right: right - 4,
      top: top + 4,
      bottom: bottom - 4,
    };
    const occupiedLabelRects = [];
    [...plottedPts]
      .sort((a, b) => a.y - b.y || a.x - b.x)
      .forEach((p) => {
        const labelWidth = ctx.measureText(p.name).width;
        const placement = placeScatterLabel(
          p.x,
          p.y,
          p.r,
          labelWidth,
          labelBounds,
          occupiedLabelRects,
        );
        occupiedLabelRects.push(placement.rect);
        ctx.textAlign = placement.align;
        ctx.textBaseline = placement.baseline;
        ctx.fillText(p.name, placement.x, placement.y);
      });
  }

  function drawTradeLegend(ctx, boxX, boxY, boxW, boxH, timeColor, memoryColor) {
    ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
    ctx.strokeStyle = "rgba(31, 42, 54, 0.08)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(boxX, boxY, boxW, boxH, 12);
    ctx.fill();
    ctx.stroke();

    ctx.font = `700 10px ${CANVAS_FONT}`;
    ctx.fillStyle = "#8A908E";
    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";
    ctx.fillText("LEGEND", boxX + 12, boxY + 18);

    const items = [
      { label: "Time", color: timeColor, y: boxY + 32 },
      { label: "Memory", color: memoryColor, y: boxY + 32 },
    ];
    const innerPad = 16;
    const itemGap = 18;
    ctx.font = `700 11px ${CANVAS_FONT}`;
    const itemWidths = items.map((item) => 20 + ctx.measureText(item.label).width);
    let cursorX = boxX + innerPad;
    const maxStartX = boxX + Math.max(innerPad, boxW - innerPad - (itemWidths[1] || 0));

    items.forEach((item, i) => {
      const ix = i === 0 ? cursorX : Math.min(cursorX, maxStartX);
      ctx.strokeStyle = item.color;
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.moveTo(ix, item.y);
      ctx.lineTo(ix + 14, item.y);
      ctx.stroke();

      ctx.fillStyle = "#FFFFFF";
      ctx.beginPath();
      ctx.arc(ix + 7, item.y, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      ctx.font = `700 11px ${CANVAS_FONT}`;
      ctx.fillStyle = item.color;
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(item.label, ix + 20, item.y);
      cursorX = ix + itemWidths[i] + itemGap;
    });
  }

  function drawTradeoffChart(canvas, data) {
    if (!data || !data.length) return;
    const canvasBox = getCanvasBox(canvas, { resizeAlways: true });
    if (!canvasBox) return;
    const { ctx, w, h } = canvasBox;

    ctx.fillStyle = CHART_BG;
    ctx.fillRect(0, 0, w, h);

    ctx.font = `700 10px ${CANVAS_FONT}`;
    ctx.fillStyle = "#8A908E";
    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";
    ctx.fillText("BALANCE VIEW", 18, 22);
    ctx.font = `700 22px ${CANVAS_SERIF}`;
    ctx.fillStyle = "#1F2A36";
    ctx.fillText("Time / Memory Trade-Off", 18, 46);
    ctx.font = `600 12px ${CANVAS_FONT}`;
    ctx.fillStyle = "#5D6672";
    ctx.fillText("Each row compares normalized time and memory. Further left is better.", 18, 66);

    const rows = data.map((d, i) => ({
      name: shortAlgName(d.name),
      color: colorForAlgo(d.alg_idx, i),
      time: Math.max(0.05, (d.time || 0) * 1000),
      memory: Math.max(0, d.peak_memory || 0),
      found: d.found !== false,
    }));

    const times = rows.map((r) => Math.log10(r.time + 1));
    const mems = rows.map((r) => r.memory);
    const minTime = Math.min(...times);
    const maxTime = Math.max(...times, minTime + 0.25);
    const minMem = Math.min(...mems);
    const maxMem = Math.max(...mems, minMem + 1);

    const ml = 110;
    const mr = 28;
    const mt = 102;
    const mb = 38;
    const cw = Math.max(220, w - ml - mr);
    const ch = Math.max(180, h - mt - mb);
    const left = ml;
    const right = left + cw;
    const top = mt;
    const rowGap = ch / Math.max(rows.length, 1);
    const timeX = (v) =>
      left + ((Math.log10(v + 1) - minTime) / Math.max(0.001, maxTime - minTime)) * cw;
    const memX = (v) =>
      left + ((v - minMem) / Math.max(1, maxMem - minMem)) * cw;
    const timeColor = "#C65B3A";
    const memoryColor = "#2C98A0";

    drawTradeLegend(
      ctx,
      Math.max(18, w - 188),
      16,
      170,
      52,
      timeColor,
      memoryColor,
    );

    ctx.strokeStyle = "#D7CEBF";
    ctx.lineWidth = 1.2;
    for (let i = 0; i <= 4; i++) {
      const x = left + (cw * i) / 4;
      ctx.beginPath();
      ctx.moveTo(x, top);
      ctx.lineTo(x, top + ch);
      ctx.stroke();
    }

    ctx.font = `700 11px ${CANVAS_FONT}`;
    ctx.fillStyle = "#5D6672";
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    ctx.fillText("Better", left, top - 18);
    ctx.textAlign = "right";
    ctx.fillText("Heavier", right, top - 18);

    rows.forEach((row, i) => {
      const y = top + rowGap * (i + 0.5);
      const xt = timeX(row.time);
      const xm = memX(row.memory);

      ctx.strokeStyle = "rgba(31, 42, 54, 0.08)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(left, y);
      ctx.lineTo(right, y);
      ctx.stroke();

      ctx.font = `700 11px ${CANVAS_FONT}`;
      ctx.fillStyle = row.color;
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(row.name, 18, y);

      ctx.strokeStyle = row.color;
      ctx.globalAlpha = row.found ? 0.5 : 0.18;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(xt, y);
      ctx.lineTo(xm, y);
      ctx.stroke();
      ctx.globalAlpha = 1;

      ctx.fillStyle = "#FFFFFF";
      ctx.strokeStyle = timeColor;
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.arc(xt, y, 7, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = "#FFFFFF";
      ctx.strokeStyle = memoryColor;
      ctx.beginPath();
      ctx.arc(xm, y, 7, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    });
  }

  function drawHeatmapChart(canvas, data) {
    if (!data || !data.length) return;
    const canvasBox = getCanvasBox(canvas, { resizeAlways: true });
    if (!canvasBox) return;
    const { ctx, w, h } = canvasBox;

    ctx.fillStyle = CHART_BG;
    ctx.fillRect(0, 0, w, h);

    ctx.font = `700 10px ${CANVAS_FONT}`;
    ctx.fillStyle = "#8A908E";
    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";
    ctx.fillText("RANK HEATMAP", 18, 22);
    ctx.font = `700 22px ${CANVAS_SERIF}`;
    ctx.fillStyle = "#1F2A36";
    ctx.fillText("Metric Heatmap", 18, 46);
    ctx.font = `600 12px ${CANVAS_FONT}`;
    ctx.fillStyle = "#5D6672";
    ctx.fillText("Darker cells indicate stronger rank on that metric.", 18, 66);

    const metrics = [
      { key: "time", label: "Time", value: (d) => Math.max(0.05, (d.time || 0) * 1000) },
      { key: "nodes", label: "Nodes", value: (d) => d.nodes || 0 },
      { key: "cost", label: "Cost", value: (d) => d.cost || 0 },
      { key: "path", label: "Path", value: (d) => d.path || 0 },
      { key: "iterations", label: "Iter", value: (d) => d.iterations || 0 },
      { key: "peak_memory", label: "Mem", value: (d) => d.peak_memory || 0 },
    ];

    const rankMaps = {};
    metrics.forEach((metric) => {
      const ranked = data
        .map((d, i) => ({ i, found: d.found !== false, val: metric.value(d) }))
        .filter((item) => item.found)
        .sort((a, b) => a.val - b.val);
      const rankMap = new Map();
      ranked.forEach((item, idx) => rankMap.set(item.i, idx + 1));
      rankMaps[metric.key] = rankMap;
    });

    const ml = 90;
    const mr = 18;
    const mt = 104;
    const mb = 26;
    const gridW = Math.max(220, w - ml - mr);
    const gridH = Math.max(180, h - mt - mb);
    const cellW = gridW / metrics.length;
    const cellH = gridH / data.length;

    metrics.forEach((metric, ci) => {
      const x = ml + ci * cellW;
      ctx.font = `700 11px ${CANVAS_FONT}`;
      ctx.fillStyle = "#68717C";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(metric.label, x + cellW / 2, mt - 18);
    });

    data.forEach((d, ri) => {
      const y = mt + ri * cellH;
      ctx.font = `700 11px ${CANVAS_FONT}`;
      ctx.fillStyle = colorForAlgo(d.alg_idx, ri);
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(shortAlgName(d.name), 18, y + cellH / 2);

      metrics.forEach((metric, ci) => {
        const rank = rankMaps[metric.key].get(ri) || null;
        const maxRank = Math.max(1, rankMaps[metric.key].size);
        const score = rank ? 1 - (rank - 1) / Math.max(1, maxRank - 1) : 0;
        const x = ml + ci * cellW + 3;
        const cellInnerW = cellW - 6;
        const cellInnerH = cellH - 6;
        const bg = rank
          ? `rgba(47, 107, 79, ${0.12 + score * 0.3})`
          : "rgba(31, 42, 54, 0.04)";

        ctx.fillStyle = bg;
        ctx.beginPath();
        ctx.roundRect(x, y + 3, cellInnerW, cellInnerH, 8);
        ctx.fill();

        ctx.strokeStyle = "rgba(31, 42, 54, 0.06)";
        ctx.lineWidth = 1;
        ctx.stroke();

        ctx.font = `700 11px ${CANVAS_FONT}`;
        ctx.fillStyle = rank ? "#244F3C" : "#8A908E";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(rank ? `#${rank}` : "-", x + cellInnerW / 2, y + cellH / 2);
      });
    });
  }

  function drawChart(canvas, data, key, title, opts = {}) {
    if (!data || !data.length) return;
    const canvasBox = getCanvasBox(canvas, { resizeAlways: true });
    if (!canvasBox) return;
    const { ctx, w, h } = canvasBox;

    ctx.fillStyle = CHART_BG;
    ctx.fillRect(0, 0, w, h);

    ctx.font = `700 11px ${CANVAS_FONT}`;
    ctx.fillStyle = "#8A908E";
    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";
    ctx.fillText(title.toUpperCase(), 18, 24);

    const ml = 124;
    const mr = 120;
    const mt = 38;
    const mb = 16;
    const cw = w - ml - mr;
    const ch = h - mt - mb;
    const n = data.length;
    const vals = data.map((item) => (key === "time" ? item[key] * 1000 : item[key]));
    const mx = Math.max(...vals) || 1;

    const gap = 10;
    const barH = Math.min(24, Math.max(14, (ch - (n - 1) * gap) / n));
    const startY = mt + (ch - (n * barH + (n - 1) * gap)) / 2;

    for (let i = 0; i < n; i++) {
      const bw = Math.max(4, (cw * vals[i]) / mx);
      const by = startY + i * (barH + gap);
      const color = colorForAlgo(data[i].alg_idx, i);

      ctx.fillStyle = TRACK_BG;
      ctx.beginPath();
      ctx.roundRect(ml, by, cw, barH, 6);
      ctx.fill();

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.roundRect(ml, by, bw, barH, 6);
      ctx.fill();

      ctx.font = `700 12px ${CANVAS_FONT}`;
      ctx.fillStyle = "#1F2A36";
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(shortAlgName(data[i].name), ml - 10, by + barH / 2);

      let valueLabel;
      if (opts.formatValue) {
        valueLabel = opts.formatValue(vals[i], data[i]);
      } else if (key === "time") {
        valueLabel =
          vals[i] < 1 ? `${vals[i].toFixed(2)} ms` : `${vals[i].toFixed(1)} ms`;
      } else {
        valueLabel = `${Math.round(vals[i])}`;
      }
      ctx.font = `600 12px ${CANVAS_FONT}`;
      ctx.fillStyle = "#5D6672";
      ctx.textAlign = "left";
      ctx.fillText(valueLabel, ml + bw + 8, by + barH / 2);

      if (opts.badge) {
        const badgeText = opts.badge(vals[i], vals);
        if (badgeText) {
          const badgePad = 5;
          const badgeH = 14;
          const valueLabelW = (() => {
            ctx.font = `600 12px ${CANVAS_FONT}`;
            const m = ctx.measureText(valueLabel);
            ctx.font = `700 9px ${CANVAS_FONT}`;
            return m.width;
          })();
          const badgeW = ctx.measureText(badgeText).width + badgePad * 2;
          const badgeX = ml + bw + 8 + valueLabelW + 8;
          const badgeY = by + barH / 2 - badgeH / 2;
          ctx.fillStyle = "rgba(47, 107, 79, 0.14)";
          ctx.beginPath();
          ctx.roundRect(badgeX, badgeY, badgeW, badgeH, 4);
          ctx.fill();
          ctx.fillStyle = "#24543D";
          ctx.fillText(badgeText, badgeX + badgePad, by + barH / 2);
        }
      }
    }
    ctx.textBaseline = "alphabetic";
  }

  function buildRacePanels() {
    const race = raceState();
    const container = $("race-panels");
    const order = race.order;
    const n = order.length;

    if (n === 0) {
      container.innerHTML = "";
      container.style.height = "";
      container.style.gridAutoRows = "";
      racePanelOrder = [];
      return;
    }

    const contentEl = $("content-race");
    const containerWidth = container.clientWidth || contentEl.clientWidth;
    const { cols, panelH, canvasH } = getRacePanelLayout(
      n,
      containerWidth,
    );
    container.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
    container.style.gridAutoRows = `${panelH}px`;
    container.style.height = "";
    container.style.flexShrink = "0";

    const key = order.join(",");
    if (key === racePanelOrder.join(",")) {
      order.forEach((idx, i) => {
        const panel = container.children[i];
        if (!panel) return;
        const runnerData = race.runners[idx];
        syncRacePanel(panel, idx, runnerData, canvasH);
      });
      return;
    }
    prevRaceGrids.clear();
    raceAnimCells.clear();
    racePanelOrder = [...order];

    container.innerHTML = "";
    order.forEach((idx) => {
      const runnerData = race.runners[idx];
      if (!runnerData) return;
      container.appendChild(createRacePanel(idx, runnerData, canvasH));
    });
  }

  function updateUI() {
    const race = raceState();
    if (!race) return;

    const selected = new Set(race.order);
    document.querySelectorAll(".race-toggle").forEach((button) => {
      const i = +button.dataset.idx;
      const color = colorForAlgo(i, i);
      if (selected.has(i)) {
        button.classList.add("selected");
        button.style.background = color;
      } else {
        button.classList.remove("selected");
        button.style.background = "";
      }
    });

    const runButton = $("btn-race");
    if (race.running) {
      runButton.textContent = "Pause";
      runButton.className = "btn btn-run pausing";
      runButton.disabled = false;
    } else if (race.paused && !race.done) {
      runButton.textContent = "Continue";
      runButton.className = "btn btn-run btn-continue";
      runButton.disabled = false;
    } else if (race.order.length >= 2) {
      runButton.textContent = "Race";
      runButton.className = "btn btn-run";
      runButton.disabled = false;
    } else {
      runButton.textContent = "Race";
      runButton.className = "btn btn-run";
      runButton.disabled = true;
    }

    const raceActive = race.running || (race.paused && !race.done);
    $("race-btn-step-back").disabled =
      (race.step_ptr ?? -1) < 1 || race.done || race.running;
    $("race-btn-step-fwd").disabled = race.running || race.done;
    $("race-btn-cancel").classList.toggle("hidden", !raceActive && !race.done);
    setText("race-speed-val", race.speed);
    $("race-speed-slider").value = race.speed;

    const selectionCount = race.order.length;
    const selectionNote = getSelectionNote(race);
    setText("race-selection-inline", `${selectionCount} selected`);
    setText(
      "race-selected-count",
      `${selectionCount} ${selectionCount === 1 ? "algorithm" : "algorithms"}`,
    );
    setText("race-grid-summary", `${race.rows} x ${race.cols}`);
    setText("race-speed-summary", `${race.speed}`);
    setText("race-status-summary", getRaceStatus(race));
    setText("race-selection-note", selectionNote);
    $("race-empty-state").classList.toggle("hidden", selectionCount > 0);

    buildRacePanels();

    if (race.results) {
      $("race-charts").classList.remove("hidden");
      const signature = resultsSignature(race.results);
      if (signature !== lastResultsSignature) {
        drawRaceCharts(race.results);
        lastResultsSignature = signature;
      }
    } else {
      $("race-charts").classList.add("hidden");
      lastResultsSignature = null;
    }
  }

  function clearPollTimer() {
    if (pollTimerId !== null) {
      clearTimeout(pollTimerId);
      pollTimerId = null;
    }
  }

  function schedulePoll(delay = uiConfig.pollIntervalMs) {
    clearPollTimer();
    pollTimerId = window.setTimeout(() => {
      pollTimerId = null;
      poll();
    }, delay);
  }

  async function poll() {
    if (state.tab !== "race") return;
    if (pollInFlight) return;
    pollInFlight = true;
    try {
      refreshRaceViewport();
      state.race = await (await fetch("/api/race")).json();
      updateUI();
      if (!raceRafId) raceRafId = requestAnimationFrame(renderRace);
    } catch (error) {
      console.warn("[race] poll failed", error);
    } finally {
      pollInFlight = false;
      if (state.tab === "race") schedulePoll();
    }
  }

  function bindUI() {
    buildRaceToggles();

    $("btn-race").addEventListener("click", () => {
      if (!raceState()) return;
      act({ action: "race_start" });
    });
    $("race-btn-step-back").addEventListener("click", () =>
      act({ action: "race_step_back" }),
    );
    $("race-btn-step-fwd").addEventListener("click", () =>
      act({ action: "race_step" }),
    );
    $("race-btn-cancel").addEventListener("click", () =>
      act({ action: "race_cancel" }),
    );

    $("race-btn-spd-dn").addEventListener("click", () => {
      const v = Math.max(uiConfig.speedMin, raceSpeed() - 1);
      setText("race-speed-val", v);
      $("race-speed-slider").value = v;
      act({ action: "speed", value: v });
    });
    $("race-btn-spd-up").addEventListener("click", () => {
      const v = Math.min(uiConfig.speedMax, raceSpeed() + 1);
      setText("race-speed-val", v);
      $("race-speed-slider").value = v;
      act({ action: "speed", value: v });
    });
    $("race-speed-slider").addEventListener("input", (e) => {
      setText("race-speed-val", e.target.value);
      act({ action: "speed", value: +e.target.value });
    });
  }

  function init() {
    bindUI();
    window.addEventListener("resize", () => {
      refreshRaceViewport(true);
      if (state.tab === "race") poll();
    });
    window.visualViewport?.addEventListener("resize", () => {
      refreshRaceViewport(true);
      if (state.tab === "race") poll();
    });
    window.App.onTabChange((tab) => {
      if (tab === "race") schedulePoll(0);
      else clearPollTimer();
    });
    if (state.tab === "race") schedulePoll(0);
  }

  return { init };
})();
