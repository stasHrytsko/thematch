// sw.js — Service Worker for TheMatch PWA
// Чистая статика: расчёт идёт в браузере, сети/бэкенда нет.
// Стратегия: cache-first для всех ассетов, фоновое обновление кэша.
const CACHE_NAME = "thematch-v2";

const STATIC_ASSETS = [
  "/",
  "/index.html",
  "/logic.js",
  "/app.js",
  "/style.css",
  "/manifest.json",
  "/icons/icon.svg",
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
// Fetch: cache-first, then network (and update cache)                 //
// ------------------------------------------------------------------ //
self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

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
