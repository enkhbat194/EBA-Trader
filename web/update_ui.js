const EBA_INSTALLED_APP_VERSION = '0.8.0';
const EBA_INSTALLED_RELEASE = 'M18.4';
const EBA_INSTALLED_PWA_CACHE = 'eba-trader-ui-v8';
let ebaLatestAppInfo = null;
let ebaReloadOnControllerChange = false;

function ebaUpdateEl(id) {
  return document.getElementById(id);
}

function ebaShortSha(value) {
  const text = String(value || '').trim();
  if (!text || text === 'unknown') return 'unknown';
  return text.slice(0, 7);
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

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (ebaReloadOnControllerChange) window.location.reload();
  });
}

ebaInstallUpdateCenter();
ebaCheckForUpdate();
