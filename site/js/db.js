// Tiny IndexedDB wrapper for user-added MIDI files and soundfonts.
const DB_NAME = "midi-pocket-db";
const DB_VER = 1;

function open() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VER);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains("userMidi"))
        db.createObjectStore("userMidi", { keyPath: "id" });
      if (!db.objectStoreNames.contains("userFonts"))
        db.createObjectStore("userFonts", { keyPath: "id" });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function tx(store, mode, fn) {
  const db = await open();
  return new Promise((resolve, reject) => {
    const t = db.transaction(store, mode);
    const s = t.objectStore(store);
    const out = fn(s);
    t.oncomplete = () => resolve(out);
    t.onerror = () => reject(t.error);
    t.onabort = () => reject(t.error);
  });
}

export const db = {
  async put(store, value) {
    return tx(store, "readwrite", (s) => s.put(value));
  },
  async get(store, key) {
    const db = await open();
    return new Promise((resolve, reject) => {
      const req = db.transaction(store).objectStore(store).get(key);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  },
  async all(store) {
    const db = await open();
    return new Promise((resolve, reject) => {
      const req = db.transaction(store).objectStore(store).getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  },
  async del(store, key) {
    return tx(store, "readwrite", (s) => s.delete(key));
  },
};
