let paperState = {
  openPosition: null,
  history: [],
  markers: [],
  realizedPnlUsd: 0,
  unrealizedPnlUsd: 0,
  totalPnlUsd: 0,
};

const paperEl = (id) => document.getElementById(id);

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
  };

  paperEl('todayPnlValue').textContent = formatUsd(paperState.totalPnlUsd);
  paperEl('todayPnlValue').className = paperState.totalPnlUsd >= 0 ? 'positive-text' : 'negative';
  paperEl('todayPnlDetail').textContent = paperState.openPosition
    ? `Paper open · unrealized ${formatUsd(paperState.unrealizedPnlUsd)}`
    : `Realized paper ${formatUsd(paperState.realizedPnlUsd)}`;

  const closeButton = paperEl('closePaperPosition');
  closeButton.disabled = !paperState.openPosition || !demoSessionToken;
  stopBot.textContent = paperState.openPosition && paperBotRunning ? '■ STOP & CLOSE' : '■ STOP';

  renderCombinedPositions();
  renderPaperHistory();
}

function paperPositionMarkup(position) {
  const pnl = Number(position.unrealized_net_usd || 0);
  return `<div class="position-row paper-position"><div><strong>EBA PAPER · BTC CASH & CARRY</strong><small>Spot BUY ${escapeHtml(formatPrice(position.spot_entry_vwap))} · Futures SELL ${escapeHtml(position.futures_symbol)} @ ${escapeHtml(formatPrice(position.futures_entry_vwap))} · ${escapeHtml(position.quantity_btc)} BTC</small></div><span class="pnl ${pnl >= 0 ? 'positive-text' : 'negative'}">${escapeHtml(formatUsd(pnl))}</span></div>`;
}

function mt5PositionMarkup(item) {
  const side = Number(item.type) === 1 ? 'SELL' : 'BUY';
  const pnl = Number(item.profit || 0);
  return `<div class="position-row"><div><strong>MT5 READ · ${escapeHtml(item.symbol)} · ${side} ${escapeHtml(item.volume)}</strong><small>Entry ${escapeHtml(formatPrice(item.priceOpen))} · Current ${escapeHtml(formatPrice(item.priceCurrent))}</small></div><span class="pnl ${pnl >= 0 ? 'positive-text' : 'negative'}">${escapeHtml(formatUsd(pnl))}</span></div>`;
}

function renderCombinedPositions() {
  const mt5Positions = Array.isArray(mt5Snapshot?.positions) ? mt5Snapshot.positions : [];
  const rows = [];
  if (paperState.openPosition) rows.push(paperPositionMarkup(paperState.openPosition));
  rows.push(...mt5Positions.map(mt5PositionMarkup));

  const openCount = (paperState.openPosition ? 1 : 0) + mt5Positions.length;
  paperEl('openPositionCount').textContent = String(openCount);

  let visiblePnl = paperState.unrealizedPnlUsd;
  if (mt5Snapshot?.account?.currency === 'USD') {
    visiblePnl += mt5Positions.reduce((sum, item) => sum + Number(item.profit || 0), 0);
  }
  paperEl('unrealizedValue').textContent = openCount ? formatUsd(visiblePnl) : '—';
  paperEl('unrealizedValue').className = visiblePnl >= 0 ? 'positive-text' : 'negative';

  if (!rows.length) {
    paperEl('positionsList').innerHTML = '<article class="empty-state"><div class="empty-icon">◎</div><h3>No visible positions</h3><p>EBA paper positions and MT5 read-only positions will appear here.</p></article>';
    return;
  }
  paperEl('positionsList').innerHTML = `<div class="mini-list">${rows.join('')}</div>`;
}

