// ATS Operations — online-only service worker.
//
// This service worker provides the minimal lifecycle hooks required
// for PWA installability without any offline caching of clinical
// content. All fetch requests are forwarded directly to the network.

self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  event.respondWith(fetch(event.request));
});
