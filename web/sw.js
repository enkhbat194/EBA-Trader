const CACHE_NAME = 'eba-trader-ui-v15';
const ASSETS = [
  './',
  './index.html',
  './app.css',
  './m18_2.css',
  './trade_detail.css',
  './research_ui.css',
  './chart.js',
  './app.js',
  './mt5_ui.js',
  './paper_ui.js',
  './momentum_ui.js',
  './trade_detail.js',
  './research_ui.js',
  './scanner_heartbeat.js',
  './credential_ui.js',
  './update_ui.js',
  './manifest.webmanifest',
  './icon.svg',
];

async function cacheFreshAssets() {
  const cache = await caches.open(CACHE_NAME);
  await Promise.all(ASSETS.map(async (asset) => {
    const response = await fetch(asset, { cache: 'reload' });
    if (!response.ok) throw new Error(`Failed to refresh PWA asset: ${asset}`);
    await cache.put(asset, response);
  }));
}

self.addEventListener('install', (event) => {
  event.waitUntil(cacheFreshAssets());
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)),
    )),
  );
  self.clients.claim();
});

self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);
  if (url.origin === self.location.origin && url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(event.request, { cache: 'no-store' }));
    return;
  }

  event.respondWith(
    fetch(event.request, { cache: 'no-store' })
      .then((response) => {
        if (response.ok && url.origin === self.location.origin) {
          const copy = response.clone();
          event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy)));
        }
        return response;
      })
      .catch(() => caches.match(event.request)),
  );
});
