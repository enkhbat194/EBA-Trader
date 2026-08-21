const providerProfiles = [
  {
    id: 'binance-demo',
    provider: 'binance',
    name: 'Binance',
    environment: 'DEMO',
    status: 'disconnected',
    detail: 'Unified Demo not connected',
    accountLabel: null,
    balances: {},
  },
  {
    id: 'mt5-demo',
    provider: 'metatrader5',
    name: 'MetaTrader 5',
    environment: 'DEMO',
    status: 'scaffolded',
    detail: 'Broker bridge coming next',
  },
  {
    id: 'mt4-demo',
    provider: 'metatrader4',
    name: 'MetaTrader 4',
    environment: 'DEMO',
    status: 'scaffolded',
    detail: 'EA / bridge coming next',
  },
];

const navButtons = [...document.querySelectorAll('[data-nav]')];
const screens = [...document.querySelectorAll('.screen')];
const dialog = document.getElementById('connectionDialog');
const providerSelect = document.getElementById('providerSelect');
const connectionResult = document.getElementById('connectionResult');
const apiKeyInput = document.getElementById('apiKey');
const apiSecretInput = document.getElementById('apiSecret');
const mtServerInput = document.getElementById('mtServer');
const mtLoginInput = document.getElementById('mtLogin');
const mtPasswordInput = document.getElementById('mtPassword');
const binanceFields = document.getElementById('binanceFields');
const mtFields = document.getElementById('mtFields');
const dialogTitle = document.getElementById('dialogTitle');
const startBot = document.getElementById('startBot');
const stopBot = document.getElementById('stopBot');
const disconnectDemo = document.getElementById('disconnectDemo');
const botStatus = document.getElementById('botStatus');
const balanceValue = document.getElementById('balanceValue');
const balanceDetail = document.getElementById('balanceDetail');
const todayPnlValue = document.getElementById('todayPnlValue');
const todayPnlDetail = document.getElementById('todayPnlDetail');
const expectedNetValue = document.getElementById('expectedNetValue');
const expectedNetDetail = document.getElementById('expectedNetDetail');
const opportunityCount = document.getElementById('opportunityCount');
const opportunityDetail = document.getElementById('opportunityDetail');
const decisionTitle = document.getElementById('decisionTitle');
const decisionReason = document.getElementById('decisionReason');
const futuresSymbolLabel = document.getElementById('futuresSymbolLabel');
const opportunityStatus = document.getElementById('opportunityStatus');
const netEdgeValue = document.getElementById('netEdgeValue');
const spotBuyValue = document.getElementById('spotBuyValue');
const futuresSellValue = document.getElementById('futuresSellValue');
const grossEdgeValue = document.getElementById('grossEdgeValue');
const feesValue = document.getElementById('feesValue');
const slippageValue = document.getElementById('slippageValue');
const safetyBufferValue = document.getElementById('safetyBufferValue');

let paperBotRunning = false;
let demoSessionToken = null;
let scannerTimer = null;

function navigate(target) {
  screens.forEach((screen) => screen.classList.toggle('active', screen.dataset.screen === target));
  document.querySelectorAll('.bottom-nav [data-nav]').forEach((button) => {
    button.classList.toggle('active', button.dataset.nav === target);
  });
  window.scrollTo({ top: 0, behavior: 'auto' });
}

navButtons.forEach((button) => button.addEventListener('click', () => navigate(button.dataset.nav)));

function providerIcon(provider) {
  if (provider === 'binance') return 'B';
  if (provider === 'metatrader5') return '5';
  return '4';
}

function escapeHtml(value) {
  const element = document.createElement('span');
  element.textContent = String(value ?? '');
  return element.innerHTML;
}

function hasConnectedBinanceDemo() {
  return Boolean(demoSessionToken) && providerProfiles.some(
    (profile) => profile.provider === 'binance' && profile.environment === 'DEMO' && profile.status === 'connected',
  );
}

