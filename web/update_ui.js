const EBA_INSTALLED_APP_VERSION = '0.9.1';
const EBA_INSTALLED_RELEASE = 'M18.6';
const EBA_INSTALLED_PWA_CACHE = 'eba-trader-ui-v10';
let ebaLatestAppInfo = null;
let ebaReloadOnControllerChange = false;
let ebaRunnerSyncTimer = null;

function ebaUpdateEl(id) {
  return document.getElementById(id);
}

function ebaShortSha(value) {
  const text = String(value || '').trim();
  if (!text || text === 'unknown') return 'unknown';
  return text.slice(0, 7);
}

function ebaAge(value) {
  const ms = Number(value);
  if (!Number.isFinite(ms) || ms <= 0) return 'not yet';
  const seconds = Math.max(0, Math.round((Date.now() - ms) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  return `${minutes}m ago`;
}

function ebaInstallUpdateCenter() {
  const settingsScreen = document.querySelector('[data-screen="settings"]');
  const riskCard = document.querySelector('.risk-card');
  if (!settingsScreen || !riskCard || ebaUpdateEl('appUpdateCard')) return;

  const card = document.createElement('article');
  card.className = 'section-card';
  card.id = 'appUpdateCard';
  card.innerHTML = `
    <div class="section-head">
      <div><span class="eyebrow">App update</span><h3>Version & update status</h3></div>
      <span class="pill neutral" id="appUpdateStatus">CHECKING</span>
    </div>
    <div class="setting-row"><span>Installed UI</span><strong id="installedAppVersion">${EBA_INSTALLED_APP_VERSION} · ${EBA_INSTALLED_RELEASE}</strong></div>
    <div class="setting-row"><span>Server release</span><strong id="serverAppVersion">Checking…</strong></div>
    <div class="setting-row"><span>Server build</span><strong id="serverBuildSha">—</strong></div>
    <div class="setting-row"><span>PWA cache</span><strong id="pwaCacheVersion">${EBA_INSTALLED_PWA_CACHE}</strong></div>
    <div class="setting-row"><span>Server scanner<br><small>PWA may be closed; server keeps scanning while the Render instance is awake.</small></span><strong id="serverRunnerStatus">CHECKING</strong></div>
    <div class="setting-row"><span>Last server scans<br><small id="serverRunnerScans">Waiting for runner status…</small></span><strong id="serverRunnerMode">—</strong></div>
    <div class="setting-row"><span>Released</span><strong id="appReleasedAt">—</strong></div>
    <div class="setting-row"><span>What's new<br><small id="appChangeSummary">Checking server release notes…</small></span><strong id="appChangeCount">—</strong></div>
    <button type="button" class="secondary full" id="checkAppUpdate">CHECK FOR UPDATE</button>
    <button type="button" class="primary full" id="reloadLatestApp" hidden>RELOAD LATEST VERSION</button>`;
  riskCard.insertAdjacentElement('afterend', card);

  ebaUpdateEl('checkAppUpdate')?.addEventListener('click', ebaCheckForUpdate);
  ebaUpdateEl('reloadLatestApp')?.addEventListener('click', ebaReloadLatest);
}

function ebaRenderUpdateInfo(info) {
  if (!info || typeof info !== 'object') return;
  ebaLatestAppInfo = info;

  const serverVersion = String(info.appVersion || 'unknown');
  const serverRelease = String(info.release || 'unknown');
  const serverCache = String(info.pwaCache || 'unknown');
  const needsUpdate = serverVersion !== EBA_INSTALLED_APP_VERSION
    || serverRelease !== EBA_INSTALLED_RELEASE
    || serverCache !== EBA_INSTALLED_PWA_CACHE;

  const status = ebaUpdateEl('appUpdateStatus');
  if (status) {
    status.textContent = needsUpdate ? 'UPDATE AVAILABLE' : 'UP TO DATE';
    status.className = needsUpdate ? 'pill demo' : 'pill positive-pill';
  }
  if (ebaUpdateEl('serverAppVersion')) ebaUpdateEl('serverAppVersion').textContent = `${serverVersion} · ${serverRelease}`;
  if (ebaUpdateEl('serverBuildSha')) ebaUpdateEl('serverBuildSha').textContent = ebaShortSha(info.buildSha);
  if (ebaUpdateEl('pwaCacheVersion')) ebaUpdateEl('pwaCacheVersion').textContent = `${EBA_INSTALLED_PWA_CACHE} / server ${serverCache}`;
  if (ebaUpdateEl('appReleasedAt')) ebaUpdateEl('appReleasedAt').textContent = String(info.releasedAt || 'unknown');

  const changes = Array.isArray(info.changes) ? info.changes : [];
  if (ebaUpdateEl('appChangeCount')) ebaUpdateEl('appChangeCount').textContent = `${changes.length} CHANGES`;
  if (ebaUpdateEl('appChangeSummary')) {
    ebaUpdateEl('appChangeSummary').innerHTML = changes.length
      ? changes.map((item) => `• ${escapeHtml(String(item))}`).join('<br>')
      : 'No release notes supplied.';
  }

  const reload = ebaUpdateEl('reloadLatestApp');
  if (reload) reload.hidden = !needsUpdate;
}

async function ebaFetchAppInfo() {
  const response = await fetch('/api/app-info', { cache: 'no-store' });
  if (!response.ok) throw new Error(`Update check failed (${response.status})`);
  return response.json();
}

async function ebaCheckForUpdate() {
  const button = ebaUpdateEl('checkAppUpdate');
  const status = ebaUpdateEl('appUpdateStatus');
  if (button) button.disabled = true;
  if (status) {
    status.textContent = 'CHECKING';
    status.className = 'pill neutral';
  }
  try {
    if ('serviceWorker' in navigator) {
      const registration = await navigator.serviceWorker.getRegistration();
      if (registration) await registration.update();
    }
    ebaRenderUpdateInfo(await ebaFetchAppInfo());
    await ebaSyncRunnerStatus();
  } catch (error) {
    if (status) {
      status.textContent = 'CHECK FAILED';
      status.className = 'pill danger';
    }
    if (ebaUpdateEl('appChangeSummary')) ebaUpdateEl('appChangeSummary').textContent = error.message || 'Could not check update status.';
  } finally {
    if (button) button.disabled = false;
  }
}

async function ebaReloadLatest() {
  const button = ebaUpdateEl('reloadLatestApp');
  if (button) {
    button.disabled = true;
    button.textContent = 'UPDATING…';
  }
  try {
    if ('serviceWorker' in navigator) {
      const registration = await navigator.serviceWorker.getRegistration();
      if (registration) {
        ebaReloadOnControllerChange = true;
        await registration.update();
        if (registration.waiting) registration.waiting.postMessage({ type: 'SKIP_WAITING' });
      }
    }
  } finally {
    window.setTimeout(() => window.location.reload(), 900);
  }
}

async function ebaFetchRunnerStatus() {
  const response = await fetch('/api/runner/status', { cache: 'no-store' });
  const result = await response.json();
  if (!response.ok) throw new Error(result.message || `Runner status failed (${response.status})`);
  return result;
}

function ebaApplyRunnerStatus(result) {
  if (!result || typeof result !== 'object') return;

  clearScannerTimer();
  if (typeof clearMomentumTimer === 'function') clearMomentumTimer();
  paperBotRunning = Boolean(result.carryRunning);
  momentumRunning = Boolean(result.fastRunning);

  if (result.snapshot) applyDemoSnapshot(result.snapshot);
  syncBotAvailability();
  if (result.carryState) applyPaperState(result.carryState);
  if (result.fastState) updateMomentumState(result.fastState);

  const healthy = Boolean(result.threadAlive) && !result.lastError;
  const runnerStatus = ebaUpdateEl('serverRunnerStatus');
  if (runnerStatus) {
    runnerStatus.textContent = healthy ? 'ACTIVE' : result.threadAlive ? 'ERROR' : 'OFFLINE';
    runnerStatus.className = healthy ? 'positive-text' : 'negative';
  }
  const runnerMode = ebaUpdateEl('serverRunnerMode');
  if (runnerMode) {
    const modes = [];
    if (result.carryRunning) modes.push('CARRY');
    if (result.fastRunning) modes.push('FAST');
    runnerMode.textContent = modes.length ? modes.join(' + ') : 'STOPPED';
  }
  const runnerScans = ebaUpdateEl('serverRunnerScans');
  if (runnerScans) {
    const error = result.lastError ? ` · error: ${result.lastError}` : '';
    runnerScans.textContent = `Carry ${ebaAge(result.lastCarryScanAtMs)} · Fast ${ebaAge(result.lastFastScanAtMs)}${error}`;
  }
}

async function ebaSyncRunnerStatus() {
  try {
    const result = await ebaFetchRunnerStatus();
    ebaApplyRunnerStatus(result);
    return result;
  } catch (error) {
    const runnerStatus = ebaUpdateEl('serverRunnerStatus');
    if (runnerStatus) {
      runnerStatus.textContent = 'UNREACHABLE';
      runnerStatus.className = 'negative';
    }
    return null;
  }
}

async function ebaRunnerCommand(path, payload) {
  const result = await postJson(path, payload);
  ebaApplyRunnerStatus(result);
  return result;
}

// M18.6: scanner execution lives on the server. These overrides only refresh UI.
refreshDemoSnapshot = async function refreshServerScannerUi() {
  if (!demoSessionToken) {
    await ebaSyncRunnerStatus();
    return;
  }
  try {
    const [snapshot, runner] = await Promise.all([
      postJson('/api/demo/snapshot', { sessionToken: demoSessionToken }),
      ebaFetchRunnerStatus(),
    ]);
    applyDemoSnapshot(snapshot);
    ebaApplyRunnerStatus(runner);
  } catch (error) {
    if (error.status === 401) lockBinance('Binance Demo session expired · reconnect');
    else resetOpportunity(error.message || 'Demo/server-runner refresh failed');
  }
};

loadPaperState = async function loadServerPaperState() {
  await ebaSyncRunnerStatus();
};

loadMomentumState = async function loadServerMomentumState() {
  await ebaSyncRunnerStatus();
};

momentumStep = async function refreshServerMomentumState() {
  await ebaSyncRunnerStatus();
};

// Capture scanner-control clicks before the older browser-timer listeners run.
document.addEventListener('click', async (event) => {
  const button = event.target.closest('button');
  if (!button) return;
  const handled = new Set([
    'startBot',
    'stopBot',
    'startMomentum',
    'stopMomentum',
    'closePaperPosition',
    'closeMomentumPosition',
  ]);
  if (!handled.has(button.id)) return;

  event.preventDefault();
  event.stopImmediatePropagation();
  button.disabled = true;
  try {
    if (button.id === 'startBot') {
      await ebaRunnerCommand('/api/runner/start', { carry: true });
    } else if (button.id === 'stopBot') {
      await ebaRunnerCommand('/api/runner/stop', { carry: true, closeCarry: true });
    } else if (button.id === 'startMomentum') {
      await ebaRunnerCommand('/api/runner/start', { fast: true });
    } else if (button.id === 'stopMomentum') {
      await ebaRunnerCommand('/api/runner/stop', { fast: true });
    } else if (button.id === 'closePaperPosition') {
      await ebaRunnerCommand('/api/runner/close', { target: 'carry' });
    } else if (button.id === 'closeMomentumPosition') {
      await ebaRunnerCommand('/api/runner/close', { target: 'fast' });
    }
  } catch (error) {
    if (ebaUpdateEl('serverRunnerScans')) {
      ebaUpdateEl('serverRunnerScans').textContent = error.message || 'Server runner command failed';
    }
  } finally {
    await ebaSyncRunnerStatus();
  }
}, true);

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (ebaReloadOnControllerChange) window.location.reload();
  });
}

ebaInstallUpdateCenter();
ebaCheckForUpdate();
ebaSyncRunnerStatus();
if (ebaRunnerSyncTimer !== null) window.clearInterval(ebaRunnerSyncTimer);
ebaRunnerSyncTimer = window.setInterval(ebaSyncRunnerStatus, 5000);
