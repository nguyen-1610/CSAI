/* Visualize tab logic */

window.VisualizePage = (() => {
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
  const GRID_BG = "#E2D9CB";
  const GRID_LINE_MINOR = "rgba(31, 42, 54, 0.1)";
  const GRID_LINE_MAJOR = "rgba(39, 76, 119, 0.16)";
  const GRID_FRAME = "rgba(31, 42, 54, 0.16)";
  const GRID_DRAG = "rgba(255, 250, 245, 0.9)";
  const MARKER_LINE = "rgba(255, 248, 240, 0.92)";
  const MARKER_FILL = "rgba(255, 248, 240, 0.96)";
  const MAZE_REVEAL_TYPES = new Set([1, 8, 9, 10]);

  let gridCanvas;
  let gridCtx;

  let mDown = false;
  let mBtn = 0;
  let gInfo = { rows: 0, cols: 0, cell: 0, ox: 0, oy: 0 };

  let ddOpen = false;

  let lastVizRows = 0;
  let lastVizCols = 0;

  let dragType = null;
  let dragCell = null;
  let lastDragSent = null;
  let lastWallPos = null;

  let cpPlaceMode = false;
  let terrainBrush = 0;

  let prevGrid = null;
  const animCells = new Map();
  let renderFrameId = null;
  let needsRender = true;
  let lastDpr = window.devicePixelRatio || 1;
  let gridAreaObserver = null;
  let pollTimerId = null;
  let pollInFlight = false;
  const knownMarkers = { start: null, end: null, checkpoint: null };

  const {
    $,
    act,
    state,
    uiConfig,
    hasPendingActions,
    onActionActivity,
    getActionEpoch,
  } = window.App;

  function vizState() {
    return state.viz;
  }

  function requestRender() {
    needsRender = true;
    if (renderFrameId === null) {
      renderFrameId = requestAnimationFrame(render);
    }
  }

  function hasActiveAnimations() {
    const now = performance.now();
    let active = false;
    animCells.forEach((anim, key) => {
      if (now < anim.startTime + anim.duration) {
        active = true;
      } else {
        animCells.delete(key);
      }
    });
    return active;
  }

  function fitCanvasIfNeeded() {
    const parent = $("grid-area");
    if (!parent) return;
    const dpr = devicePixelRatio || 1;
    const style = getComputedStyle(parent);
    const w = Math.max(
      0,
      parent.clientWidth -
        parseFloat(style.paddingLeft || 0) -
        parseFloat(style.paddingRight || 0),
    );
    const h = Math.max(
      0,
      parent.clientHeight -
        parseFloat(style.paddingTop || 0) -
        parseFloat(style.paddingBottom || 0),
    );
    if (!w || !h) return;
    const targetW = Math.round(w * dpr);
    const targetH = Math.round(h * dpr);
    if (gridCanvas.width !== targetW || gridCanvas.height !== targetH) {
      gridCanvas.width = targetW;
      gridCanvas.height = targetH;
      gridCanvas.style.width = `${w}px`;
      gridCanvas.style.height = `${h}px`;
      gridCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
      needsRender = true;
    }
  }

  function refreshCanvasMetrics(force = false) {
    const dpr = window.devicePixelRatio || 1;
    if (force || Math.abs(dpr - lastDpr) > 0.001) {
      lastDpr = dpr;
      fitCanvasIfNeeded();
      requestRender();
    }
  }

  function setText(id, value) {
    const el = $(id);
    if (el) el.textContent = value;
  }

  function describeCheckpoint(checkpoint) {
    if (!checkpoint) return "Inactive";
    return `R${checkpoint[0] + 1} / C${checkpoint[1] + 1}`;
  }

  function syncKnownMarkers(viz) {
    if (!viz?.grid?.length) return;
    for (let i = 0; i < viz.grid.length; i++) {
      const t = viz.grid[i];
      if (t !== 2 && t !== 3 && t !== 7) continue;
      const pos = [Math.floor(i / viz.cols), i % viz.cols];
      if (t === 2) knownMarkers.start = pos;
      else if (t === 3) knownMarkers.end = pos;
      else if (t === 7) knownMarkers.checkpoint = pos;
    }
    if (!viz.checkpoint) knownMarkers.checkpoint = null;
  }

  function drawMarkerCell(r, c, cell, ox, oy, type) {
    if (r < 0 || c < 0) return;
    const x = ox + c * cell;
    const y = oy + r * cell;
    gridCtx.fillStyle = CELL_C[type] || CELL_C[0];
    gridCtx.fillRect(x, y, cell, cell);
    drawMarkerAccent(gridCtx, x, y, cell, type);
    if (cell >= 6) {
      gridCtx.strokeStyle = GRID_LINE_MINOR;
      gridCtx.lineWidth = 0.45;
      gridCtx.strokeRect(x + 0.25, y + 0.25, cell - 0.5, cell - 0.5);
    }
  }

  function describeRouteMode(viz) {
    return viz?.checkpoint ? "Checkpoint route" : "Direct route";
  }

  function resolveStage(viz) {
    if (viz.running) return { text: "Searching", state: "running" };
    if (viz.paused && !viz.finished) return { text: "Paused", state: "paused" };
    if (viz.stats.found === true) return { text: "Path Found", state: "success" };
    if (viz.stats.found === false) return { text: "No Path", state: "failure" };
    return { text: "Ready", state: "idle" };
  }

  function setTerrainBrush(type) {
    terrainBrush = terrainBrush === type ? 0 : type;
    if (terrainBrush) cpPlaceMode = false;
    document.querySelectorAll(".btn-terrain").forEach((button) => {
      button.classList.toggle(
        "btn-selected",
        +button.dataset.terrain === terrainBrush,
      );
    });
  }

  function buildAlgoList() {
    const list = $("algo-list");
    list.innerHTML = "";
    ALG_NAMES.forEach((name, i) => {
      const item = document.createElement("div");
      item.className = "dd-item";

      const copy = document.createElement("div");
      copy.className = "dd-item-copy";

      const itemName = document.createElement("span");
      itemName.className = "dd-item-name";
      itemName.textContent = name;

      const itemNote = document.createElement("span");
      itemNote.className = "dd-item-note";
      itemNote.textContent = "Search procedure";

      copy.appendChild(itemName);
      copy.appendChild(itemNote);
      item.appendChild(copy);

      item.addEventListener("click", () => {
        act({ action: "select_algo", idx: i });
        ddOpen = false;
        list.classList.add("hidden");
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
    (vizState()?.path_cells || []).forEach(([r, c], i) =>
      pathIdx.set(`${r},${c}`, i),
    );
    const changes = [];
    let mazeRevealCount = 0;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const i = r * cols + c;
        const oldT = prevGrid[i];
        const newT = newGrid[i];
        if (oldT === newT) continue;
        changes.push({ r, c, oldT, newT, key: `${r},${c}` });
        if (MAZE_REVEAL_TYPES.has(newT)) mazeRevealCount += 1;
      }
    }

    const bulkMazeReveal =
      mazeRevealCount >= Math.max(18, Math.floor(rows * cols * 0.08));

    changes.forEach(({ r, c, oldT, newT, key }) => {
      if (newT === 6) {
        const delay =
          (pathIdx.get(key) ?? 0) * uiConfig.pathAnimationStepDelayMs;
        animCells.set(key, {
          kind: "path",
          from: oldT === 0 ? 4 : oldT,
          to: newT,
          startTime: now + delay,
          duration: uiConfig.pathAnimationDurationMs + 40,
        });
        return;
      }

      if (MAZE_REVEAL_TYPES.has(newT)) {
        const delay = bulkMazeReveal ? ((r * 3 + c * 5) % 11) * 18 : 0;
        animCells.set(key, {
          kind: "reveal",
          from: oldT,
          to: newT,
          startTime: now + delay,
          duration: bulkMazeReveal ? 260 : 180,
        });
        return;
      }

      if (newT === 4 || newT === 5) {
        animCells.set(key, {
          kind: "pulse",
          from: oldT,
          to: newT,
          startTime: now,
          duration: 180,
        });
        return;
      }

      animCells.delete(key);
    });
    prevGrid = newGrid.slice();
  }

  function easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
  }

  function drawAnimatedOverlay(x, y, cell, color, progress) {
    const eased = easeOutCubic(progress);
    const scale = 0.58 + eased * 0.42;
    const size = cell * scale;
    const bx = x + (cell - size) / 2;
    const by = y + (cell - size) / 2;
    gridCtx.save();
    gridCtx.globalAlpha = 0.18 + eased * 0.82;
    gridCtx.fillStyle = color;
    if (cell >= 4) {
      gridCtx.beginPath();
      gridCtx.roundRect(bx, by, size, size, Math.max(2, size * 0.18));
      gridCtx.fill();
    } else {
      gridCtx.fillRect(bx, by, size, size);
    }
    gridCtx.restore();
  }

  function drawMarkerAccent(ctx, x, y, cell, type) {
    if (type !== 2 && type !== 3 && type !== 7) return;

    ctx.save();

    if (cell >= 8) {
      const inset = Math.max(1, cell * 0.16);
      const size = Math.max(2, cell - inset * 2);
      ctx.strokeStyle = MARKER_LINE;
      ctx.lineWidth = Math.max(1.1, cell * 0.07);
      ctx.beginPath();
      ctx.roundRect(
        x + inset,
        y + inset,
        size,
        size,
        Math.max(2, size * 0.22),
      );
      ctx.stroke();
    }

    if (cell >= 14) {
      const cx = x + cell / 2;
      const cy = y + cell / 2;
      const symbolSize = cell * 0.38;
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
          Math.max(1.6, size * 0.22),
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
    wash.addColorStop(0, "#EBE1D2");
    wash.addColorStop(1, GRID_BG);
    ctx.fillStyle = wash;
    ctx.fillRect(0, 0, w, h);

    const coolGlow = ctx.createRadialGradient(
      w * 0.82,
      h * 0.14,
      0,
      w * 0.82,
      h * 0.14,
      Math.max(w, h) * 0.72,
    );
    coolGlow.addColorStop(0, "rgba(39, 76, 119, 0.08)");
    coolGlow.addColorStop(1, "rgba(39, 76, 119, 0)");
    ctx.fillStyle = coolGlow;
    ctx.fillRect(0, 0, w, h);

    const warmGlow = ctx.createRadialGradient(
      w * 0.12,
      h * 0.88,
      0,
      w * 0.12,
      h * 0.88,
      Math.max(w, h) * 0.6,
    );
    warmGlow.addColorStop(0, "rgba(197, 155, 73, 0.06)");
    warmGlow.addColorStop(1, "rgba(197, 155, 73, 0)");
    ctx.fillStyle = warmGlow;
    ctx.fillRect(0, 0, w, h);
  }

  function drawGridGuides(ctx, rows, cols, cell, ox, oy) {
    const gw = cols * cell;
    const gh = rows * cell;

    ctx.save();
    ctx.strokeStyle = GRID_FRAME;
    ctx.lineWidth = 1.1;
    ctx.strokeRect(ox + 0.5, oy + 0.5, gw - 1, gh - 1);

    if (cell >= 11) {
      ctx.strokeStyle = GRID_LINE_MAJOR;
      ctx.lineWidth = 0.85;
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

  function drawGrid() {
    const viz = vizState();
    if (!viz) return;
    const { rows, cols, grid } = viz;
    const dpr = devicePixelRatio || 1;
    const cw = Math.floor(gridCanvas.width / dpr);
    const ch = Math.floor(gridCanvas.height / dpr);
    if (!cw || !ch) return;
    const cell = Math.max(1, Math.floor(Math.min(cw / cols, ch / rows)));
    const gw = cols * cell;
    const gh = rows * cell;
    const ox = Math.floor((cw - gw) / 2);
    const oy = Math.floor((ch - gh) / 2);
    gInfo = { rows, cols, cell, ox, oy };

    drawPaperBackdrop(gridCtx, cw, ch);

    const now = performance.now();
    const gridHasEnd = grid.includes(3);
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        let t = grid[r * cols + c];
        if (dragType === "start") {
          if (t === 2) t = 0;
          if (dragCell && r === dragCell.r && c === dragCell.c) t = 2;
        } else if (dragType === "end") {
          if (t === 3) t = 0;
          if (dragCell && r === dragCell.r && c === dragCell.c) t = 3;
        } else if (dragType === "checkpoint") {
          if (t === 7) t = 0;
          if (dragCell && r === dragCell.r && c === dragCell.c) t = 7;
        }

        const x = ox + c * cell;
        const y = oy + r * cell;
        const key = `${r},${c}`;
        const activeAnim = animCells.get(key);

        if (activeAnim && cell >= 4) {
          const baseType = CELL_C[activeAnim.from] ? activeAnim.from : 0;
          if (now < activeAnim.startTime) {
            gridCtx.fillStyle = CELL_C[baseType] || CELL_C[0];
            gridCtx.fillRect(x, y, cell, cell);
          } else {
            const elapsed = now - activeAnim.startTime;
            const progress = Math.min(elapsed / activeAnim.duration, 1);

            if (activeAnim.kind === "path") {
              if (progress >= 1) animCells.delete(key);
              const c1 = 1.70158;
              const c3 = c1 + 1;
              const scale = Math.max(
                0,
                1 +
                  c3 * Math.pow(progress - 1, 3) +
                  c1 * Math.pow(progress - 1, 2),
              );

              gridCtx.fillStyle = CELL_C[baseType] || CELL_C[4];
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
                gridCtx.beginPath();
                gridCtx.roundRect(bx, by, s, s, Math.max(2, s * 0.22));
                gridCtx.fill();
                gridCtx.restore();
              }
            } else {
              gridCtx.fillStyle = CELL_C[baseType] || CELL_C[0];
              gridCtx.fillRect(x, y, cell, cell);
              drawAnimatedOverlay(
                x,
                y,
                cell,
                CELL_C[activeAnim.to] || CELL_C[t] || CELL_C[0],
                progress,
              );
              if (progress >= 1) animCells.delete(key);
            }
          }
        } else {
          gridCtx.fillStyle = CELL_C[t] || CELL_C[0];
          gridCtx.fillRect(x, y, cell, cell);
        }

        drawMarkerAccent(gridCtx, x, y, cell, t);

        if (cell >= 6) {
          gridCtx.strokeStyle = GRID_LINE_MINOR;
          gridCtx.lineWidth = 0.45;
          gridCtx.strokeRect(x + 0.25, y + 0.25, cell - 0.5, cell - 0.5);
        }
        if (dragCell && r === dragCell.r && c === dragCell.c && dragType) {
          gridCtx.strokeStyle = GRID_DRAG;
          gridCtx.lineWidth = Math.max(1.5, cell * 0.12);
          gridCtx.strokeRect(x + 1.5, y + 1.5, cell - 3, cell - 3);
        }
      }
    }

    if (viz.checkpoint && !gridHasEnd && knownMarkers.end) {
      const [endR, endC] = knownMarkers.end;
      if (endR < rows && endC < cols) {
        drawMarkerCell(endR, endC, cell, ox, oy, 3);
      }
    }

    drawGridGuides(gridCtx, rows, cols, cell, ox, oy);
  }

  function gridPos(e) {
    const rect = gridCanvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const { rows, cols, cell, ox, oy } = gInfo;
    const c = Math.floor((mx - ox) / cell);
    const r = Math.floor((my - oy) / cell);
    return r >= 0 && r < rows && c >= 0 && c < cols ? { r, c } : null;
  }

  function updateUI() {
    const viz = vizState();
    if (!viz) return;
    syncKnownMarkers(viz);

    const stage = resolveStage(viz);
    const algorithmName = ALG_NAMES[viz.cur_alg] || "Unknown";
    const gridLabel = `${viz.rows} x ${viz.cols}`;
    const routeLabel = describeRouteMode(viz);
    const checkpointLabel = describeCheckpoint(viz.checkpoint);

    const runButton = $("btn-run");
    const isActive = viz.running || viz.paused;
    if (viz.running) {
      runButton.textContent = "Pause";
      runButton.className = "btn btn-run pausing";
    } else if (viz.paused && !viz.finished) {
      runButton.textContent = "Continue";
      runButton.className = "btn btn-run btn-continue";
    } else {
      runButton.textContent = "Run";
      runButton.className = "btn btn-run";
    }
    $("btn-step-back").disabled =
      (viz.step_ptr ?? -1) < 1 || viz.finished || viz.running;
    $("btn-step-fwd").disabled = viz.running || viz.finished;
    $("btn-cancel").classList.toggle("hidden", !isActive && !viz.finished);

    const cpButton = $("btn-cp-toggle");
    const hasCp = !!viz.checkpoint;
    setText("cp-label", hasCp ? "Remove Checkpoint" : "Checkpoint");
    cpButton.classList.toggle("btn-cp-active", hasCp);
    if (hasCp) {
      cpButton.classList.remove("btn-selected");
      cpPlaceMode = false;
    } else {
      cpButton.classList.toggle("btn-selected", cpPlaceMode);
    }

    setText("st-nodes", viz.stats.nodes);
    setText("st-path", viz.stats.path);
    setText("st-cost", viz.stats.cost);
    const elapsedSeconds = viz.stats.time || 0;
    setText("st-time", `${(elapsedSeconds * 1000).toFixed(2)} ms`);

    const status = $("st-status");
    status.textContent = stage.text;
    status.dataset.state = stage.state;

    setText("speed-val", viz.speed);
    $("speed-slider").value = viz.speed;
    setText("race-speed-val", viz.speed);
    $("race-speed-slider").value = viz.speed;

    if (document.activeElement !== $("inp-rows")) $("inp-rows").value = viz.rows;
    if (document.activeElement !== $("inp-cols")) $("inp-cols").value = viz.cols;

    setText("algo-name", algorithmName);
    setText("viz-session-alg", algorithmName);
    setText("viz-session-grid", gridLabel);
    setText("viz-session-mode", routeLabel);
    setText("viz-session-checkpoint", checkpointLabel);
    setText("viz-summary-alg", algorithmName);
    setText("viz-summary-grid", gridLabel);
    setText("viz-summary-mode", routeLabel);
    setText("viz-summary-checkpoint", checkpointLabel);
    setText("viz-stage-chip", stage.text);
    setText("viz-step-chip", (viz.step_ptr ?? -1) >= 0 ? `${viz.step_ptr}` : "-");

    document.querySelectorAll(".dd-item").forEach((item, i) => {
      item.classList.toggle("selected", i === viz.cur_alg);
      if (i === viz.cur_alg && !item.querySelector(".check")) {
        const check = document.createElement("span");
        check.className = "check";
        check.textContent = "Active";
        item.appendChild(check);
      } else if (i !== viz.cur_alg) {
        const check = item.querySelector(".check");
        if (check) check.remove();
      }
    });

    const sidebar = $("viz-sidebar");
    sidebar.classList.toggle(
      "expanded-stats",
      viz.finished || viz.stats.found !== null,
    );
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
    if (state.tab !== "visualize") return;
    if (pollInFlight) return;
    if (hasPendingActions()) {
      schedulePoll(uiConfig.pendingActionPollDelayMs);
      return;
    }
    const pollActionEpoch = getActionEpoch();
    pollInFlight = true;
    try {
      refreshCanvasMetrics();
      const nextVizState = await (await fetch("/api/state")).json();
      if (hasPendingActions() || getActionEpoch() !== pollActionEpoch) {
        schedulePoll(uiConfig.pendingActionPollDelayMs);
        return;
      }
      state.viz = nextVizState;
      if (state.viz.rows !== lastVizRows || state.viz.cols !== lastVizCols) {
        lastVizRows = state.viz.rows;
        lastVizCols = state.viz.cols;
        prevGrid = null;
        animCells.clear();
      }
      if (state.viz.grid)
        updateAnimations(state.viz.grid, state.viz.rows, state.viz.cols);
      updateUI();
      requestRender();
    } catch (error) {
      console.warn("[visualize] poll failed", error);
    } finally {
      pollInFlight = false;
      if (state.tab === "visualize") schedulePoll();
    }
  }

  function render() {
    renderFrameId = null;
    if (state.tab !== "visualize") return;
    refreshCanvasMetrics();
    fitCanvasIfNeeded();
    const animating = hasActiveAnimations();
    if (!needsRender && !animating) return;
    drawGrid();
    needsRender = false;
    if (animating) {
      renderFrameId = requestAnimationFrame(render);
    }
  }

  function onResize() {
    if (state.tab === "visualize") {
      lastDpr = window.devicePixelRatio || 1;
      fitCanvasIfNeeded();
      requestRender();
    }
  }

  function bindUI() {
    buildAlgoList();

    $("algo-btn").addEventListener("click", () => {
      ddOpen = !ddOpen;
      $("algo-list").classList.toggle("hidden", !ddOpen);
    });
    document.addEventListener("click", (e) => {
      if (ddOpen && !$("algo-dd").contains(e.target)) {
        ddOpen = false;
        $("algo-list").classList.add("hidden");
      }
    });

    $("btn-run").addEventListener("click", () => act({ action: "run" }));
    $("btn-step-back").addEventListener("click", () =>
      act({ action: "step_back" }),
    );
    $("btn-step-fwd").addEventListener("click", () => act({ action: "step" }));
    $("btn-cancel").addEventListener("click", () =>
      act({ action: "cancel_algo" }),
    );
    $("btn-clear").addEventListener("click", () => act({ action: "clear" }));
    $("btn-maze").addEventListener("click", () => act({ action: "maze" }));
    $("btn-weighted-maze").addEventListener("click", () =>
      act({ action: "weighted_maze" }),
    );
    $("btn-reset").addEventListener("click", () => act({ action: "reset" }));

    $("btn-cp-toggle").addEventListener("click", () => {
      if (vizState()?.checkpoint) {
        act({ action: "remove_checkpoint" });
      } else {
        cpPlaceMode = !cpPlaceMode;
        if (cpPlaceMode) setTerrainBrush(0);
        $("btn-cp-toggle").classList.toggle("btn-selected", cpPlaceMode);
      }
    });

    document.querySelectorAll(".btn-terrain").forEach((button) => {
      button.addEventListener("click", () =>
        setTerrainBrush(+button.dataset.terrain),
      );
    });

    $("btn-spd-down").addEventListener("click", () => {
      const v = Math.max(uiConfig.speedMin, (vizState()?.speed || 20) - 1);
      setText("speed-val", v);
      $("speed-slider").value = v;
      act({ action: "speed", value: v });
    });
    $("btn-spd-up").addEventListener("click", () => {
      const v = Math.min(uiConfig.speedMax, (vizState()?.speed || 20) + 1);
      setText("speed-val", v);
      $("speed-slider").value = v;
      act({ action: "speed", value: v });
    });
    $("speed-slider").addEventListener("input", (e) => {
      setText("speed-val", e.target.value);
      act({ action: "speed", value: +e.target.value });
    });

    $("btn-row-dn").addEventListener("click", () =>
      act({ action: "change_grid", dr: -1, dc: 0 }),
    );
    $("btn-row-up").addEventListener("click", () =>
      act({ action: "change_grid", dr: 1, dc: 0 }),
    );
    $("btn-col-dn").addEventListener("click", () =>
      act({ action: "change_grid", dr: 0, dc: -1 }),
    );
    $("btn-col-up").addEventListener("click", () =>
      act({ action: "change_grid", dr: 0, dc: 1 }),
    );

    ["inp-rows", "inp-cols"].forEach((id) => {
      $(id).addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          const rows = +$("inp-rows").value || vizState()?.rows || 22;
          const cols = +$("inp-cols").value || vizState()?.cols || 30;
          act({ action: "set_grid", rows, cols });
          e.target.blur();
        }
      });
    });

    document.addEventListener("keydown", (e) => {
      if (e.target.tagName === "INPUT") return;
      if (e.key === " ") {
        e.preventDefault();
        act({ action: "run" });
      }
      if (e.key === "." && state.tab === "visualize") act({ action: "step" });
      if (e.key === "," && state.tab === "visualize")
        act({ action: "step_back" });
      if (e.key === "r" && state.tab === "visualize") act({ action: "reset" });
      if (e.key === "Escape" && state.tab === "visualize")
        act({ action: "cancel_algo" });
    });

    function applyWallOptimistic(p, remove) {
      const viz = state.viz;
      if (!viz?.grid) return;
      const idx = p.r * viz.cols + p.c;
      const t = viz.grid[idx];
      if (t === 2 || t === 3 || t === 7) return;
      viz.grid[idx] = remove ? 0 : 1;
      requestRender();
    }

    function applyTerrainOptimistic(p, terrain) {
      const viz = state.viz;
      if (!viz?.grid) return;
      const idx = p.r * viz.cols + p.c;
      const t = viz.grid[idx];
      if (t === 1 || t === 2 || t === 3 || t === 7) return;
      viz.grid[idx] = terrain;
      requestRender();
    }

    gridCanvas.addEventListener("mousedown", (e) => {
      const viz = vizState();
      const p = gridPos(e);
      if (terrainBrush > 0 && p && !viz?.running) {
        mDown = true;
        mBtn = e.button;
        lastWallPos = p;
        applyTerrainOptimistic(p, e.button === 2 ? 0 : terrainBrush);
        act({
          action: "set_terrain",
          r: p.r,
          c: p.c,
          terrain: e.button === 2 ? 0 : terrainBrush,
        });
        return;
      }
      if (e.button === 0 && p && !viz?.running) {
        const t = viz?.grid?.[p.r * (viz?.cols ?? 0) + p.c];
        if (t === 2) {
          dragType = "start";
          dragCell = { ...p };
          lastDragSent = { ...p };
          document.body.style.cursor = "grabbing";
          requestRender();
          return;
        }
        if (t === 3) {
          dragType = "end";
          dragCell = { ...p };
          lastDragSent = { ...p };
          document.body.style.cursor = "grabbing";
          requestRender();
          return;
        }
        if (t === 7) {
          dragType = "checkpoint";
          dragCell = { ...p };
          lastDragSent = { ...p };
          document.body.style.cursor = "grabbing";
          requestRender();
          return;
        }
      }
      if (e.button === 0 && (e.shiftKey || cpPlaceMode) && p && !viz?.running) {
        const t = viz?.grid?.[p.r * (viz?.cols ?? 0) + p.c];
        if (t === 7) act({ action: "remove_checkpoint" });
        else if (t !== 2 && t !== 3)
          act({ action: "set_checkpoint", r: p.r, c: p.c });
        if (cpPlaceMode) {
          cpPlaceMode = false;
          $("btn-cp-toggle").classList.remove("btn-selected");
        }
        return;
      }
      if (!p) return;
      mDown = true;
      mBtn = e.button;
      lastWallPos = p;
      applyWallOptimistic(p, e.button === 2);
      act({ action: "grid_cell", r: p.r, c: p.c, remove: e.button === 2 });
    });

    gridCanvas.addEventListener("mousemove", (e) => {
      const viz = vizState();
      if (!mDown && !dragType) {
        const p = gridPos(e);
        if (p && viz?.grid && !viz.running) {
          const t = viz.grid[p.r * viz.cols + p.c];
          gridCanvas.style.cursor =
            t === 2 || t === 3 || t === 7 ? "grab" : "";
        } else {
          gridCanvas.style.cursor = "";
        }
      }
      if (!mDown) return;
      const p = gridPos(e);
      if (!p) return;
      if (lastWallPos && lastWallPos.r === p.r && lastWallPos.c === p.c) return;
      lastWallPos = p;
      if (terrainBrush > 0) {
        applyTerrainOptimistic(p, mBtn === 2 ? 0 : terrainBrush);
        act({
          action: "set_terrain",
          r: p.r,
          c: p.c,
          terrain: mBtn === 2 ? 0 : terrainBrush,
        });
      } else {
        applyWallOptimistic(p, mBtn === 2);
        act({ action: "grid_cell", r: p.r, c: p.c, remove: mBtn === 2 });
      }
    });

    document.addEventListener("mouseup", () => {
      dragType = null;
      dragCell = null;
      lastDragSent = null;
      lastWallPos = null;
      document.body.style.cursor = "";
      mDown = false;
      requestRender();
    });
    gridCanvas.addEventListener("contextmenu", (e) => e.preventDefault());

    document.addEventListener("mousemove", (e) => {
      if (dragType) {
        const p = gridPos(e);
        if (p && (p.r !== lastDragSent?.r || p.c !== lastDragSent?.c)) {
          dragCell = { ...p };
          lastDragSent = { ...p };
          requestRender();
          const actionMap = {
            start: "set_start",
            end: "set_end",
            checkpoint: "set_checkpoint",
          };
          act({ action: actionMap[dragType], r: p.r, c: p.c });
        }
      }
    });
  }

  function init() {
    gridCanvas = $("grid-canvas");
    gridCtx = gridCanvas.getContext("2d");

    bindUI();

    window.addEventListener("resize", onResize);
    window.visualViewport?.addEventListener("resize", onResize);
    if ("ResizeObserver" in window) {
      gridAreaObserver = new ResizeObserver(() => onResize());
      gridAreaObserver.observe($("grid-area"));
    }
    window.App.onTabChange((tab) => {
      if (tab === "visualize") {
        onResize();
        schedulePoll(0);
      } else {
        clearPollTimer();
      }
    });
    onActionActivity((pendingCount) => {
      if (
        pendingCount === 0 &&
        state.tab === "visualize" &&
        !pollInFlight
      ) {
        schedulePoll(0);
      }
    });

    onResize();
    if (state.tab === "visualize") schedulePoll(0);
    requestRender();
  }

  return { init };
})();