function renderPaperHistory() {
  const history = paperState.history;
  paperEl('paperTradeCount').textContent = `${history.length} PAPER`;
  if (!history.length) {
    paperEl('historyList').innerHTML = '<article class="empty-state"><div class="empty-icon">↺</div><h3>No EBA paper trades yet</h3><p>A trade is recorded only after a qualified virtual paired position closes.</p></article>';
    return;
  }
  const rows = [...history].reverse().map((trade) => {
    const pnl = Number(trade.net_pnl_usd || 0);
    return `<article class="opportunity-card history-trade"><div class="card-title"><div><strong>BTC / USDT · PAPER</strong><small>${escapeHtml(trade.futures_symbol)} · ${escapeHtml(paperTime(trade.entry_time_ms))} → ${escapeHtml(paperTime(trade.exit_time_ms))}</small></div><span class="badge ${pnl >= 0 ? 'positive-pill' : 'muted'}">${escapeHtml(formatUsd(pnl))}</span></div><dl><div><dt>Spot</dt><dd>${escapeHtml(formatPrice(trade.spot_entry_vwap))} → ${escapeHtml(formatPrice(trade.spot_exit_vwap))}</dd></div><div><dt>Futures</dt><dd>${escapeHtml(formatPrice(trade.futures_entry_vwap))} → ${escapeHtml(formatPrice(trade.futures_exit_vwap))}</dd></div><div><dt>Gross P&amp;L</dt><dd>${escapeHtml(formatUsd(trade.gross_pnl_usd))}</dd></div><div><dt>Fees</dt><dd>${escapeHtml(formatUsd(Number(trade.entry_fee_usd || 0) + Number(trade.exit_fee_usd || 0)))}</dd></div><div><dt>NET P&amp;L</dt><dd class="${pnl >= 0 ? 'positive-text' : 'negative'}">${escapeHtml(formatUsd(pnl))}</dd></div><div><dt>Exit</dt><dd>${escapeHtml(trade.exit_reason)}</dd></div></dl></article>`;
  });
  paperEl('historyList').innerHTML = rows.join('');
}

const originalRenderMt5Positions = renderMt5Positions;
renderMt5Positions = function renderAllPositions() {
  originalRenderMt5Positions();
  renderCombinedPositions();
};

const originalSyncBotAvailability = syncBotAvailability;
syncBotAvailability = function syncBotAndPaper() {
  originalSyncBotAvailability();
  if (hasConnectedBinanceDemo() && (paperState.openPosition || paperState.history.length)) {
    paperEl('todayPnlValue').textContent = formatUsd(paperState.totalPnlUsd);
    paperEl('todayPnlValue').className = paperState.totalPnlUsd >= 0 ? 'positive-text' : 'negative';
    paperEl('todayPnlDetail').textContent = paperState.openPosition
      ? `Paper open · unrealized ${formatUsd(paperState.unrealizedPnlUsd)}`
      : `Realized paper ${formatUsd(paperState.realizedPnlUsd)}`;
  }
};

refreshDemoSnapshot = async function refreshDemoAndPaper() {
  if (!demoSessionToken) return;
  try {
    if (paperBotRunning) {
      const result = await postJson('/api/paper/step', {
        sessionToken: demoSessionToken,
        allowEntry: true,
      });
      applyDemoSnapshot(result.snapshot);
      applyPaperState(result.paper);
      if (chartProvider.value === 'binance') await refreshChart();
      return;
    }
    const result = await postJson('/api/demo/snapshot', { sessionToken: demoSessionToken });
    applyDemoSnapshot(result);
  } catch (error) {
    if (error.status === 401) {
      paperState = { openPosition: null, history: [], markers: [], realizedPnlUsd: 0, unrealizedPnlUsd: 0, totalPnlUsd: 0 };
      lockBinance('Binance Demo session expired · reconnect');
    } else {
      resetOpportunity(error.message || 'Demo/paper snapshot failed');
    }
  }
};

async function loadPaperState() {
  if (!demoSessionToken) return;
  try {
    const state = await postJson('/api/paper/state', { sessionToken: demoSessionToken });
    applyPaperState(state);
  } catch (_) {
    // A missing state is fail-closed and does not affect Binance connection state.
  }
}

async function closePaperPosition(reason = 'MANUAL_PAPER_CLOSE') {
  if (!demoSessionToken || !paperState.openPosition) return;
  const button = paperEl('closePaperPosition');
  button.disabled = true;
  button.textContent = 'CLOSING PAPER…';
  try {
    const result = await postJson('/api/paper/close', {
      sessionToken: demoSessionToken,
      reason,
    });
    applyDemoSnapshot(result.snapshot);
    applyPaperState(result.paper);
    if (chartProvider.value === 'binance') await refreshChart();
  } catch (error) {
    paperEl('decisionReason').textContent = error.message || 'Paper close failed';
  } finally {
    button.textContent = 'CLOSE PAPER POSITION';
    button.disabled = !paperState.openPosition;
  }
}

