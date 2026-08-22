let momentumState = {
  openPosition: null,
  history: [],
  markers: [],
  signal: {},
  realizedPnlUsd: 0,
  unrealizedPnlUsd: 0,
  totalPnlUsd: 0,
  tradeCount: 0,
  winRate: 0,
};
let momentumRunning = false;
let momentumTimer = null;
let serverSecretsConfigured = false;
let autoReconnectSuppressed = false;

function momentumEl(id) {
  return document.getElementById(id);
}

function installMomentumUi() {
  const list = document.querySelector('.opportunity-list');
  const mt5Card = momentumEl('mt5MarketsCard');
  if (list && !momentumEl('momentumCard')) {
    const card = document.createElement('article');
    card.className = 'opportunity-card';
    card.id = 'momentumCard';
    card.innerHTML = `
      <div class="card-title"><div><strong>BTC Fast Momentum</strong><small>USD-M Perpetual · 1m + 5m · PAPER ONLY</small></div><span class="badge muted" id="momentumStatus">OFF</span></div>
      <div class="edge-score"><span>SIGNAL</span><strong id="momentumDecision">NO_TRADE</strong></div>
      <dl>
        <div><dt>Long / Short score</dt><dd id="momentumScores">0 / 0</dd></div>
        <div><dt>Paper margin</dt><dd>$10.00</dd></div>
        <div><dt>Risk-selected leverage</dt><dd id="momentumLeverage">—</dd></div>
        <div><dt>RSI / ADX</dt><dd id="momentumRsiAdx">—</dd></div>
        <div><dt>Volume</dt><dd id="momentumVolume">—</dd></div>
        <div><dt>Spread</dt><dd id="momentumSpread">—</dd></div>
      </dl>
      <div class="bot-controls momentum-controls"><button class="primary" id="startMomentum">▶ START FAST PAPER</button><button class="danger-btn" id="stopMomentum" disabled>■ STOP NEW ENTRIES</button></div>
      <p class="muted-copy" id="momentumReason">Engineering paper strategy. No live orders, no exchange leverage changes.</p>`;
    if (mt5Card) list.insertBefore(card, mt5Card);
    else list.appendChild(card);
  }

  const positions = momentumEl('positionsList');
  if (positions && !momentumEl('momentumPositionPanel')) {
    const panel = document.createElement('article');
    panel.className = 'section-card';
    panel.id = 'momentumPositionPanel';
    panel.innerHTML = '<div class="section-head"><div><span class="eyebrow">Fast paper</span><h3>BTC Momentum</h3></div><span class="pill neutral" id="momentumPositionBadge">FLAT</span></div><div id="momentumPositionBody"><p>No fast paper position.</p></div><button class="secondary full" id="closeMomentumPosition" disabled>CLOSE FAST PAPER POSITION</button>';
    positions.parentElement.insertBefore(panel, positions);
  }

  const historyList = momentumEl('historyList');
  if (historyList && !momentumEl('momentumHistoryPanel')) {
    const panel = document.createElement('section');
    panel.id = 'momentumHistoryPanel';
    panel.innerHTML = '<div class="section-head"><div><span class="eyebrow">Fast paper ledger</span><h3>Momentum trades</h3></div><span class="pill neutral" id="momentumTradeCount">0 FAST</span></div><div id="momentumHistoryList"><article class="empty-state"><div class="empty-icon">↯</div><h3>No fast paper trades yet</h3><p>The engine waits for a qualified 1m/5m momentum signal.</p></article></div>';
    historyList.parentElement.insertBefore(panel, historyList);
  }

  const riskCard = document.querySelector('.risk-card');
  if (riskCard && !momentumEl('serverSecretStatus')) {
    const row = document.createElement('div');
    row.className = 'setting-row';
    row.innerHTML = '<span>Binance Demo auto-connect<br><small id="serverSecretHelp">Render secrets not checked yet</small></span><strong id="serverSecretStatus">CHECKING</strong>';
    riskCard.appendChild(row);
    const momentumRisk = document.createElement('div');
    momentumRisk.className = 'setting-row';
    momentumRisk.innerHTML = '<span>Fast paper risk<br><small>$10 margin · max planned loss $0.35 · 5x/10x/20x cap</small></span><strong class="positive-text">PAPER</strong>';
    riskCard.appendChild(momentumRisk);
  }

  momentumEl('startMomentum')?.addEventListener('click', startMomentum);
  momentumEl('stopMomentum')?.addEventListener('click', stopMomentum);
  momentumEl('closeMomentumPosition')?.addEventListener('click', closeMomentumPosition);
  disconnectDemo?.addEventListener('click', () => { autoReconnectSuppressed = true; });
}

