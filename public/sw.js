// sw.js — Service Worker for TheMatch PWA
// Strategy:
//   • API requests  (/api/*) → network only, offline error JSON fallback
//   • Static assets           → cache-first, update in background
const CACHE_NAME = "thematch-v1";

const STATIC_ASSETS = [
  "/",
  "/index.html",
  "/app.js",
  "/style.css",
  "/manifest.json",
];

// ------------------------------------------------------------------ //
// Install: pre-cache the app shell                                    //
// ------------------------------------------------------------------ //
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

// ------------------------------------------------------------------ //
// Activate: purge stale caches                                        //
// ------------------------------------------------------------------ //
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_NAME)
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

// ------------------------------------------------------------------ //
// Fetch: route requests by strategy                                   //
// ------------------------------------------------------------------ //
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // API calls: network-only with offline fallback
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(request).catch(() =>
        new Response(
          JSON.stringify({ error: "You are offline. Please check your connection." }),
          {
            status: 503,
            headers: { "Content-Type": "application/json" },
          }
        )
      )
    );
    return;
  }

  // Static assets: cache-first, then network (and update cache)
  event.respondWith(
    caches.match(request).then((cached) => {
      const networkFetch = fetch(request)
        .then((response) => {
          if (response && response.status === 200 && response.type === "basic") {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => null);

      return cached || networkFetch || caches.match("/index.html");
    })
  );
});
