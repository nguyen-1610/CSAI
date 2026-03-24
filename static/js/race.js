/* Race tab logic */

window.RacePage = (() => {
  const CELL_C = [
    "#FFFFFF",
    "#1C1C1E",
    "#34C759",
    "#FF3B30",
    "#007AFF",
    "#5856D6",
    "#FF9500",
    "#FFD60A",
    "#1B6CA8",
    "#8B5E3C",
    "#8BC34A",
  ];
  const BAR_PAL = [
    "#4B83E0",
    "#2EBF8A",
    "#F5A623",
    "#E05C5C",
    "#9B6FE0",
    "#1AB8C4",
    "#E87D4A",
    "#6BB87A",
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

  const RACE_LAYOUT = {
    panelGap: 10,
    panelMinHeight: 120,
    panelViewportMin: 240,
    panelViewportMax: 460,
    panelViewportRatio: 0.42,
    canvasTrimIdle: 24,
    canvasTrimDone: 42,
    maxCols: 4,
  };

  const RACE_BADGE = {
    success: "#34C759",
    failure: "#FF3B30",
  };

  const RACE_CHART = {
    titleX: 16,
    titleY: 21,
    topPad: 58,
    sidePad: 96,
    legendTopGap: 32,
    legendRowH: 28,
    labelOffset: 34,
    minRadius: 90,
    axisLabelGap: 22,
    ringCount: 4,
    ringOuterStroke: 2.2,
    ringInnerStroke: 1.35,
    axisStroke: 1.5,
    vertexRadius: 6,
    barLeft: 116,
    barRight: 76,
    barTop: 32,
    barBottom: 10,
    barGap: 8,
    barMinH: 14,
    barMaxH: 24,
    barRadius: 5,
    legendMinItem: 180,
    legendLeft: 24,
    legendBottom: 18,
    valueBadgePad: 4,
    valueBadgeH: 13,
    valueBadgeRadius: 4,
  };

  let racePanelOrder = [];
  const prevRaceGrids = new Map();
  const raceAnimCells = new Map();
  let raceRafId = null;

  const { $, act, state } = window.App;

  function raceState() {
    return state.race;
  }

  function shortAlgName(name) {
    return ALG_SHORT[name] || name;
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
    return raceState()?.rows || 28;
  }

  function raceGridCols() {
    return raceState()?.cols || 40;
  }

  function raceSpeed() {
    return raceState()?.speed || 20;
  }

  function racePanelColumns(count) {
    if (count <= 2) return count;
    if (count <= 4) return 2;
    if (count <= 6) return 3;
    return RACE_LAYOUT.maxCols;
  }

  function racePanelSizing(count, viewportH, hasResults) {
    const cols = racePanelColumns(count);
    const rows = Math.ceil(count / cols);
    const gapTotal = Math.max(0, rows - 1) * RACE_LAYOUT.panelGap;
    const sectionH = hasResults
      ? Math.min(
          Math.max(RACE_LAYOUT.panelViewportMin, Math.round(viewportH * RACE_LAYOUT.panelViewportRatio)),
          RACE_LAYOUT.panelViewportMax,
        )
      : viewportH;
    const panelH = Math.max(
      RACE_LAYOUT.panelMinHeight,
      Math.floor((sectionH - gapTotal) / rows),
    );
    const canvasH = Math.max(
      110,
      panelH - (hasResults ? RACE_LAYOUT.canvasTrimDone : RACE_LAYOUT.canvasTrimIdle),
    );
    return { cols, sectionH, canvasH };
  }

  function raceBadgeState(runnerData) {
    if (!runnerData?.done || !runnerData.stats) return null;
    if (runnerData.stats.found) {
      return {
        text: `Path: ${runnerData.stats.path}  |  ${(runnerData.stats.time * 1000).toFixed(2)} ms`,
        color: RACE_BADGE.success,
      };
    }
    return {
      text: "No path found",
      color: RACE_BADGE.failure,
    };
  }

  function applyRaceBadge(badge, runnerData) {
    const badgeState = raceBadgeState(runnerData);
    if (!badgeState) {
      badge.style.display = "none";
      return;
    }
    badge.textContent = badgeState.text;
    badge.style.backgroundColor = badgeState.color;
    badge.style.display = "block";
  }

  function raceBadgeFill(color, alpha = "20") {
    return `${color}${alpha}`;
  }

  function updateRaceAnimations(idx, grid, path, gridCols) {
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

    // Keep loop alive while running or any animation is still in progress.
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
      button.textContent = name;
      button.addEventListener("click", () =>
        act({ action: "race_toggle", idx: i }),
      );
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
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const rows = raceGridRows();
    const cols = raceGridCols();
    const cell = Math.max(
      2,
      Math.min(Math.floor(w / cols), Math.floor(h / rows)),
    );
    const gw = cols * cell;
    const gh = rows * cell;
    const ox = Math.floor((w - gw) / 2);
    const oy = Math.floor((h - gh) / 2);

    ctx.fillStyle = "#F2F2F7";
    ctx.fillRect(0, 0, w, h);

    const now = performance.now();
    const animMap = idx !== undefined ? raceAnimCells.get(idx) : null;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const t = runnerData.grid[r * cols + c];
        const x = ox + c * cell;
        const y = oy + r * cell;
        const key = `${r},${c}`;
        const anim = t === 6 && animMap ? animMap.get(key) : null;

        if (anim && cell >= 4 && now >= anim.startTime) {
          const elapsed = now - anim.startTime;
          const progress = Math.min(elapsed / anim.duration, 1);
          if (progress >= 1) animMap.delete(key);
          const c1 = 1.70158;
          const c3 = c1 + 1;
          const scale = Math.max(
            0,
            1 + c3 * Math.pow(progress - 1, 3) + c1 * Math.pow(progress - 1, 2),
          );

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
          ctx.fillStyle = anim ? CELL_C[4] : CELL_C[t] || CELL_C[0];
          ctx.fillRect(x, y, cell, cell);
        }

        if (cell >= 4) {
          ctx.strokeStyle = "#E5E5EA";
          ctx.lineWidth = 0.3;
          ctx.strokeRect(x + 0.15, y + 0.15, cell - 0.3, cell - 0.3);
        }
      }
    }
  }

  function drawRadarChart(canvas, data) {
    if (!data || data.length < 2) return;
    const dpr = devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    if (!w || !h) return;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    ctx.fillStyle = "#FAFBFF";
    ctx.fillRect(0, 0, w, h);

    // Title
    ctx.font = "700 11px -apple-system, BlinkMacSystemFont, sans-serif";
    ctx.fillStyle = "#8E8E93";
    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";
    ctx.fillText("ALGORITHM PROFILE", RACE_CHART.titleX, RACE_CHART.titleY);

    const axes = [
      { key: "time",         label: "Speed",       invert: true  },
      { key: "nodes",        label: "Node Eff.",    invert: true  },
      { key: "peak_memory",  label: "Memory",       invert: true  },
      { key: "cost",         label: "Path Cost",    invert: true  },
      { key: "iterations",   label: "Iterations",   invert: true  },
      { key: "path",         label: "Path Length",  invert: true  },
    ];
    const N = axes.length;
    const legendCols = w >= 1180 ? 4 : w >= 860 ? 3 : 2;
    const legendRows = Math.ceil(data.length / legendCols);
    const compact = w < 1120 || h < 460;
    const topPad = compact ? 52 : RACE_CHART.topPad;
    const sidePad = compact ? 78 : RACE_CHART.sidePad;
    const legendTopGap = compact ? 24 : RACE_CHART.legendTopGap;
    const legendRowH = compact ? 24 : RACE_CHART.legendRowH;
    const legendAreaH = legendRows * legendRowH;
    const bottomPad = legendAreaH + legendTopGap + 4;
    const chartTop = topPad;
    const chartBottom = h - bottomPad;
    const chartH = Math.max(compact ? 210 : 240, chartBottom - chartTop);
    const cx = w / 2;
    const cy = chartTop + chartH / 2 + (compact ? 4 : 8);
    const labelOffset = compact ? 28 : RACE_CHART.labelOffset;
    const radius = Math.max(
      RACE_CHART.minRadius,
      Math.min(w / 2 - sidePad - labelOffset, chartH / 2 - labelOffset),
    );

    // Compute raw values per algo per axis
    const rawVals = data.map(d =>
      axes.map(ax => {
        if (!d.found) return 0;
        const v = ax.key === "time" ? (d[ax.key] || 0) * 1000 : (d[ax.key] || 0);
        return v;
      })
    );

    // Score: for each axis, score = best/val (so best algo = 1.0, others < 1.0)
    // For memory/iterations where 0 means algo didn't track → treat as best
    const scores = rawVals.map((vals, di) => {
      if (!data[di].found) return axes.map(() => 0);
      return axes.map((_ax, ai) => {
        const v = vals[ai];
        if (v === 0) return 0;
        const allFound = rawVals.filter((_, i) => data[i].found).map(rv => rv[ai]);
        const nonZero = allFound.filter(x => x > 0);
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
      // Explicitly return to the first vertex to avoid any visible seam
      // from anti-aliasing at the closing edge on some displays/projectors.
      ctx.lineTo(points[0].x, points[0].y);
      ctx.closePath();
    };

    // Grid rings (4 levels)
    const levels = RACE_CHART.ringCount;
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
      ctx.strokeStyle = l === levels ? "#D1D1D6" : "#E5E5EA";
      ctx.lineWidth = l === levels ? RACE_CHART.ringOuterStroke : RACE_CHART.ringInnerStroke;
      ctx.stroke();
      if (l % 2 === 0) {
        ctx.fillStyle = "#F2F2F720";
        ctx.fill();
      }
    }

    // Axis lines + labels
    axes.forEach((ax, i) => {
      const angle = (Math.PI * 2 * i) / N - Math.PI / 2;
      const ex = cx + radius * Math.cos(angle);
      const ey = cy + radius * Math.sin(angle);
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(ex, ey);
      ctx.strokeStyle = "#D1D1D6";
      ctx.lineWidth = RACE_CHART.axisStroke;
      ctx.stroke();

      const lx = cx + (radius + RACE_CHART.axisLabelGap) * Math.cos(angle);
      const ly = cy + (radius + RACE_CHART.axisLabelGap) * Math.sin(angle);
      const cosA = Math.cos(angle);
      const sinA = Math.sin(angle);
      ctx.font = "700 13px -apple-system, BlinkMacSystemFont, sans-serif";
      ctx.fillStyle = "#636366";
      ctx.textAlign = Math.abs(cosA) < 0.15 ? "center" : cosA > 0 ? "left" : "right";
      ctx.textBaseline = sinA < -0.4 ? "bottom" : sinA > 0.4 ? "top" : "middle";
      ctx.fillText(ax.label, lx, ly);
    });

    // Draw each algo polygon
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
      ctx.lineWidth = 4.5;
      ctx.stroke();
      ctx.restore();

      // Vertex dots
      points.forEach(({ x, y, score }) => {
        if (score === 0) return;
        ctx.beginPath();
        ctx.arc(x, y, RACE_CHART.vertexRadius, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.lineWidth = 2.5;
        ctx.strokeStyle = "#FFFFFF";
        ctx.stroke();
      });
    });

    // Legend
    const legendItemW = Math.max(
      RACE_CHART.legendMinItem,
      Math.floor((w - sidePad * 2) / legendCols),
    );
    const legendStartX = Math.max(
      RACE_CHART.legendLeft,
      Math.floor((w - legendItemW * legendCols) / 2),
    );
    const legendStartY = h - legendAreaH - RACE_CHART.legendBottom;
    data.forEach((d, di) => {
      const color = BAR_PAL[(d.alg_idx ?? di) % BAR_PAL.length];
      const col = di % legendCols;
      const row = Math.floor(di / legendCols);
      const legX = legendStartX + col * legendItemW;
      const legY = legendStartY + row * legendRowH;

      ctx.beginPath();
      ctx.roundRect(legX, legY - 6, 14, 12, 3);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.font = "700 13px -apple-system, BlinkMacSystemFont, sans-serif";
      ctx.fillStyle = d.found ? "#3A3A3C" : "#8E8E93";
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(shortAlgName(d.name), legX + 20, legY);
    });
  }

  function drawChart(canvas, data, key, title, opts = {}) {
    if (!data || !data.length) return;
    const dpr = devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    ctx.fillStyle = "#FAFBFF";
    ctx.fillRect(0, 0, w, h);

    ctx.font = "700 11px -apple-system, BlinkMacSystemFont, sans-serif";
    ctx.fillStyle = "#8E8E93";
    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";
    ctx.fillText(title.toUpperCase(), RACE_CHART.titleX, RACE_CHART.titleY);

    const ml = RACE_CHART.barLeft;
    const mr = RACE_CHART.barRight;
    const mt = RACE_CHART.barTop;
    const mb = RACE_CHART.barBottom;
    const cw = w - ml - mr;
    const ch = h - mt - mb;
    const n = data.length;
    const vals = data.map((item) =>
      key === "time" ? item[key] * 1000 : item[key],
    );
    const mx = Math.max(...vals) || 1;

    const gap = RACE_CHART.barGap;
    const barH = Math.min(
      RACE_CHART.barMaxH,
      Math.max(RACE_CHART.barMinH, (ch - (n - 1) * gap) / n),
    );
    const startY = mt + (ch - (n * barH + (n - 1) * gap)) / 2;

    for (let i = 0; i < n; i++) {
      const bw = Math.max(4, (cw * vals[i]) / mx);
      const by = startY + i * (barH + gap);
      const color = BAR_PAL[(data[i].alg_idx ?? i) % BAR_PAL.length];

      // background track
      ctx.fillStyle = "#ECEEF5";
      ctx.beginPath();
      ctx.roundRect(ml, by, cw, barH, RACE_CHART.barRadius);
      ctx.fill();

      // colored bar
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.roundRect(ml, by, bw, barH, RACE_CHART.barRadius);
      ctx.fill();

      // name label
      ctx.font = "600 12px -apple-system, BlinkMacSystemFont, sans-serif";
      ctx.fillStyle = "#3A3A3C";
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(shortAlgName(data[i].name), ml - 8, by + barH / 2);

      // value label
      let valueLabel;
      if (opts.formatValue) {
        valueLabel = opts.formatValue(vals[i], data[i]);
      } else if (key === "time") {
        valueLabel =
          vals[i] < 1 ? vals[i].toFixed(2) + " ms" : vals[i].toFixed(1) + " ms";
      } else {
        valueLabel = `${Math.round(vals[i])}`;
      }
      ctx.font = "600 12px -apple-system, BlinkMacSystemFont, sans-serif";
      ctx.fillStyle = "#5D6778";
      ctx.textAlign = "left";
      ctx.fillText(valueLabel, ml + bw + 8, by + barH / 2);

      // optional badge
      if (opts.badge) {
        const badgeText = opts.badge(vals[i], vals);
        if (badgeText) {
          const badgePad = RACE_CHART.valueBadgePad;
          ctx.font = "700 9px -apple-system, BlinkMacSystemFont, sans-serif";
          ctx.textAlign = "left";
          ctx.textBaseline = "middle";
          const valueLabelW = (() => {
            ctx.font = "600 12px -apple-system, BlinkMacSystemFont, sans-serif";
            const m = ctx.measureText(valueLabel);
            ctx.font = "700 9px -apple-system, BlinkMacSystemFont, sans-serif";
            return m.width;
          })();
          const badgeW = ctx.measureText(badgeText).width + badgePad * 2;
          const badgeH = RACE_CHART.valueBadgeH;
          const badgeX = ml + bw + 8 + valueLabelW + 6;
          const badgeY = by + barH / 2 - badgeH / 2;
          ctx.fillStyle = raceBadgeFill(RACE_BADGE.success);
          ctx.beginPath();
          ctx.roundRect(badgeX, badgeY, badgeW, badgeH, RACE_CHART.valueBadgeRadius);
          ctx.fill();
          ctx.fillStyle = RACE_BADGE.success;
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
      racePanelOrder = [];
      return;
    }

    const contentEl = $("content-race");
    const gridCols = raceGridCols();
    const { cols, sectionH, canvasH } = racePanelSizing(
      n,
      Math.max(320, contentEl.clientHeight - 6),
      Boolean(race.results && race.results.length),
    );
    container.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;

    container.style.height = `${sectionH}px`;
    container.style.flexShrink = "0";

    const key = order.join(",");
    if (key === racePanelOrder.join(",")) {
      order.forEach((idx, i) => {
        const panel = container.children[i];
        if (!panel) return;
        const canvas = panel.querySelector(".panel-canvas");
        const runnerData = race.runners[idx];
        if (canvas) canvas.style.height = `${canvasH}px`;
        if (runnerData)
          updateRaceAnimations(
            idx,
            runnerData.grid,
            runnerData.path,
            gridCols,
          );
        const badge = panel.querySelector(".panel-badge");
        if (badge) applyRaceBadge(badge, runnerData);
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
      const color = BAR_PAL[idx % BAR_PAL.length];
      const panel = document.createElement("div");
      panel.className = "race-panel";

      const header = document.createElement("div");
      header.className = "panel-header";
      header.style.backgroundColor = color;
      header.textContent = runnerData.name;

      const canvas = document.createElement("canvas");
      canvas.className = "panel-canvas";
      canvas.style.height = `${canvasH}px`;

      const badge = document.createElement("div");
      badge.className = "panel-badge";

      panel.appendChild(header);
      panel.appendChild(canvas);
      panel.appendChild(badge);
      container.appendChild(panel);

      updateRaceAnimations(
        idx,
        runnerData.grid,
        runnerData.path,
        gridCols,
      );
      drawMiniMaze(canvas, runnerData, idx);
      applyRaceBadge(badge, runnerData);
    });
  }

  function updateUI() {
    const race = raceState();
    if (!race) return;

    const selected = new Set(race.order);
    document.querySelectorAll(".race-toggle").forEach((button) => {
      const i = +button.dataset.idx;
      const color = BAR_PAL[i % BAR_PAL.length];
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
    $("race-speed-val").textContent = race.speed;
    $("race-speed-slider").value = race.speed;

    buildRacePanels();

    if (race.results) {
      $("race-charts").classList.remove("hidden");
      drawChart($("chart-nodes"), race.results, "nodes", "Nodes Visited", {
        badge: makeLowBadge("EFFICIENT", { avgFactor: 0.88 }),
      });
      drawChart($("chart-path"), race.results, "path", "Path Length", {
        badge: makeLowBadge("SHORT", { avgFactor: 0.9 }),
      });
      drawChart($("chart-cost"), race.results, "cost", "Cost", {
        badge: makeLowBadge("CHEAP", { avgFactor: 0.9 }),
      });
      drawChart($("chart-time"), race.results, "time", "Time (ms)", {
        badge: makeLowBadge("FAST", { avgFactor: 0.86 }),
      });
      drawChart($("chart-iterations"), race.results, "iterations", "Iterations", {
        formatValue: (v) => `\u00d7${Math.round(v)}`,
        badge: makeLowBadge("FEW", { avgFactor: 0.8 }),
      });
      drawChart($("chart-memory"), race.results, "peak_memory", "Peak Memory (nodes)", {
        formatValue: (v) => v === 0 ? "\u2014" : `${Math.round(v)}`,
        badge: makeLowBadge("LOW \u2193", { avgFactor: 0.75 }),
      });
      drawRadarChart($("chart-radar"), race.results);
    } else {
      $("race-charts").classList.add("hidden");
    }
  }

  async function poll() {
    if (state.tab !== "race") return;
    try {
      state.race = await (await fetch("/api/race")).json();
      updateUI();
      if (!raceRafId) raceRafId = requestAnimationFrame(renderRace);
    } catch (_) {}
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
      const v = Math.max(1, raceSpeed() - 1);
      $("race-speed-val").textContent = v;
      $("race-speed-slider").value = v;
      act({ action: "speed", value: v });
    });
    $("race-btn-spd-up").addEventListener("click", () => {
      const v = Math.min(400, raceSpeed() + 1);
      $("race-speed-val").textContent = v;
      $("race-speed-slider").value = v;
      act({ action: "speed", value: v });
    });
    $("race-speed-slider").addEventListener("input", (e) => {
      $("race-speed-val").textContent = e.target.value;
      act({ action: "speed", value: +e.target.value });
    });
  }

  function init() {
    bindUI();
    window.App.onTabChange((tab) => {
      if (tab === "race") poll();
    });
    poll();
    setInterval(poll, 40);
  }

  return { init };
})();
