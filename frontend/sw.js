const CACHE_NAME = 'moneymind-cache-v7';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Không can thiệp cache cho HTML, scripts và API để đảm bảo luôn cập nhật tức thì
  if (
    event.request.method !== 'GET' ||
    event.request.destination === 'document' ||
    event.request.destination === 'script' ||
    event.request.url.includes('/api/') ||
    event.request.url.includes('/auth/') ||
    event.request.url.includes('/giao-dich') ||
    event.request.url.includes('/thong-ke') ||
    event.request.url.includes('/danh-muc') ||
    event.request.url.includes('/tiet-kiem') ||
    event.request.url.includes('/js/')
  ) {
    return;
  }

  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