function updateMomentumState(state) {
  if (!state || typeof state !== 'object') return;
  momentumState = {
    openPosition: state.openPosition || null,
    history: Array.isArray(state.history) ? state.history : [],
    markers: Array.isArray(state.markers) ? state.markers : [],
    signal: state.signal || {},
    realizedPnlUsd: Number(state.realizedPnlUsd || 0),
    unrealizedPnlUsd: Number(state.unrealizedPnlUsd || 0),
    totalPnlUsd: Number(state.totalPnlUsd || 0),
    tradeCount: Number(state.tradeCount || 0),
    winRate: Number(state.winRate || 0),
    reason: state.reason || 'OK',
    event: state.event || 'STATE',
  };
  renderMomentumUi();
}

function renderMomentumUi() {
  const signal = momentumState.signal || {};
  const decision = signal.decision || 'NO_TRADE';
  const status = momentumEl('momentumStatus');
  if (status) {
    status.textContent = momentumRunning ? 'RUNNING' : momentumState.openPosition ? 'MONITORING' : 'OFF';
    status.className = `badge ${momentumRunning || momentumState.openPosition ? 'positive-pill' : 'muted'}`;
  }
  if (momentumEl('momentumDecision')) {
    momentumEl('momentumDecision').textContent = decision;
    momentumEl('momentumDecision').className = decision === 'NO_TRADE' ? 'negative' : 'positive-text';
    momentumEl('momentumScores').textContent = `${Number(signal.longScore || 0)} / ${Number(signal.shortScore || 0)}`;
    momentumEl('momentumRsiAdx').textContent = signal.rsi14 == null ? '—' : `${Number(signal.rsi14).toFixed(1)} / ${Number(signal.adx14 || 0).toFixed(1)}`;
    momentumEl('momentumVolume').textContent = signal.volumeRatio == null ? '—' : `${Number(signal.volumeRatio).toFixed(2)}× avg`;
    momentumEl('momentumSpread').textContent = signal.spreadBps == null ? '—' : `${Number(signal.spreadBps).toFixed(2)} bps`;
    momentumEl('momentumReason').textContent = momentumState.reason || 'Waiting for signal';
  }

  const position = momentumState.openPosition;
  const leverage = position ? `${Number(position.effective_leverage || 0).toFixed(1)}x (cap ${position.leverage_cap}x)` : signal.score ? `${signal.score >= 8 ? 'up to 20x' : signal.score >= 7 ? 'up to 10x' : 'up to 5x'}` : '—';
  if (momentumEl('momentumLeverage')) momentumEl('momentumLeverage').textContent = leverage;
  if (momentumEl('momentumPositionBadge')) momentumEl('momentumPositionBadge').textContent = position ? `${position.side} ${Number(position.effective_leverage).toFixed(1)}x` : 'FLAT';
  if (momentumEl('closeMomentumPosition')) momentumEl('closeMomentumPosition').disabled = !position || !demoSessionToken;

  if (momentumEl('momentumPositionBody')) {
    if (!position) {
      momentumEl('momentumPositionBody').innerHTML = '<p>No fast paper position.</p>';
    } else {
      const pnl = Number(position.unrealized_net_usd || 0);
      momentumEl('momentumPositionBody').innerHTML = `<div class="position-row"><div><strong>BTCUSDT ${escapeHtml(position.side)} · PAPER</strong><small>Entry ${escapeHtml(formatPrice(position.entry_price))} · mark ${escapeHtml(formatPrice(position.mark_price))} · TP ${escapeHtml(formatPrice(position.take_profit_price))} · SL ${escapeHtml(formatPrice(position.stop_price))}</small></div><span class="pnl ${pnl >= 0 ? 'positive-text' : 'negative'}">${escapeHtml(formatUsd(pnl))}</span></div>`;
    }
  }

  if (momentumEl('momentumTradeCount')) momentumEl('momentumTradeCount').textContent = `${momentumState.tradeCount} FAST`;
  if (momentumEl('momentumHistoryList')) {
    if (!momentumState.history.length) {
      momentumEl('momentumHistoryList').innerHTML = '<article class="empty-state"><div class="empty-icon">↯</div><h3>No fast paper trades yet</h3><p>The engine waits for a qualified 1m/5m momentum signal.</p></article>';
    } else {
      momentumEl('momentumHistoryList').innerHTML = [...momentumState.history].reverse().map((trade) => {
        const pnl = Number(trade.net_pnl_usd || 0);
        return `<article class="opportunity-card history-trade"><div class="card-title"><div><strong>BTCUSDT · ${escapeHtml(trade.side)} · FAST PAPER</strong><small>${Number(trade.effective_leverage || 0).toFixed(1)}x · ${escapeHtml(paperTime(trade.entry_time_ms))} → ${escapeHtml(paperTime(trade.exit_time_ms))}</small></div><span class="badge ${pnl >= 0 ? 'positive-pill' : 'muted'}">${escapeHtml(formatUsd(pnl))}</span></div><dl><div><dt>Entry → Exit</dt><dd>${escapeHtml(formatPrice(trade.entry_price))} → ${escapeHtml(formatPrice(trade.exit_price))}</dd></div><div><dt>Notional</dt><dd>${escapeHtml(formatUsd(trade.notional_usd))}</dd></div><div><dt>Fees</dt><dd>${escapeHtml(formatUsd(Number(trade.entry_fee_usd || 0) + Number(trade.exit_fee_usd || 0)))}</dd></div><div><dt>Exit</dt><dd>${escapeHtml(trade.exit_reason)}</dd></div></dl></article>`;
      }).join('');
    }
  }

  const start = momentumEl('startMomentum');
  const stop = momentumEl('stopMomentum');
  if (start) {
    start.disabled = momentumRunning || !hasConnectedBinanceDemo();
    start.textContent = momentumRunning ? '● FAST PAPER RUNNING' : '▶ START FAST PAPER';
  }
  if (stop) stop.disabled = !momentumRunning;
  renderCombinedPaperPnl();
}

