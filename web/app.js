const extraStyle = document.createElement('link');
extraStyle.rel = 'stylesheet';
extraStyle.href = './m18_2.css';
document.head.appendChild(extraStyle);

const providerProfiles = [
  {
    id: 'binance-demo',
    provider: 'binance',
    name: 'Binance',
    environment: 'DEMO',
    status: 'disconnected',
    detail: 'Unified Demo not connected',
    balances: {},
  },
  {
    id: 'mt5-demo',
    provider: 'metatrader5',
    name: 'MetaTrader 5',
    environment: 'DEMO',
    status: 'disconnected',
    detail: 'Windows Demo bridge not paired',
  },
];

const $ = (id) => document.getElementById(id);
const navButtons = [...document.querySelectorAll('[data-nav]')];
const screens = [...document.querySelectorAll('.screen')];
const dialog = $('connectionDialog');
const providerSelect = $('providerSelect');
const connectionResult = $('connectionResult');
const apiKeyInput = $('apiKey');
const apiSecretInput = $('apiSecret');
const binanceFields = $('binanceFields');
const mt5Fields = $('mt5Fields');
const dialogTitle = $('dialogTitle');
const startBot = $('startBot');
const stopBot = $('stopBot');
const disconnectDemo = $('disconnectDemo');
const createMt5Pair = $('createMt5Pair');
const mt5PairPanel = $('mt5PairPanel');
const mt5PairTokenInput = $('mt5PairToken');
const mt5Command = $('mt5Command');
const disconnectMt5Button = $('disconnectMt5');
const chartProvider = $('chartProvider');
const chartSymbol = $('chartSymbol');
const chartTimeframe = $('chartTimeframe');

let paperBotRunning = false;
let demoSessionToken = null;
let mt5PairToken = null;
let mt5Snapshot = null;
let scannerTimer = null;
let mt5Timer = null;
let chartTimer = null;
let lastBinanceDecision = 'NO_TRADE';

function escapeHtml(value) {
  const element = document.createElement('span');
  element.textContent = String(value ?? '');
  return element.innerHTML;
}

function providerIcon(provider) {
  return provider === 'binance' ? 'B' : '5';
}

function formatUsd(value) {
  if (!Number.isFinite(Number(value))) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(value));
}

