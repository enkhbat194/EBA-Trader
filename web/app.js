const providerProfiles = [
  { id: 'binance-demo', provider: 'binance', name: 'Binance', environment: 'DEMO', status: 'disconnected', detail: 'Spot + USD-M Testnet not connected', accountLabel: null, balances: {} },
  { id: 'mt5-demo', provider: 'metatrader5', name: 'MetaTrader 5', environment: 'DEMO', status: 'scaffolded', detail: 'Broker bridge coming next' },
  { id: 'mt4-demo', provider: 'metatrader4', name: 'MetaTrader 4', environment: 'DEMO', status: 'scaffolded', detail: 'EA / bridge coming next' },
];

const navButtons = [...document.querySelectorAll('[data-nav]')];
const screens = [...document.querySelectorAll('.screen')];
const dialog = document.getElementById('connectionDialog');
const providerSelect = document.getElementById('providerSelect');
const connectionResult = document.getElementById('connectionResult');
const apiKeyInput = document.getElementById('apiKey');
const apiSecretInput = document.getElementById('apiSecret');
const futuresApiKeyInput = document.getElementById('futuresApiKey');
const futuresApiSecretInput = document.getElementById('futuresApiSecret');
const mtServerInput = document.getElementById('mtServer');
const mtLoginInput = document.getElementById('mtLogin');
const mtPasswordInput = document.getElementById('mtPassword');
const binanceFields = document.getElementById('binanceFields');
const mtFields = document.getElementById('mtFields');
const dialogTitle = document.getElementById('dialogTitle');
const startBot = document.getElementById('startBot');
const stopBot = document.getElementById('stopBot');
const botStatus = document.getElementById('botStatus');
const balanceValue = document.getElementById('balanceValue');
const balanceDetail = document.getElementById('balanceDetail');
const todayPnlValue = document.getElementById('todayPnlValue');
const todayPnlDetail = document.getElementById('todayPnlDetail');
const expectedNetValue = document.getElementById('expectedNetValue');
const expectedNetDetail = document.getElementById('expectedNetDetail');

let paperBotRunning = false;

function navigate(target) {
  screens.forEach((screen) => screen.classList.toggle('active', screen.dataset.screen === target));
  document.querySelectorAll('.bottom-nav [data-nav]').forEach((button) => {
    button.classList.toggle('active', button.dataset.nav === target);
  });
  window.scrollTo({ top: 0, behavior: 'instant' });
}

navButtons.forEach((button) => button.addEventListener('click', () => navigate(button.dataset.nav)));

function providerIcon(provider) {
  if (provider === 'binance') return 'B';
  if (provider === 'metatrader5') return '5';
  return '4';
}

function hasConnectedBinanceDemo() {
  return providerProfiles.some(
    (profile) => profile.provider === 'binance' && profile.environment === 'DEMO' && profile.status === 'connected',
  );
}

function connectedBinanceProfile() {
  return providerProfiles.find(
    (profile) => profile.provider === 'binance' && profile.environment === 'DEMO' && profile.status === 'connected',
  );
}

function formatUsd(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
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
    balanceDetail.textContent = 'Connect Spot + USD-M Demo';
    todayPnlValue.textContent = '—';
    todayPnlDetail.textContent = 'No paper session';
    expectedNetValue.textContent = '—';
    expectedNetDetail.textContent = 'Waiting for fee-aware snapshot';
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
  expectedNetValue.textContent = '—';
  expectedNetDetail.textContent = 'Waiting for fee-aware snapshot';

  if (paperBotRunning) {
    startBot.disabled = true;
    stopBot.disabled = false;
    startBot.textContent = '● PAPER BOT RUNNING';
    botStatus.textContent = 'PAPER RUNNING';
    todayPnlValue.textContent = '$0.00';
    todayPnlDetail.textContent = 'Paper session active';
  } else {
    startBot.disabled = false;
    stopBot.disabled = true;
    startBot.textContent = '▶ START PAPER BOT';
    botStatus.textContent = 'BOT OFF';
    todayPnlValue.textContent = '—';
    todayPnlDetail.textContent = 'No paper session';
  }
}

