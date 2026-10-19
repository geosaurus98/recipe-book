// Lets the planner open with no signal (e.g. in the supermarket).
// Network first so recipe updates show up straight away; if the network is
// down or slower than 3 seconds, the last copy saved on the phone is used.
const CACHE = "meal-planner-v1";
const CORE = ["./", "manifest.webmanifest", "icons/icon-192.png", "icons/apple-touch-icon.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  // Google Fonts never change at a given URL: cache first
  if (url.hostname.endsWith("fonts.googleapis.com") || url.hostname.endsWith("fonts.gstatic.com")) {
    e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => save(req, res))));
    return;
  }
  if (url.origin !== location.origin) return;

  e.respondWith(networkFirst(req));
});

async function networkFirst(req) {
  const network = fetch(req).then(res => save(req, res));
  const cached = await caches.match(req, { ignoreSearch: true });
  if (!cached) return network;
  const timeout = new Promise(resolve => setTimeout(() => resolve(cached), 3000));
  return Promise.race([network.catch(() => cached), timeout]);
}

function save(req, res) {
  if (res.ok || res.type === "opaque") {
    const copy = res.clone();
    caches.open(CACHE).then(c => c.put(req, copy));
  }
  return res;
}