function connectedBinanceProfile() {
  return providerProfiles.find(
    (profile) => profile.provider === 'binance' && profile.environment === 'DEMO' && profile.status === 'connected',
  );
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
  if (!Number.isFinite(Number(value))) return '—';
  return `$${Number(value).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatBps(value) {
  if (!Number.isFinite(Number(value))) return '—';
  return `${Number(value).toFixed(2)} bps`;
}

function clearScannerTimer() {
  if (scannerTimer !== null) {
    window.clearInterval(scannerTimer);
    scannerTimer = null;
  }
}

function resetOpportunity(message = 'Waiting for Demo snapshot') {
  opportunityCount.textContent = '0';
  opportunityDetail.textContent = message;
  expectedNetValue.textContent = '—';
  expectedNetDetail.textContent = 'Waiting for fee-aware snapshot';
  decisionTitle.textContent = 'NO TRADE';
  decisionReason.textContent = message;
  futuresSymbolLabel.textContent = 'Binance Spot ↔ USD-M Quarterly';
  opportunityStatus.textContent = 'NO_TRADE';
  opportunityStatus.className = 'badge muted';
  netEdgeValue.textContent = '—';
  netEdgeValue.className = 'negative';
  spotBuyValue.textContent = 'Waiting for quote';
  futuresSellValue.textContent = 'Waiting for quote';
  grossEdgeValue.textContent = '—';
  feesValue.textContent = '—';
  slippageValue.textContent = '—';
  safetyBufferValue.textContent = '—';
}

function lockDemoSession(message) {
  demoSessionToken = null;
  paperBotRunning = false;
  clearScannerTimer();
  const profile = providerProfiles.find((item) => item.provider === 'binance');
  if (profile) {
    profile.status = 'disconnected';
    profile.detail = message;
    profile.accountLabel = null;
    profile.balances = {};
  }
  resetOpportunity(message);
  renderConnections();
}

function syncBotAvailability() {
  const connected = hasConnectedBinanceDemo();
  if (!connected) paperBotRunning = false;

  if (!connected) {
    startBot.disabled = true;
    stopBot.disabled = true;
    startBot.textContent = 'CONNECT BINANCE DEMO';
    botStatus.textContent = 'BOT LOCKED';
    balanceValue.textContent = '—';
    balanceDetail.textContent = 'Connect Binance Unified Demo';
    todayPnlValue.textContent = '—';
    todayPnlDetail.textContent = 'No paper session';
    return;
  }

  const profile = connectedBinanceProfile();
  const spotUsdt = Number(profile?.balances?.spot?.USDT);
  const usdmUsdt = Number(profile?.balances?.usdm?.USDT);
  const hasSpot = Number.isFinite(spotUsdt);
  const hasUsdm = Number.isFinite(usdmUsdt);

  if (hasSpot && hasUsdm) {
    balanceValue.textContent = formatUsd(spotUsdt + usdmUsdt);
    balanceDetail.textContent = `Spot ${formatUsd(spotUsdt)} · USD-M ${formatUsd(usdmUsdt)}`;
  } else {
    balanceValue.textContent = '—';
    balanceDetail.textContent = 'Connected · balance data incomplete';
  }

  if (paperBotRunning) {
    startBot.disabled = true;
    stopBot.disabled = false;
    startBot.textContent = '● PAPER SCANNER RUNNING';
    botStatus.textContent = 'PAPER RUNNING';
    todayPnlValue.textContent = '$0.00';
    todayPnlDetail.textContent = 'Read-only scanner · no orders';
  } else {
    startBot.disabled = false;
    stopBot.disabled = true;
    startBot.textContent = '▶ START PAPER SCANNER';
    botStatus.textContent = 'BOT OFF';
    todayPnlValue.textContent = '—';
    todayPnlDetail.textContent = 'No paper session';
  }
}

function renderConnections() {
  const markup = providerProfiles.map((profile) => `
    <article class="connection-card" data-connection="${escapeHtml(profile.id)}">
      <div class="provider-icon ${profile.provider}">${escapeHtml(providerIcon(profile.provider))}</div>
      <div class="connection-copy">
        <strong>${escapeHtml(profile.name)} <span class="pill demo">${escapeHtml(profile.environment)}</span></strong>
        <small>${escapeHtml(profile.detail)}</small>
      </div>
      <span class="connection-status ${profile.status === 'connected' ? 'connected' : ''}">${escapeHtml(profile.status.toUpperCase())}</span>
    </article>
  `).join('');
  document.getElementById('connectionList').innerHTML = markup;
  document.getElementById('homeConnections').innerHTML = markup;
  const online = providerProfiles.filter((profile) => profile.status === 'connected').length;
  document.getElementById('connectionSummary').textContent = `${online} CONNECTION${online === 1 ? '' : 'S'}`;
  disconnectDemo.hidden = !hasConnectedBinanceDemo();

  document.querySelectorAll('[data-connection]').forEach((card) => {
    card.addEventListener('click', () => {
      const profile = providerProfiles.find((item) => item.id === card.dataset.connection);
      if (!profile) return;
      providerSelect.value = profile.provider;
      updateProviderFields();
      dialog.showModal();
    });
  });
  syncBotAvailability();
}

function updateProviderFields() {
  const provider = providerSelect.value;
  const isBinance = provider === 'binance';
  binanceFields.hidden = !isBinance;
  mtFields.hidden = isBinance;
  disconnectDemo.hidden = !(isBinance && hasConnectedBinanceDemo());
  dialogTitle.textContent = isBinance
    ? 'Binance Demo'
    : `${provider === 'metatrader5' ? 'MetaTrader 5' : 'MetaTrader 4'} Demo`;
  connectionResult.className = 'connection-result';
  connectionResult.textContent = 'Not tested';
}

providerSelect.addEventListener('change', updateProviderFields);
document.getElementById('addConnection').addEventListener('click', () => {
  providerSelect.value = 'binance';
  updateProviderFields();
  dialog.showModal();
});

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

function clearCredentialInputs() {
  apiKeyInput.value = '';
  apiSecretInput.value = '';
  mtServerInput.value = '';
  mtLoginInput.value = '';
  mtPasswordInput.value = '';
}

function applyDemoSnapshot(result) {
  const estimate = result.estimate || null;
  const candidate = result.decision === 'PAPER_CANDIDATE';
  const reasons = Array.isArray(result.reasonCodes) ? result.reasonCodes : [];

  opportunityCount.textContent = candidate ? '1' : '0';
  opportunityDetail.textContent = candidate ? 'Fee-aware paper candidate' : 'No qualified setup';
  decisionTitle.textContent = candidate ? 'PAPER CANDIDATE' : 'NO TRADE';
  decisionReason.textContent = reasons.length ? reasons.join(' · ') : 'Snapshot evaluated';
  opportunityStatus.textContent = result.decision || 'NO_TRADE';
  opportunityStatus.className = candidate ? 'badge positive-pill' : 'badge muted';
  futuresSymbolLabel.textContent = result.futuresSymbol
    ? `Binance Spot ↔ ${result.futuresSymbol}`
    : 'Binance Spot ↔ USD-M Quarterly';

  if (!estimate) {
    netEdgeValue.textContent = '—';
    netEdgeValue.className = 'negative';
    expectedNetValue.textContent = '—';
    expectedNetDetail.textContent = 'No executable Demo delivery snapshot';
    spotBuyValue.textContent = '—';
    futuresSellValue.textContent = '—';
    grossEdgeValue.textContent = '—';
    feesValue.textContent = '—';
    slippageValue.textContent = '—';
    safetyBufferValue.textContent = '—';
    return;
  }

  netEdgeValue.textContent = formatBps(estimate.screening_net_edge_bps);
  netEdgeValue.className = candidate ? 'positive-text' : 'negative';
  expectedNetValue.textContent = formatUsd(Number(estimate.screening_net_usd || 0));
  expectedNetDetail.textContent = `${formatBps(estimate.screening_net_edge_bps)} after reserves`;
  spotBuyValue.textContent = formatPrice(estimate.spot_entry_vwap);
  futuresSellValue.textContent = formatPrice(estimate.futures_entry_vwap);
  grossEdgeValue.textContent = formatBps(estimate.gross_edge_bps);
  const totalFees = Number(estimate.entry_fee_usd || 0) + Number(estimate.reserved_exit_fee_usd || 0);
  feesValue.textContent = formatUsd(totalFees);
  slippageValue.textContent = formatUsd(Number(estimate.reserved_exit_slippage_usd || 0));
  safetyBufferValue.textContent = formatUsd(Number(estimate.safety_buffer_usd || 0));
}

async function refreshDemoSnapshot() {
  if (!demoSessionToken) return;
  decisionReason.textContent = 'Refreshing Demo fee-aware snapshot…';
  try {
    const result = await postJson('/api/demo/snapshot', { sessionToken: demoSessionToken });
    applyDemoSnapshot(result);
  } catch (error) {
    if (error.status === 401) {
      lockDemoSession('Demo session expired · reconnect');
      return;
    }
    resetOpportunity(error.message || 'Demo snapshot failed');
  }
}

async function testConnection() {
  const provider = providerSelect.value;
  connectionResult.className = 'connection-result';
  connectionResult.textContent = 'Testing…';

  let credentials;
  if (provider === 'binance') {
    if (!apiKeyInput.value.trim() || !apiSecretInput.value.trim()) {
      connectionResult.classList.add('bad');
      connectionResult.textContent = 'Binance Demo API key and secret are required.';
      return;
    }
    credentials = {
      apiKey: apiKeyInput.value.trim(),
      apiSecret: apiSecretInput.value.trim(),
    };
  } else {
    if (!mtServerInput.value.trim() || !mtLoginInput.value.trim() || !mtPasswordInput.value) {
      connectionResult.classList.add('bad');
      connectionResult.textContent = 'Broker server, login and password are required.';
      return;
    }
    credentials = {
      server: mtServerInput.value.trim(),
      login: mtLoginInput.value.trim(),
      password: mtPasswordInput.value,
    };
  }

  try {
    const result = await postJson('/api/connections/test', {
      provider,
      environment: 'demo',
      credentials,
    });
    const sessionReady = provider !== 'binance' ? result.ok : Boolean(result.ok && result.sessionToken);
    connectionResult.classList.add(sessionReady ? 'good' : 'bad');
    connectionResult.textContent = sessionReady
      ? result.message
      : (result.message || 'Demo session was not created');

    const profile = providerProfiles.find((item) => item.provider === provider);
    if (profile) {
      profile.status = sessionReady ? 'connected' : 'error';
      profile.accountLabel = sessionReady ? result.accountLabel : null;
      profile.balances = sessionReady && result.balances ? result.balances : {};
      profile.detail = sessionReady
        ? `Unified Demo connected${result.latencyMs ? ` · ${result.latencyMs} ms` : ''}`
        : connectionResult.textContent;
    }

    if (provider === 'binance') {
      demoSessionToken = sessionReady ? result.sessionToken : null;
      if (!sessionReady) {
        paperBotRunning = false;
        clearScannerTimer();
      }
    }

    renderConnections();
    if (sessionReady && provider === 'binance') await refreshDemoSnapshot();
  } catch (error) {
    connectionResult.classList.add('bad');
    connectionResult.textContent = error instanceof Error ? error.message : 'Connection test failed';
    const profile = providerProfiles.find((item) => item.provider === provider);
    if (profile) {
      profile.status = 'error';
      profile.accountLabel = null;
      profile.balances = {};
      profile.detail = connectionResult.textContent;
    }
    if (provider === 'binance') {
      demoSessionToken = null;
      paperBotRunning = false;
      clearScannerTimer();
    }
    renderConnections();
  } finally {
    credentials = null;
    clearCredentialInputs();
  }
}

document.getElementById('testConnection').addEventListener('click', testConnection);

disconnectDemo.addEventListener('click', async () => {
  const token = demoSessionToken;
  if (!token) {
    lockDemoSession('Unified Demo disconnected');
    return;
  }
  try {
    await postJson('/api/demo/disconnect', { sessionToken: token });
    lockDemoSession('Unified Demo disconnected');
    connectionResult.className = 'connection-result good';
    connectionResult.textContent = 'Demo session disconnected.';
  } catch (error) {
    lockDemoSession('Disconnected locally · server session will expire automatically');
    connectionResult.className = 'connection-result bad';
    connectionResult.textContent = error instanceof Error ? error.message : 'Disconnect failed';
  }
});

dialog.addEventListener('close', () => {
  clearCredentialInputs();
  connectionResult.className = 'connection-result';
  connectionResult.textContent = 'Not tested';
});

startBot.addEventListener('click', async () => {
  if (!hasConnectedBinanceDemo()) {
    syncBotAvailability();
    return;
  }
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

renderConnections();
resetOpportunity('Connect Binance Unified Demo to start scanning');

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('./sw.js').catch(() => {}));
}