function renderCombinedPaperPnl() {
  if (!hasConnectedBinanceDemo()) return;
  const carry = Number(typeof paperState === 'object' ? paperState.totalPnlUsd || 0 : 0);
  const fast = Number(momentumState.totalPnlUsd || 0);
  const total = carry + fast;
  const value = momentumEl('todayPnlValue');
  const detail = momentumEl('todayPnlDetail');
  if (value) {
    value.textContent = formatUsd(total);
    value.className = total >= 0 ? 'positive-text' : 'negative';
  }
  if (detail) detail.textContent = `Carry ${formatUsd(carry)} · Fast ${formatUsd(fast)}`;
}

async function momentumStep(allowEntry) {
  if (!demoSessionToken) return;
  try {
    const state = await postJson('/api/momentum/step', {
      sessionToken: demoSessionToken,
      allowEntry,
    });
    updateMomentumState(state);
    if (!momentumRunning && !momentumState.openPosition) clearMomentumTimer();
    const chartScreen = document.querySelector('[data-screen="chart"]');
    if (chartScreen?.classList.contains('active') && chartProvider.value === 'binance') await refreshChart();
  } catch (error) {
    if (error.status === 401) {
      momentumRunning = false;
      clearMomentumTimer();
      if (serverSecretsConfigured && !autoReconnectSuppressed) await tryServerAutoConnect();
    } else if (momentumEl('momentumReason')) {
      momentumEl('momentumReason').textContent = error.message || 'Fast paper step failed';
    }
  }
}

function clearMomentumTimer() {
  if (momentumTimer !== null) window.clearInterval(momentumTimer);
  momentumTimer = null;
}

