const CACHE_NAME = "ti84-pwa-v1";
const PRECACHE_URLS = ["/", "/static/index.html", "/static/manifest.webmanifest", "/static/icon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.map((key) => (key.startsWith("ti84-pwa-") && key !== CACHE_NAME ? caches.delete(key) : null)))
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  const sameOrigin = url.origin === self.location.origin;

  if (event.request.mode === "navigate") {
    event.respondWith(fetch(event.request).catch(() => caches.match("/")));
    return;
  }

  if (sameOrigin && url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        const network = fetch(event.request)
          .then((response) => {
            if (response && response.ok) {
              caches.open(CACHE_NAME).then((cache) => cache.put(event.request, response.clone()));
            }
            return response;
          })
          .catch(() => cached);

        return cached || network;
      })
    );
  }
});
