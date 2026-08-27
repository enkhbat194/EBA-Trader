// Legacy carry compatibility shim.
//
// The original M18 carry paper engine was browser/session-scoped and in-memory.
// Fast Momentum is now the sole active production paper scanner because its
// state is server-side and restart-safe in SQLite. Keep the minimal globals
// used by later UI modules, but do not poll /api/paper/step or create entries.

let paperState = {
  openPosition: null,
  history: [],
  markers: [],
  realizedPnlUsd: 0,
  unrealizedPnlUsd: 0,
  totalPnlUsd: 0,
  legacyCarryRetired: true,
  newEntriesAllowed: false,
};

const paperEl = (id) => document.getElementById(id);

// Shared position renderers are deliberately defined before trade_detail.js is
// loaded. trade_detail.js combines Fast, legacy carry and MT5 rows in one list.
// Keeping these helpers explicit prevents a missing renderer from crashing a
// successful /api/runner/status refresh and falsely reporting the server offline.
function paperPositionMarkup(position) {
  const pnl = Number(position?.unrealizedPnlUsd ?? position?.unrealized_net_usd ?? 0);
  const symbol = String(position?.symbol || 'BTCUSDT');
  const side = String(position?.side || 'CARRY');
  const entry = position?.entry_price ?? position?.spot_entry_vwap ?? null;
  const entryText = Number.isFinite(Number(entry)) ? formatPrice(entry) : '—';
  return `<div class="position-row"><div><strong>LEGACY CARRY PAPER · ${escapeHtml(symbol)} ${escapeHtml(side)}</strong><small>Read-only retired engine · Entry ${escapeHtml(entryText)}</small></div><span class="pnl ${pnl >= 0 ? 'positive-text' : 'negative'}">${escapeHtml(formatUsd(pnl))}</span></div>`;
}

function mt5PositionMarkup(position) {
  const side = Number(position?.type) === 1 ? 'SELL' : 'BUY';
  const pnl = Number(position?.profit || 0);
  const symbol = String(position?.symbol || 'MT5');
  const volume = position?.volume ?? '—';
  return `<div class="position-row"><div><strong>${escapeHtml(symbol)} · ${side} ${escapeHtml(volume)}</strong><small>Entry ${escapeHtml(formatPrice(position?.priceOpen))} · Current ${escapeHtml(formatPrice(position?.priceCurrent))}</small></div><span class="pnl ${pnl >= 0 ? 'positive-text' : 'negative'}">${escapeHtml(formatUsd(pnl))}</span></div>`;
}

function paperTime(ms) {
  const value = Number(ms);
  if (!Number.isFinite(value) || value <= 0) return '—';
  return new Date(value).toLocaleString();
}

function applyPaperState(state) {
  if (!state || typeof state !== 'object') return;
  paperState = {
    openPosition: state.openPosition || null,
    history: Array.isArray(state.history) ? state.history : [],
    markers: Array.isArray(state.markers) ? state.markers : [],
    realizedPnlUsd: Number(state.realizedPnlUsd || 0),
    unrealizedPnlUsd: Number(state.unrealizedPnlUsd || 0),
    totalPnlUsd: Number(state.totalPnlUsd || 0),
    legacyCarryRetired: state.legacyCarryRetired !== false,
    newEntriesAllowed: state.newEntriesAllowed === true,
  };
}

async function loadPaperState() {
  if (!demoSessionToken) return paperState;
  try {
    const state = await postJson('/api/paper/state', { sessionToken: demoSessionToken });
    applyPaperState(state);
  } catch (_) {
    // Legacy carry state is non-authoritative. Fast Momentum remains unaffected.
  }
  return paperState;
}

function installCarryRetirementUi() {
  const start = paperEl('startBot');
  const stop = paperEl('stopBot');
  const legacyControls = start?.closest('.bot-controls');
  if (legacyControls) legacyControls.hidden = true;
  if (start) start.disabled = true;
  if (stop) stop.disabled = true;

  const close = paperEl('closePaperPosition');
  if (close) {
    close.disabled = true;
    close.hidden = true;
  }

  const count = paperEl('paperTradeCount');
  if (count) count.textContent = 'CARRY RETIRED';

  const history = paperEl('historyList');
  if (history) {
    history.innerHTML = '<article class="empty-state"><div class="empty-icon">✓</div><h3>Legacy carry paper retired</h3><p>Fast Momentum is the active restart-safe paper engine. Historical M18 carry code remains regression-only and cannot open new production positions.</p></article>';
  }

  if (!paperEl('carryRetiredNotice')) {
    const heartbeat = paperEl('scannerHeartbeatCard');
    const homeGrid = document.querySelector('[data-screen="home"] .metric-grid');
    const notice = document.createElement('article');
    notice.className = 'section-card';
    notice.id = 'carryRetiredNotice';
    notice.innerHTML = '<div class="section-head"><div><span class="eyebrow">Paper engine</span><h3>Fast Momentum is active</h3></div><span class="pill neutral">CARRY RETIRED</span></div><p class="muted-copy">The old browser/in-memory cash-and-carry paper engine no longer opens new positions. Fast Momentum remains server-side, paper-only and SQLite restart-safe.</p>';
    if (heartbeat) heartbeat.insertAdjacentElement('afterend', notice);
    else homeGrid?.insertAdjacentElement('afterend', notice);
  }
}

try {
  paperBotRunning = false;
} catch (_) {
  // Base UI may change; hiding the legacy controls is the authoritative UI guard.
}

installCarryRetirementUi();
loadPaperState();
