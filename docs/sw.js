// Service worker de Ofertas Gamer CO: abre la página sin internet con la última copia guardada.
const CACHE = "ogc-3b8558c4e226074ae35d";
const SHELL = ["./", "index.html", "sin-conexion.html", "assets/styles.css?v=3b8558c4e2", "assets/app.js?v=26074ae35d", "assets/icon-192.png", "assets/placeholder.svg"];
self.addEventListener("install", (ev) => {
  ev.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (ev) => {
  ev.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", (ev) => {
  const req = ev.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  if (req.mode === "navigate" || url.pathname.includes("/data/")) {
    // Primero internet (precios frescos); sin conexión, la copia guardada.
    ev.respondWith(fetch(req).then((res) => {
      const copy = res.clone();
      if (res.ok) caches.open(CACHE).then((c) => c.put(req, copy));
      return res;
    }).catch(() => caches.match(req).then((hit) => hit || caches.match("sin-conexion.html"))));
    return;
  }
  ev.respondWith(caches.match(req).then((hit) => hit || fetch(req)));
});
