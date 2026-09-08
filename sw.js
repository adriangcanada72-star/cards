// The Terpene Sommelier — service worker
// Bump CACHE when you change the app shell so clients pick up updates.
const CACHE = "ts-app-v1";
const SHELL = [
  "ts_app.html",
  "manifest.webmanifest",
  "pwa-192.png",
  "pwa-512.png",
  "pwa-512-maskable.png",
  "apple-touch-icon.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  // Only handle our own origin (GitHub Pages). Let Supabase/Stripe/CDN pass straight through.
  if (url.origin !== self.location.origin) return;

  // Network-first, fall back to cache (so re-uploads show up, but offline still works).
  e.respondWith(
    fetch(req)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        return res;
      })
      .catch(() => caches.match(req).then((hit) => hit || caches.match("ts_app.html")))
  );
});