function renderConnections() {
  const markup = providerProfiles.map((profile) => `
    <article class="connection-card" data-connection="${profile.id}">
      <div class="provider-icon ${profile.provider}">${providerIcon(profile.provider)}</div>
      <div class="connection-copy">
        <strong>${profile.name} <span class="pill demo">${profile.environment}</span></strong>
        <small>${profile.detail}</small>
      </div>
      <span class="connection-status ${profile.status === 'connected' ? 'connected' : ''}">${profile.status.toUpperCase()}</span>
    </article>
  `).join('');
  document.getElementById('connectionList').innerHTML = markup;
  document.getElementById('homeConnections').innerHTML = markup;
  const online = providerProfiles.filter((profile) => profile.status === 'connected').length;
  document.getElementById('connectionSummary').textContent = `${online} CONNECTION${online === 1 ? '' : 'S'}`;

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

async function callConnectionTest(provider, credentials) {
  const response = await fetch('/api/connections/test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
    body: JSON.stringify({ provider, environment: 'demo', credentials }),
  });
  const payload = await response.json();
  if (!response.ok && !payload.message) throw new Error(`Connection test failed (${response.status})`);
  return payload;
}

async function testConnection() {
  const provider = providerSelect.value;
  connectionResult.className = 'connection-result';
  connectionResult.textContent = 'Testing…';

  let credentials;
  if (provider === 'binance') {
    const missingSpot = !apiKeyInput.value.trim() || !apiSecretInput.value.trim();
    const missingFutures = !futuresApiKeyInput.value.trim() || !futuresApiSecretInput.value.trim();
    if (missingSpot || missingFutures) {
      connectionResult.classList.add('bad');
      connectionResult.textContent = 'Spot and USD-M Futures Testnet API keys/secrets are all required.';
      return;
    }
    credentials = {
      apiKey: apiKeyInput.value.trim(),
      apiSecret: apiSecretInput.value.trim(),
      futuresApiKey: futuresApiKeyInput.value.trim(),
      futuresApiSecret: futuresApiSecretInput.value.trim(),
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
    const result = await callConnectionTest(provider, credentials);
    connectionResult.classList.add(result.ok ? 'good' : 'bad');
    connectionResult.textContent = result.message;
    const profile = providerProfiles.find((item) => item.provider === provider);
    if (profile) {
      profile.status = result.ok ? 'connected' : 'error';
      profile.accountLabel = result.ok ? result.accountLabel : null;
      profile.balances = result.ok && result.balances ? result.balances : {};
      profile.detail = result.ok
        ? `Spot + USD-M Demo connected${result.latencyMs ? ` · ${result.latencyMs} ms` : ''}`
        : result.message;
      renderConnections();
    }
  } catch (error) {
    connectionResult.classList.add('bad');
    connectionResult.textContent = error instanceof Error ? error.message : 'Connection test failed';
    const profile = providerProfiles.find((item) => item.provider === provider);
    if (profile) {
      profile.status = 'error';
      profile.accountLabel = null;
      profile.balances = {};
      profile.detail = connectionResult.textContent;
      renderConnections();
    }
  } finally {
    credentials = null;
  }
}

document.getElementById('testConnection').addEventListener('click', testConnection);

dialog.addEventListener('close', () => {
  apiKeyInput.value = '';
  apiSecretInput.value = '';
  futuresApiKeyInput.value = '';
  futuresApiSecretInput.value = '';
  mtServerInput.value = '';
  mtLoginInput.value = '';
  mtPasswordInput.value = '';
  connectionResult.className = 'connection-result';
  connectionResult.textContent = 'Not tested';
});

startBot.addEventListener('click', () => {
  if (!hasConnectedBinanceDemo()) {
    syncBotAvailability();
    return;
  }
  paperBotRunning = true;
  syncBotAvailability();
});

stopBot.addEventListener('click', () => {
  paperBotRunning = false;
  syncBotAvailability();
});

renderConnections();

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('./sw.js').catch(() => {}));
}