function formatPrice(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  return number >= 1000
    ? `$${number.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : `$${number.toFixed(number >= 10 ? 2 : 4)}`;
}

function formatBps(value) {
  if (!Number.isFinite(Number(value))) return '—';
  return `${Number(value).toFixed(2)} bps`;
}

async function postJson(path, payload) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
    body: JSON.stringify(payload),
  });
  const body = await response.json();
  if (!response.ok) {
    const error = new Error(body.message || `Request failed (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return body;
}

function hasConnectedBinanceDemo() {
  return Boolean(demoSessionToken) && providerProfiles.some(
    (profile) => profile.provider === 'binance' && profile.status === 'connected',
  );
}

function hasConnectedMt5() {
  return Boolean(mt5PairToken && mt5Snapshot) && providerProfiles.some(
    (profile) => profile.provider === 'metatrader5' && profile.status === 'connected',
  );
}

function navigate(target) {
  screens.forEach((screen) => screen.classList.toggle('active', screen.dataset.screen === target));
  document.querySelectorAll('.bottom-nav [data-nav]').forEach((button) => {
    button.classList.toggle('active', button.dataset.nav === target);
  });
  window.scrollTo({ top: 0, behavior: 'auto' });
  if (target === 'chart') refreshChart();
}

navButtons.forEach((button) => button.addEventListener('click', () => navigate(button.dataset.nav)));

function clearScannerTimer() {
  if (scannerTimer !== null) window.clearInterval(scannerTimer);
  scannerTimer = null;
}

function clearMt5Timer() {
  if (mt5Timer !== null) window.clearInterval(mt5Timer);
  mt5Timer = null;
}

function clearChartTimer() {
  if (chartTimer !== null) window.clearInterval(chartTimer);
  chartTimer = null;
}

function resetOpportunity(message = 'Waiting for Demo snapshot') {
  $('opportunityCount').textContent = '0';
  $('opportunityDetail').textContent = message;
  $('expectedNetValue').textContent = '—';
  $('expectedNetDetail').textContent = 'Waiting for fee-aware snapshot';
  $('decisionTitle').textContent = 'NO TRADE';
  $('decisionReason').textContent = message;
  $('futuresSymbolLabel').textContent = 'Binance Spot ↔ USD-M Quarterly';
  $('opportunityStatus').textContent = 'NO_TRADE';
  $('opportunityStatus').className = 'badge muted';
  $('netEdgeValue').textContent = '—';
  $('netEdgeValue').className = 'negative';
  $('spotBuyValue').textContent = 'Waiting for quote';
  $('futuresSellValue').textContent = 'Waiting for quote';
  $('grossEdgeValue').textContent = '—';
  $('feesValue').textContent = '—';
  $('slippageValue').textContent = '—';
  $('safetyBufferValue').textContent = '—';
  lastBinanceDecision = 'NO_TRADE';
}

function connectionMarkup(profile) {
  const stateClass = profile.status === 'connected' ? 'connected' : profile.status;
  return `
    <article class="connection-card" data-connection="${escapeHtml(profile.id)}">
      <div class="provider-icon ${escapeHtml(profile.provider)}">${escapeHtml(providerIcon(profile.provider))}</div>
      <div class="connection-copy">
        <strong>${escapeHtml(profile.name)} <span class="pill demo">${escapeHtml(profile.environment)}</span></strong>
        <small>${escapeHtml(profile.detail)}</small>
      </div>
      <span class="connection-status ${escapeHtml(stateClass)}">${escapeHtml(profile.status.toUpperCase())}</span>
    </article>`;
}

function syncAccountOverview() {
  const binance = providerProfiles.find((profile) => profile.provider === 'binance');
  const spot = Number(binance?.balances?.spot?.USDT);
  const usdm = Number(binance?.balances?.usdm?.USDT);
  const binanceTotal = Number.isFinite(spot) && Number.isFinite(usdm) ? spot + usdm : null;
  const mt5Account = mt5Snapshot?.account || null;
  const mt5Balance = Number(mt5Account?.balance);
  const mt5Usd = mt5Account?.currency === 'USD' && Number.isFinite(mt5Balance) ? mt5Balance : null;

  if (binanceTotal !== null && mt5Usd !== null) {
    $('balanceValue').textContent = formatUsd(binanceTotal + mt5Usd);
    $('balanceDetail').textContent = `Binance ${formatUsd(binanceTotal)} · MT5 ${formatUsd(mt5Usd)}`;
  } else if (binanceTotal !== null) {
    $('balanceValue').textContent = formatUsd(binanceTotal);
    $('balanceDetail').textContent = `Binance Spot ${formatUsd(spot)} · USD-M ${formatUsd(usdm)}`;
  } else if (mt5Usd !== null) {
    $('balanceValue').textContent = formatUsd(mt5Usd);
    $('balanceDetail').textContent = `MT5 ${escapeHtml(mt5Account.server || 'Demo')} · equity ${formatUsd(mt5Account.equity)}`;
  } else {
    $('balanceValue').textContent = '—';
    $('balanceDetail').textContent = 'Connect Binance or MT5 Demo';
  }
}

function syncBotAvailability() {
  const connected = hasConnectedBinanceDemo();
  if (!connected) paperBotRunning = false;
  if (!connected) {
    startBot.disabled = true;
    stopBot.disabled = true;
    startBot.textContent = 'CONNECT BINANCE DEMO';
    $('botStatus').textContent = 'BOT LOCKED';
    $('todayPnlValue').textContent = '—';
    $('todayPnlDetail').textContent = 'No paper session';
    return;
  }
  if (paperBotRunning) {
    startBot.disabled = true;
    stopBot.disabled = false;
    startBot.textContent = '● PAPER SCANNER RUNNING';
    $('botStatus').textContent = 'PAPER RUNNING';
    $('todayPnlValue').textContent = '$0.00';
    $('todayPnlDetail').textContent = 'Read-only scanner · no orders';
  } else {
    startBot.disabled = false;
    stopBot.disabled = true;
    startBot.textContent = '▶ START PAPER SCANNER';
    $('botStatus').textContent = 'BOT OFF';
    $('todayPnlValue').textContent = '—';
    $('todayPnlDetail').textContent = 'No paper session';
  }
}

function renderConnections() {
  const markup = providerProfiles.map(connectionMarkup).join('');
  $('connectionList').innerHTML = markup;
  $('homeConnections').innerHTML = markup;
  const online = providerProfiles.filter((profile) => profile.status === 'connected').length;
  $('connectionSummary').textContent = `${online} CONNECTION${online === 1 ? '' : 'S'}`;
  disconnectDemo.hidden = !hasConnectedBinanceDemo();
  syncAccountOverview();
  syncBotAvailability();

  document.querySelectorAll('[data-connection]').forEach((card) => {
    card.addEventListener('click', () => {
      const profile = providerProfiles.find((item) => item.id === card.dataset.connection);
      if (!profile) return;
      providerSelect.value = profile.provider;
      updateProviderFields();
      dialog.showModal();
    });
  });
}

function updateProviderFields() {
  const isBinance = providerSelect.value === 'binance';
  binanceFields.hidden = !isBinance;
  mt5Fields.hidden = isBinance;
  disconnectDemo.hidden = !(isBinance && hasConnectedBinanceDemo());
  dialogTitle.textContent = isBinance ? 'Binance Demo' : 'MetaTrader 5 Demo Bridge';
  connectionResult.className = 'connection-result';
  connectionResult.textContent = isBinance ? 'Binance Demo connection' : 'MT5 local bridge pairing';
  if (!isBinance && mt5PairToken) {
    mt5PairPanel.hidden = false;
    mt5PairTokenInput.value = mt5PairToken;
  }
}

providerSelect.addEventListener('change', updateProviderFields);
$('addConnection').addEventListener('click', () => {
  providerSelect.value = 'binance';
  updateProviderFields();
  dialog.showModal();
});

function lockBinance(message) {
  demoSessionToken = null;
  paperBotRunning = false;
  clearScannerTimer();
  const profile = providerProfiles.find((item) => item.provider === 'binance');
  profile.status = 'disconnected';
  profile.detail = message;
  profile.balances = {};
  resetOpportunity(message);
  renderConnections();
}

function applyDemoSnapshot(result) {
  const estimate = result.estimate || null;
  const candidate = result.decision === 'PAPER_CANDIDATE';
  const reasons = Array.isArray(result.reasonCodes) ? result.reasonCodes : [];
  lastBinanceDecision = result.decision || 'NO_TRADE';
  $('opportunityCount').textContent = candidate ? '1' : '0';
  $('opportunityDetail').textContent = candidate ? 'Fee-aware paper candidate' : 'No qualified setup';
  $('decisionTitle').textContent = candidate ? 'PAPER CANDIDATE' : 'NO TRADE';
  $('decisionReason').textContent = reasons.length ? reasons.join(' · ') : 'Snapshot evaluated';
  $('opportunityStatus').textContent = lastBinanceDecision;
  $('opportunityStatus').className = candidate ? 'badge positive-pill' : 'badge muted';
  $('futuresSymbolLabel').textContent = result.futuresSymbol
    ? `Binance Spot ↔ ${result.futuresSymbol}`
    : 'Binance Spot ↔ USD-M Quarterly';
  if (!estimate) {
    $('netEdgeValue').textContent = '—';
    $('expectedNetValue').textContent = '—';
    $('expectedNetDetail').textContent = 'No executable Demo delivery snapshot';
    return;
  }
  $('netEdgeValue').textContent = formatBps(estimate.screening_net_edge_bps);
  $('netEdgeValue').className = candidate ? 'positive-text' : 'negative';
  $('expectedNetValue').textContent = formatUsd(Number(estimate.screening_net_usd || 0));
  $('expectedNetDetail').textContent = `${formatBps(estimate.screening_net_edge_bps)} after reserves`;
  $('spotBuyValue').textContent = formatPrice(estimate.spot_entry_vwap);
  $('futuresSellValue').textContent = formatPrice(estimate.futures_entry_vwap);
  $('grossEdgeValue').textContent = formatBps(estimate.gross_edge_bps);
  const totalFees = Number(estimate.entry_fee_usd || 0) + Number(estimate.reserved_exit_fee_usd || 0);
  $('feesValue').textContent = formatUsd(totalFees);
  $('slippageValue').textContent = formatUsd(Number(estimate.reserved_exit_slippage_usd || 0));
  $('safetyBufferValue').textContent = formatUsd(Number(estimate.safety_buffer_usd || 0));
  if (chartProvider.value === 'binance') $('chartDecisionBadge').textContent = lastBinanceDecision;
}

async function refreshDemoSnapshot() {
  if (!demoSessionToken) return;
  try {
    const result = await postJson('/api/demo/snapshot', { sessionToken: demoSessionToken });
    applyDemoSnapshot(result);
  } catch (error) {
    if (error.status === 401) lockBinance('Binance Demo session expired · reconnect');
    else resetOpportunity(error.message || 'Demo snapshot failed');
  }
}

async function testBinanceConnection() {
  if (!apiKeyInput.value.trim() || !apiSecretInput.value.trim()) {
    connectionResult.className = 'connection-result bad';
    connectionResult.textContent = 'Binance Demo API key and secret are required.';
    return;
  }
  const credentials = { apiKey: apiKeyInput.value.trim(), apiSecret: apiSecretInput.value.trim() };
  connectionResult.className = 'connection-result';
  connectionResult.textContent = 'Testing Binance Demo…';
  try {
    const result = await postJson('/api/connections/test', {
      provider: 'binance', environment: 'demo', credentials,
    });
    const ready = Boolean(result.ok && result.sessionToken);
    const profile = providerProfiles.find((item) => item.provider === 'binance');
    profile.status = ready ? 'connected' : 'error';
    profile.detail = ready ? `Unified Demo connected${result.latencyMs ? ` · ${result.latencyMs} ms` : ''}` : result.message;
    profile.balances = ready ? (result.balances || {}) : {};
    demoSessionToken = ready ? result.sessionToken : null;
    connectionResult.className = `connection-result ${ready ? 'good' : 'bad'}`;
    connectionResult.textContent = ready ? result.message : (result.message || 'Connection failed');
    renderConnections();
    if (ready) await refreshDemoSnapshot();
  } catch (error) {
    lockBinance(error.message || 'Binance connection failed');
    connectionResult.className = 'connection-result bad';
    connectionResult.textContent = error.message || 'Binance connection failed';
  } finally {
    credentials.apiKey = '';
    credentials.apiSecret = '';
    apiKeyInput.value = '';
    apiSecretInput.value = '';
  }
}

$('testConnection').addEventListener('click', testBinanceConnection);

disconnectDemo.addEventListener('click', async () => {
  const token = demoSessionToken;
  lockBinance('Binance Demo disconnected');
  if (!token) return;
  try { await postJson('/api/demo/disconnect', { sessionToken: token }); } catch (_) { /* local lock wins */ }
});

function buildMt5Command(token) {
  return `py mt5_demo_bridge.py --eba-url "${window.location.origin}" --pair-token "${token}" --symbols XAUUSD,XAGUSD,USOIL --interval 15`;
}

async function createMt5Pairing() {
  connectionResult.className = 'connection-result';
  connectionResult.textContent = 'Creating secure MT5 pair token…';
  try {
    const result = await postJson('/api/mt5/pair', {});
    mt5PairToken = result.pairToken;
    mt5PairTokenInput.value = mt5PairToken;
    mt5Command.value = buildMt5Command(mt5PairToken);
    mt5PairPanel.hidden = false;
    const profile = providerProfiles.find((item) => item.provider === 'metatrader5');
    profile.status = 'waiting';
    profile.detail = 'Waiting for Windows MT5 Demo bridge';
    connectionResult.textContent = 'Pair code ready · start the Windows bridge';
    renderConnections();
    clearMt5Timer();
    mt5Timer = window.setInterval(refreshMt5State, 5000);
  } catch (error) {
    connectionResult.className = 'connection-result bad';
    connectionResult.textContent = error.message || 'Could not create MT5 pair';
  }
}

createMt5Pair.addEventListener('click', createMt5Pairing);

$('copyMt5Command').addEventListener('click', async () => {
  if (!mt5Command.value) return;
  try {
    await navigator.clipboard.writeText(mt5Command.value);
    connectionResult.className = 'connection-result good';
    connectionResult.textContent = 'Windows command copied';
  } catch (_) {
    mt5Command.select();
    connectionResult.textContent = 'Select and copy the command manually';
  }
});

function lockMt5(message) {
  mt5PairToken = null;
  mt5Snapshot = null;
  clearMt5Timer();
  const profile = providerProfiles.find((item) => item.provider === 'metatrader5');
  profile.status = 'disconnected';
  profile.detail = message;
  mt5PairPanel.hidden = true;
  mt5PairTokenInput.value = '';
  mt5Command.value = '';
  renderMt5Positions();
  renderMt5MarketCard();
  renderConnections();
}

async function refreshMt5State() {
  if (!mt5PairToken) return;
  try {
    const result = await postJson('/api/mt5/state', { pairToken: mt5PairToken });
    const profile = providerProfiles.find((item) => item.provider === 'metatrader5');
    if (result.connected && result.snapshot) {
      mt5Snapshot = result.snapshot;
      profile.status = 'connected';
      const account = mt5Snapshot.account || {};
      profile.detail = `${account.server || 'MT5 Demo'} · ${result.heartbeatAgeSeconds ?? 0}s heartbeat`;
      connectionResult.className = 'connection-result good';
      connectionResult.textContent = `MT5 Demo connected · account ${account.login || '—'}`;
    } else {
      mt5Snapshot = null;
      profile.status = result.state === 'stale' ? 'stale' : 'waiting';
      profile.detail = result.state === 'stale' ? 'MT5 bridge heartbeat stale' : 'Waiting for Windows MT5 Demo bridge';
    }
    renderMt5Positions();
    renderMt5MarketCard();
    renderConnections();
    if (chartProvider.value === 'metatrader5') await refreshChart();
  } catch (error) {
    if (error.status === 401) lockMt5('MT5 pair expired · create a new pair');
  }
}

async function disconnectMt5() {
  const token = mt5PairToken;
  lockMt5('MT5 Demo bridge disconnected');
  if (!token) return;
  try { await postJson('/api/mt5/disconnect', { pairToken: token }); } catch (_) { /* fail closed locally */ }
}

disconnectMt5Button.addEventListener('click', disconnectMt5);

function renderMt5MarketCard() {
  const badge = $('mt5OpportunityStatus');
  const detail = $('mt5MarketDetail');
  if (!hasConnectedMt5()) {
    badge.textContent = mt5PairToken ? 'WAITING BRIDGE' : 'BRIDGE OFFLINE';
    detail.textContent = 'Connect the MT5 Demo bridge to stream broker quotes and charts.';
    return;
  }
  badge.textContent = 'STREAMING';
  badge.className = 'badge positive-pill';
  const ticks = mt5Snapshot.ticks || {};
  const chunks = ['XAUUSD', 'XAGUSD', 'USOIL'].map((symbol) => {
    const tick = ticks[symbol];
    return tick ? `${symbol} ${formatPrice(tick.bid)}/${formatPrice(tick.ask)}` : `${symbol} unavailable`;
  });
  detail.textContent = chunks.join(' · ');
}

function renderMt5Positions() {
  const positions = Array.isArray(mt5Snapshot?.positions) ? mt5Snapshot.positions : [];
  $('openPositionCount').textContent = String(positions.length);
  const totalPnl = positions.reduce((sum, item) => sum + Number(item.profit || 0), 0);
  $('unrealizedValue').textContent = positions.length ? formatUsd(totalPnl) : '—';
  $('unrealizedValue').className = totalPnl >= 0 ? 'positive-text' : 'negative';
  if (!positions.length) {
    $('positionsList').innerHTML = '<article class="empty-state"><div class="empty-icon">◎</div><h3>No visible positions</h3><p>MT5 bridge positions and future EBA paper positions will appear here.</p></article>';
    return;
  }
  $('positionsList').innerHTML = `<div class="mini-list">${positions.map((item) => {
    const side = Number(item.type) === 1 ? 'SELL' : 'BUY';
    const pnl = Number(item.profit || 0);
    return `<div class="position-row"><div><strong>${escapeHtml(item.symbol)} · ${side} ${escapeHtml(item.volume)}</strong><small>Entry ${escapeHtml(formatPrice(item.priceOpen))} · Current ${escapeHtml(formatPrice(item.priceCurrent))}</small></div><span class="pnl ${pnl >= 0 ? 'positive-text' : 'negative'}">${escapeHtml(formatUsd(pnl))}</span></div>`;
  }).join('')}</div>`;
}

function updateChartSymbols() {
  const provider = chartProvider.value;
  const symbols = provider === 'binance' ? ['BTCUSDT'] : ['XAUUSD', 'XAGUSD', 'USOIL'];
  const current = chartSymbol.value;
  chartSymbol.innerHTML = symbols.map((symbol) => `<option value="${symbol}">${symbol}</option>`).join('');
  if (symbols.includes(current)) chartSymbol.value = current;
  $('chartSubtitle').textContent = provider === 'binance' ? 'Binance Demo' : 'MetaTrader 5 Demo broker';
}

function mt5PositionsForChart(symbol) {
  const actual = mt5Snapshot?.resolvedSymbols?.[symbol] || symbol;
  const positions = Array.isArray(mt5Snapshot?.positions) ? mt5Snapshot.positions : [];
  return positions.filter((item) => item.symbol === actual || item.symbol === symbol);
}

function renderChartPositionSummary(provider, symbol, positions) {
  $('chartDecisionBadge').textContent = provider === 'binance' ? lastBinanceDecision : 'READ_ONLY';
  if (!positions.length) {
    $('chartPositionSummary').innerHTML = '<p>No open position on this chart. EBA trade markers will appear here when the paper-execution layer opens a simulated trade.</p>';
    return;
  }
  $('chartPositionSummary').innerHTML = positions.map((item) => {
    const side = Number(item.type) === 1 ? 'SELL' : 'BUY';
    return `<div class="position-row"><div><strong>${escapeHtml(symbol)} ${side}</strong><small>Entry ${escapeHtml(formatPrice(item.priceOpen))} · MT5 position</small></div><span class="pnl ${Number(item.profit || 0) >= 0 ? 'positive-text' : 'negative'}">${escapeHtml(formatUsd(item.profit || 0))}</span></div>`;
  }).join('');
}

async function refreshChart() {
  const provider = chartProvider.value;
  const symbol = chartSymbol.value;
  const timeframe = chartTimeframe.value;
  $('chartTitle').textContent = `${symbol} · ${timeframe}`;
  $('chartStatus').textContent = 'Refreshing market data…';
  if (provider === 'metatrader5' && !mt5PairToken) {
    $('chartStatus').textContent = 'Connect MT5 Demo bridge first.';
    window.EBAChart?.render($('marketChart'), []);
    return;
  }
  try {
    const payload = { provider, symbol, timeframe, limit: 120 };
    if (provider === 'metatrader5') payload.pairToken = mt5PairToken;
    const result = await postJson('/api/chart', payload);
    const candles = Array.isArray(result.candles) ? result.candles : [];
    const positions = provider === 'metatrader5' ? mt5PositionsForChart(symbol) : [];
    window.EBAChart?.render($('marketChart'), candles, result.markers || [], positions);
    if (candles.length) {
      const last = candles[candles.length - 1];
      const previous = candles[Math.max(0, candles.length - 2)];
      $('chartLastPrice').textContent = formatPrice(last.close);
      const change = previous?.close ? ((Number(last.close) / Number(previous.close)) - 1) * 100 : 0;
      $('chartChange').textContent = `${change >= 0 ? '+' : ''}${change.toFixed(3)}% last bar`;
      $('chartChange').className = change >= 0 ? 'positive-text' : 'negative';
    }
    $('chartStatus').textContent = provider === 'binance'
      ? `Binance Demo · ${candles.length} candles`
      : `MT5 bridge · ${candles.length} candles · ${result.bridgeHeartbeatAgeSeconds ?? '—'}s heartbeat`;
    renderChartPositionSummary(provider, symbol, positions);
  } catch (error) {
    $('chartStatus').textContent = error.message || 'Chart refresh failed';
    window.EBAChart?.render($('marketChart'), []);
  }
}

chartProvider.addEventListener('change', () => { updateChartSymbols(); refreshChart(); });
chartSymbol.addEventListener('change', refreshChart);
chartTimeframe.addEventListener('change', refreshChart);

window.addEventListener('resize', () => {
  const chartScreen = document.querySelector('[data-screen="chart"]');
  if (chartScreen?.classList.contains('active')) refreshChart();
});

document.querySelectorAll('[data-chart-market]').forEach((button) => {
  button.addEventListener('click', () => {
    chartProvider.value = 'metatrader5';
    updateChartSymbols();
    chartSymbol.value = button.dataset.chartMarket;
    navigate('chart');
  });
});

startBot.addEventListener('click', async () => {
  if (!hasConnectedBinanceDemo()) return;
  paperBotRunning = true;
  syncBotAvailability();
  await refreshDemoSnapshot();
  clearScannerTimer();
  scannerTimer = window.setInterval(refreshDemoSnapshot, 15_000);
});

stopBot.addEventListener('click', () => {
  paperBotRunning = false;
  clearScannerTimer();
  syncBotAvailability();
});

$('refreshApp').addEventListener('click', async () => {
  await Promise.allSettled([refreshDemoSnapshot(), refreshMt5State(), refreshChart()]);
});

dialog.addEventListener('close', () => {
  apiKeyInput.value = '';
  apiSecretInput.value = '';
  connectionResult.className = 'connection-result';
  connectionResult.textContent = 'Not connected';
});

updateChartSymbols();
renderConnections();
renderMt5Positions();
renderMt5MarketCard();
resetOpportunity('Connect Binance Unified Demo to start scanning');
refreshChart();
clearChartTimer();
chartTimer = window.setInterval(() => {
  const chartScreen = document.querySelector('[data-screen="chart"]');
  if (chartScreen?.classList.contains('active')) refreshChart();
}, 10_000);

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('./sw.js').catch(() => {}));
}