paperEl('closePaperPosition').addEventListener('click', () => closePaperPosition());

// The base STOP listener runs first and stops new scanning. If a virtual paper
// position exists, STOP also closes it using the next executable close-side quote.
stopBot.addEventListener('click', async () => {
  if (paperState.openPosition) await closePaperPosition('SCANNER_STOP_CLOSE');
});

const originalLockBinance = lockBinance;
lockBinance = function lockBinanceAndPaper(message) {
  paperState = { openPosition: null, history: [], markers: [], realizedPnlUsd: 0, unrealizedPnlUsd: 0, totalPnlUsd: 0 };
  originalLockBinance(message);
  renderCombinedPositions();
  renderPaperHistory();
};

refreshChart = async function refreshChartWithPaper() {
  const provider = chartProvider.value;
  const symbol = chartSymbol.value;
  const timeframe = chartTimeframe.value;
  paperEl('chartTitle').textContent = `${symbol} · ${timeframe}`;
  paperEl('chartStatus').textContent = 'Refreshing market data…';
  if (provider === 'metatrader5' && !mt5PairToken) {
    paperEl('chartStatus').textContent = 'Connect MT5 Demo bridge first.';
    window.EBAChart?.render(paperEl('marketChart'), []);
    return;
  }
  try {
    const payload = { provider, symbol, timeframe, limit: 120 };
    if (provider === 'metatrader5') payload.pairToken = mt5PairToken;
    if (provider === 'binance' && demoSessionToken) payload.sessionToken = demoSessionToken;
    const result = await postJson('/api/chart', payload);
    const candles = Array.isArray(result.candles) ? result.candles : [];
    let positions = [];
    if (provider === 'metatrader5') {
      positions = mt5PositionsForChart(symbol);
    } else if (result.paper?.openPosition) {
      const open = result.paper.openPosition;
      positions = [{
        priceOpen: open.spot_entry_vwap,
        type: 0,
        profit: open.unrealized_net_usd,
        side: 'buy',
      }];
      applyPaperState(result.paper);
    }
    window.EBAChart?.render(paperEl('marketChart'), candles, result.markers || [], positions);
    if (candles.length) {
      const last = candles[candles.length - 1];
      const previous = candles[Math.max(0, candles.length - 2)];
      paperEl('chartLastPrice').textContent = formatPrice(last.close);
      const change = previous?.close ? ((Number(last.close) / Number(previous.close)) - 1) * 100 : 0;
      paperEl('chartChange').textContent = `${change >= 0 ? '+' : ''}${change.toFixed(3)}% last bar`;
      paperEl('chartChange').className = change >= 0 ? 'positive-text' : 'negative';
    }
    paperEl('chartStatus').textContent = provider === 'binance'
      ? `Binance Demo · ${candles.length} candles · paper markers ${Array.isArray(result.markers) ? result.markers.length : 0}`
      : `MT5 bridge · ${candles.length} candles · ${result.bridgeHeartbeatAgeSeconds ?? '—'}s heartbeat`;

    if (provider === 'binance' && result.paper?.openPosition) {
      const open = result.paper.openPosition;
      paperEl('chartDecisionBadge').textContent = 'PAPER_OPEN';
      paperEl('chartPositionSummary').innerHTML = `<div class="position-row"><div><strong>EBA PAPER BTC</strong><small>Spot entry ${escapeHtml(formatPrice(open.spot_entry_vwap))} · Futures ${escapeHtml(open.futures_symbol)} short ${escapeHtml(formatPrice(open.futures_entry_vwap))}</small></div><span class="pnl ${Number(open.unrealized_net_usd || 0) >= 0 ? 'positive-text' : 'negative'}">${escapeHtml(formatUsd(open.unrealized_net_usd || 0))}</span></div>`;
    } else {
      renderChartPositionSummary(provider, symbol, positions);
    }
  } catch (error) {
    paperEl('chartStatus').textContent = error.message || 'Chart refresh failed';
    window.EBAChart?.render(paperEl('marketChart'), []);
  }
};

// If Binance was connected before this UI module loaded, recover its paper state.
loadPaperState();
renderCombinedPositions();
renderPaperHistory();
