(() => {
  const byId = (id) => document.getElementById(id);
  let credentialStatus = null;
  let saveInFlight = false;

  function installCredentialPanel() {
    const fields = byId('binanceFields');
    const keyInput = byId('apiKey');
    if (!fields || !keyInput || byId('savedDemoCredentialPanel')) return;

    const panel = document.createElement('div');
    panel.id = 'savedDemoCredentialPanel';
    panel.className = 'security-note';
    panel.innerHTML = `
      <strong id="savedDemoCredentialTitle">Saved Demo credential</strong>
      <div id="savedDemoCredentialDetail">Checking encrypted Linode vault…</div>`;
    keyInput.closest('label')?.insertAdjacentElement('beforebegin', panel);

    const deleteButton = document.createElement('button');
    deleteButton.type = 'button';
    deleteButton.id = 'deleteSavedDemoCredential';
    deleteButton.className = 'danger-btn full';
    deleteButton.textContent = 'DELETE SAVED DEMO KEY';
    deleteButton.hidden = true;
    byId('testConnection')?.insertAdjacentElement('afterend', deleteButton);
    deleteButton.addEventListener('click', deleteSavedCredential);
  }

  function renderCredentialStatus(status) {
    credentialStatus = status || null;
    const configured = Boolean(status?.configured);
    const title = byId('savedDemoCredentialTitle');
    const detail = byId('savedDemoCredentialDetail');
    const saveButton = byId('testConnection');
    const deleteButton = byId('deleteSavedDemoCredential');
    const keyInput = byId('apiKey');
    const secretInput = byId('apiSecret');

    if (title) title.textContent = configured ? 'Saved securely on Linode' : 'No saved Demo credential';
    if (detail) {
      if (status?.ok === false) {
        detail.textContent = status.message || 'Encrypted credential vault is unavailable.';
      } else if (configured) {
        const masked = status.maskedApiKey ? ` · ${status.maskedApiKey}` : '';
        const source = status.credentialMode === 'encrypted_server_vault'
          ? 'Encrypted server vault'
          : 'Legacy server environment';
        detail.textContent = `${source}${masked}. Secret is never returned to this browser.`;
      } else {
        detail.textContent = 'Enter a Binance Demo Trading key once. It will be encrypted on Linode; Fast Paper still works without it.';
      }
    }
    if (saveButton) saveButton.textContent = configured
      ? 'REPLACE SAVED DEMO KEY'
      : 'SAVE & CONNECT AUTHENTICATED DEMO';
    if (deleteButton) {
      deleteButton.hidden = !configured || status?.credentialMode !== 'encrypted_server_vault';
    }
    if (keyInput) keyInput.placeholder = configured
      ? 'New Demo API key to replace saved key'
      : 'Binance Demo API key';
    if (secretInput) secretInput.placeholder = configured
      ? 'New Demo API secret to replace saved secret'
      : 'Binance Demo API secret';
  }

  async function fetchCredentialStatus() {
    const response = await fetch('/api/demo/credential-status', { cache: 'no-store' });
    const payload = await response.json();
    if (!response.ok && payload.ok !== false) {
      throw new Error(payload.message || `Credential status failed (${response.status})`);
    }
    renderCredentialStatus(payload);
    return payload;
  }

  function applyConnectedResult(result, detailPrefix = 'Saved Demo auto-connected') {
    const ready = Boolean(result?.ok && result?.sessionToken);
    const profile = providerProfiles.find((item) => item.provider === 'binance');
    if (!profile) return ready;
    profile.status = ready ? 'connected' : 'error';
    profile.detail = ready
      ? `${detailPrefix}${result.latencyMs ? ` · ${result.latencyMs} ms` : ''}`
      : (result?.message || 'Authenticated Demo connection failed');
    profile.balances = ready ? (result.balances || {}) : {};
    demoSessionToken = ready ? result.sessionToken : null;
    renderConnections();
    return ready;
  }

  async function autoConnectSavedCredential() {
    let status;
    try {
      status = await fetchCredentialStatus();
    } catch (error) {
      renderCredentialStatus({ ok: false, configured: false, message: error.message });
      return;
    }
    if (!status.configured) return;

    const resultBox = byId('connectionResult');
    if (resultBox) {
      resultBox.className = 'connection-result';
      resultBox.textContent = 'Connecting saved Binance Demo credential…';
    }
    try {
      const result = await postJson('/api/demo/autoconnect', {});
      const ready = applyConnectedResult(result);
      if (resultBox) {
        resultBox.className = `connection-result ${ready ? 'good' : 'bad'}`;
        resultBox.textContent = ready
          ? 'Saved Binance Demo credential connected automatically'
          : (result.message || 'Saved Demo credential could not connect');
      }
      if (ready) await refreshDemoSnapshot();
    } catch (error) {
      const profile = providerProfiles.find((item) => item.provider === 'binance');
      if (profile) {
        profile.status = 'error';
        profile.detail = 'Saved Demo key needs attention';
        profile.balances = {};
        renderConnections();
      }
      if (resultBox) {
        resultBox.className = 'connection-result bad';
        resultBox.textContent = error.message || 'Saved Demo credential could not connect';
      }
    }
  }

  async function saveCredential() {
    if (saveInFlight) return;
    const keyInput = byId('apiKey');
    const secretInput = byId('apiSecret');
    const resultBox = byId('connectionResult');
    const saveButton = byId('testConnection');
    const apiKey = keyInput?.value.trim() || '';
    const apiSecret = secretInput?.value.trim() || '';
    if (!apiKey || !apiSecret) {
      if (resultBox) {
        resultBox.className = 'connection-result bad';
        resultBox.textContent = 'Binance Demo API key and secret are required to save.';
      }
      return;
    }

    saveInFlight = true;
    if (saveButton) saveButton.disabled = true;
    if (resultBox) {
      resultBox.className = 'connection-result';
      resultBox.textContent = 'Testing Demo key before encrypted save…';
    }
    const credentials = { apiKey, apiSecret };
    try {
      const result = await postJson('/api/demo/credentials/save', {
        provider: 'binance',
        environment: 'demo',
        credentials,
      });
      const ready = Boolean(result.saved) && applyConnectedResult(result, 'Encrypted Demo connected');
      if (resultBox) {
        resultBox.className = `connection-result ${ready ? 'good' : 'bad'}`;
        resultBox.textContent = ready
          ? 'Demo key saved encrypted on Linode · future app opens can auto-connect'
          : (result.message || 'Credential test failed; nothing was saved');
      }
      await fetchCredentialStatus();
      if (ready) await refreshDemoSnapshot();
    } catch (error) {
      if (resultBox) {
        resultBox.className = 'connection-result bad';
        resultBox.textContent = error.message || 'Could not save Demo credential';
      }
    } finally {
      credentials.apiKey = '';
      credentials.apiSecret = '';
      if (keyInput) keyInput.value = '';
      if (secretInput) secretInput.value = '';
      if (saveButton) saveButton.disabled = false;
      saveInFlight = false;
    }
  }

  async function deleteSavedCredential() {
    if (!credentialStatus?.configured) return;
    if (!window.confirm('Delete the encrypted Binance Demo key from Linode? Fast Paper can continue on public Demo data.')) return;
    const deleteButton = byId('deleteSavedDemoCredential');
    const resultBox = byId('connectionResult');
    if (deleteButton) deleteButton.disabled = true;
    try {
      const result = await postJson('/api/demo/credentials/delete', {
        confirm: true,
        sessionToken: demoSessionToken || '',
      });
      demoSessionToken = null;
      lockBinance('Saved Demo key deleted · Fast Paper can use public Demo data');
      renderCredentialStatus(result);
      if (resultBox) {
        resultBox.className = 'connection-result good';
        resultBox.textContent = result.message || 'Saved Demo credential deleted';
      }
    } catch (error) {
      if (resultBox) {
        resultBox.className = 'connection-result bad';
        resultBox.textContent = error.message || 'Could not delete saved Demo credential';
      }
    } finally {
      if (deleteButton) deleteButton.disabled = false;
    }
  }

  // Capture before app.js's legacy one-shot connection handler. The new path validates,
  // encrypts and persists the credential server-side, then creates the Demo session.
  document.addEventListener('click', (event) => {
    const button = event.target.closest('button');
    if (button?.id !== 'testConnection') return;
    event.preventDefault();
    event.stopImmediatePropagation();
    saveCredential();
  }, true);

  byId('addConnection')?.addEventListener('click', () => fetchCredentialStatus().catch(() => {}));
  document.querySelector('[data-nav="settings"]')?.addEventListener('click', () => fetchCredentialStatus().catch(() => {}));
  byId('refreshApp')?.addEventListener('click', () => fetchCredentialStatus().catch(() => {}));

  installCredentialPanel();
  autoConnectSavedCredential();
  window.EBACredentials = {
    refresh: fetchCredentialStatus,
    save: saveCredential,
    remove: deleteSavedCredential,
  };
})();
