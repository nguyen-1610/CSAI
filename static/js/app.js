/* Shared frontend bootstrap */

const App = (() => {
  const TAB_STORAGE_KEY = "maze_active_tab";
  const uiConfig = {
    pollIntervalMs: 40,
    pendingActionPollDelayMs: 60,
    pathAnimationStepDelayMs: 12,
    pathAnimationDurationMs: 420,
    speedMin: 1,
    speedMax: 999,
  };

  const state = {
    tab: 'visualize',
    viz: null,
    race: null,
  };

  const tabListeners = [];
  const actionListeners = [];
  let actionQueue = Promise.resolve();
  let pendingActions = 0;
  let actionEpoch = 0;

  const $ = id => document.getElementById(id);

  function emitActionActivity() {
    actionListeners.forEach(listener => listener(pendingActions));
  }

  function fitCanvas(canvas, parent) {
    const dpr = devicePixelRatio || 1;
    const w = parent.clientWidth;
    const h = parent.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return ctx;
  }

  async function postAction(data) {
    try {
      const response = await fetch('/api/action', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok || body?.ok === false) {
        console.warn(
          '[api/action]',
          data?.action || 'unknown',
          body?.message || body?.error || `HTTP ${response.status}`,
        );
      }
      return body;
    } catch (error) {
      console.warn('[api/action] request failed', data?.action || 'unknown', error);
    }
  }

  function act(data) {
    actionEpoch += 1;
    pendingActions += 1;
    emitActionActivity();

    const task = actionQueue
      .catch(() => null)
      .then(() => postAction(data));

    actionQueue = task.finally(() => {
      pendingActions = Math.max(0, pendingActions - 1);
      emitActionActivity();
    });

    return task;
  }

  function readSavedTab() {
    try {
      const saved = window.localStorage.getItem(TAB_STORAGE_KEY);
      return saved === 'race' || saved === 'visualize' ? saved : null;
    } catch (_) {
      return null;
    }
  }

  function persistTab(tab) {
    try {
      window.localStorage.setItem(TAB_STORAGE_KEY, tab);
    } catch (_) {}
  }

  function switchTab(tab, { persist = true } = {}) {
    if (tab !== 'visualize' && tab !== 'race') tab = 'visualize';
    state.tab = tab;
    if (persist) persistTab(tab);
    act({ action: 'switch_tab', tab: tab });
    document.body.dataset.tab = tab;
    document.querySelectorAll('.tab').forEach(button => {
      button.classList.toggle('active', button.dataset.tab === tab);
    });
    $('ribbon-viz').classList.toggle('hidden', tab !== 'visualize');
    $('ribbon-race').classList.toggle('hidden', tab !== 'race');
    $('content-viz').classList.toggle('hidden', tab !== 'visualize');
    $('content-race').classList.toggle('hidden', tab !== 'race');
    tabListeners.forEach(listener => listener(tab));
  }

  function onTabChange(listener) {
    tabListeners.push(listener);
  }

  function onActionActivity(listener) {
    actionListeners.push(listener);
  }

  function hasPendingActions() {
    return pendingActions > 0;
  }

  function getActionEpoch() {
    return actionEpoch;
  }

  function initTabs() {
    document.querySelectorAll('.tab').forEach(button => {
      button.addEventListener('click', () => switchTab(button.dataset.tab));
    });
  }

  function init() {
    state.tab = readSavedTab() || 'visualize';
    initTabs();
    switchTab(state.tab, { persist: false });
    if (window.VisualizePage?.init) window.VisualizePage.init();
    if (window.RacePage?.init) window.RacePage.init();
  }

  return {
    $,
    act,
    fitCanvas,
    uiConfig,
    state,
    switchTab,
    onTabChange,
    onActionActivity,
    hasPendingActions,
    getActionEpoch,
    init,
  };
})();

window.App = App;

document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
