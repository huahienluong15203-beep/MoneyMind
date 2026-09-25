const CACHE_NAME = 'moneymind-cache-v1';
const STATIC_ASSETS = [
  '/',
  '/manifest.json',
  '/css/style.css',
  '/css/layout.css',
  '/icons/icon-192.png',
  '/icons/icon-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Chỉ can thiệp các request GET tĩnh, không can thiệp API request
  if (event.request.method !== 'GET' || event.request.url.includes('/api/') || event.request.url.includes('/auth/') || event.request.url.includes('/giao-dich') || event.request.url.includes('/thong-ke') || event.request.url.includes('/danh-muc') || event.request.url.includes('/tiet-kiem')) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .catch(() => caches.match(event.request))
  );
});
