self.addEventListener('install', (e) => {
  e.waitUntil(caches.open('v1').then((cache) => cache.addAll(['/admin', '/static/style.css'])));
});
self.addEventListener('fetch', (e) => {
  e.respondWith(caches.match(e.request).then((response) => response || fetch(e.request)));
});
