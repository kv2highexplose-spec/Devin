// MIDI Pocket service worker — precache app shell, runtime-cache library data.
const VERSION = "mp-v2";
const SHELL = [
  "./", "index.html", "css/app.css", "js/app.js", "js/db.js",
  "manifest.webmanifest",
  "vendor/spessasynth/spessasynth.bundle.js",
  "vendor/spessasynth/spessasynth_processor.min.js",
  "library/catalog.json", "library/soundfonts/fonts.json",
  "icons/icon-192.png", "icons/icon-512.png",
];
const RUNTIME = [
  /^library\/catalog\/part-\d+\.json$/,
  /^library\/midi\//,
  /^library\/soundfonts\/.*\.(sf2|sf3|dls|sfogg)$/,
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  const path = url.pathname.replace(/^.*?(?=index|css|js|vendor|library|icons|manifest|$)/, "");
  const shellHit = SHELL.some((p) => url.pathname.endsWith(p.replace(/^\.\//, "")));
  const rtHit = RUNTIME.some((re) => re.test(path));
  if (!shellHit && !rtHit) return;
  e.respondWith(
    caches.match(e.request).then((hit) => {
      if (hit) return hit;
      return fetch(e.request).then((res) => {
        if (res.ok && rtHit) {
          const clone = res.clone();
          caches.open(VERSION).then((c) => c.put(e.request, clone));
        }
        return res;
      });
    })
  );
});
