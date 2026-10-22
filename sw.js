// Keeps a copy of the designer so it opens without signal (on the water).
// Always tries the network first, so updates show up as soon as you are online.
var CACHE = 'canoe-v1';
var CORE = ['./', 'index.html', 'manifest.webmanifest', 'icons/apple-touch-icon.png', 'icons/icon-192.png', 'icons/icon-512.png'];

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(CORE); }).then(function () { return self.skipWaiting(); }));
});
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (ks) {
    return Promise.all(ks.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});
self.addEventListener('fetch', function (e) {
  var r = e.request;
  if (r.method !== 'GET') return;
  var u = new URL(r.url);
  var mine = u.origin === location.origin, fonts = /fonts\.(googleapis|gstatic)\.com$/.test(u.hostname);
  if (!mine && !fonts) return;
  e.respondWith(fetch(r).then(function (res) {
    if (res && (res.ok || res.type === 'opaque')) { var copy = res.clone(); caches.open(CACHE).then(function (c) { c.put(r, copy); }); }
    return res;
  }).catch(function () {
    return caches.match(r).then(function (hit) { return hit || (r.mode === 'navigate' ? caches.match('index.html') : undefined); });
  }));
});