async function startMomentum() {
  if (!hasConnectedBinanceDemo()) return;
  momentumRunning = true;
  renderMomentumUi();
  await momentumStep(true);
  clearMomentumTimer();
  momentumTimer = window.setInterval(() => momentumStep(momentumRunning), 15_000);
}

function stopMomentum() {
  momentumRunning = false;
  renderMomentumUi();
  if (momentumState.openPosition) {
    clearMomentumTimer();
    momentumTimer = window.setInterval(() => momentumStep(false), 15_000);
  } else {
    clearMomentumTimer();
  }
}

async function closeMomentumPosition() {
  if (!demoSessionToken || !momentumState.openPosition) return;
  try {
    const state = await postJson('/api/momentum/close', {
      sessionToken: demoSessionToken,
      reason: 'MANUAL_FAST_PAPER_CLOSE',
    });
    updateMomentumState(state);
    if (!momentumRunning) clearMomentumTimer();
    if (chartProvider.value === 'binance') await refreshChart();
  } catch (error) {
    if (momentumEl('momentumReason')) momentumEl('momentumReason').textContent = error.message || 'Fast paper close failed';
  }
}

async function loadMomentumState() {
  if (!demoSessionToken) return;
  try {
    updateMomentumState(await postJson('/api/momentum/state', { sessionToken: demoSessionToken }));
  } catch (_) {
    // Empty state is normal on a fresh process/session.
  }
}

async function checkServerCredentialStatus() {
  try {
    const response = await fetch('/api/demo/credential-status', { cache: 'no-store' });
    const result = await response.json();
    serverSecretsConfigured = Boolean(result.configured);
    const status = momentumEl('serverSecretStatus');
    const help = momentumEl('serverSecretHelp');
    if (status) {
      status.textContent = serverSecretsConfigured ? 'AUTO' : 'MANUAL';
      status.className = serverSecretsConfigured ? 'positive-text' : 'negative';
    }
    if (help) help.textContent = serverSecretsConfigured
      ? 'Render secret configured · Binance key never returns to browser'
      : 'Set EBA_BINANCE_DEMO_API_KEY + EBA_BINANCE_DEMO_API_SECRET once in Render';
  } catch (_) {
    serverSecretsConfigured = false;
  }
}

async function tryServerAutoConnect() {
  if (demoSessionToken || autoReconnectSuppressed) return false;
  try {
    const result = await postJson('/api/demo/autoconnect', {});
    serverSecretsConfigured = Boolean(result.configured);
    if (!result.ok || !result.sessionToken) return false;
    const profile = providerProfiles.find((item) => item.provider === 'binance');
    profile.status = 'connected';
    profile.detail = `Unified Demo auto-connected${result.latencyMs ? ` · ${result.latencyMs} ms` : ''}`;
    profile.balances = result.balances || {};
    demoSessionToken = result.sessionToken;
    autoReconnectSuppressed = false;
    renderConnections();
    await refreshDemoSnapshot();
    await loadPaperState();
    await loadMomentumState();
    renderMomentumUi();
    return true;
  } catch (_) {
    return false;
  }
}

if (typeof applyPaperState === 'function') {
  const baseApplyPaperStateForMomentum = applyPaperState;
  applyPaperState = function applyPaperAndMomentum(state) {
    baseApplyPaperStateForMomentum(state);
    renderCombinedPaperPnl();
  };
}

if (window.EBAChart?.render) {
  const baseChartRenderForMomentum = window.EBAChart.render.bind(window.EBAChart);
  window.EBAChart.render = function renderChartWithMomentum(canvas, candles, markers = [], positions = []) {
    const extraMarkers = chartProvider?.value === 'binance' ? momentumState.markers : [];
    return baseChartRenderForMomentum(canvas, candles, [...markers, ...extraMarkers], positions);
  };
}

installMomentumUi();
renderMomentumUi();
checkServerCredentialStatus().then(() => tryServerAutoConnect());
window.setInterval(() => {
  if (!demoSessionToken && serverSecretsConfigured && !autoReconnectSuppressed) tryServerAutoConnect();
}, 60_000);
