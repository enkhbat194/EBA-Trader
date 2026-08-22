(() => {
  const root = document.getElementById('mt5Fields');
  const pairButton = document.getElementById('createMt5Pair');
  if (!root || !pairButton || document.getElementById('downloadMt5Bridge')) return;

  const download = document.createElement('a');
  download.id = 'downloadMt5Bridge';
  download.className = 'secondary full download-link';
  download.href = './downloads/install_mt5_bridge.bat';
  download.download = 'install_mt5_bridge.bat';
  download.textContent = '1. DOWNLOAD WINDOWS MT5 BRIDGE';
  pairButton.textContent = '2. CREATE MT5 PAIR CODE';
  root.insertBefore(download, pairButton);
})();
