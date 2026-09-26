import { WorkletSynthesizer, Sequencer } from "../vendor/spessasynth/spessasynth.bundle.js";
import { db } from "./db.js";

/* ============================================================
 * MIDI Pocket — offline MIDI + SoundFont player
 * ============================================================ */

const GENRE_META = {
  eurobeat:   { label: "ユーロビート", color: "#ff5b8d" },
  synthwave:  { label: "シンセウェーブ", color: "#b06bff" },
  game:       { label: "ゲームBGM", color: "#58a6ff" },
  piano:      { label: "ピアノ", color: "#f2e7c9" },
  orchestra:  { label: "オーケストラ", color: "#d9a066" },
  chiptune:   { label: "チップチューン", color: "#4fd1a5" },
  jazz:       { label: "ジャズ", color: "#e3b341" },
  lofi:       { label: "ローファイ", color: "#a1a1aa" },
  trance:     { label: "トランス", color: "#22d3ee" },
  waltz:      { label: "ワルツ", color: "#f9a8d4" },
  bossa:      { label: "ボサノバ", color: "#86efac" },
  ambient:    { label: "アンビエント", color: "#7dd3fc" },
  user:       { label: "マイMIDI", color: "#ff9d5b" },
};

const LS = {
  favs: "mp_favs",
  recent: "mp_recent",
  font: "mp_font",
  tempo: "mp_tempo",
};

const state = {
  tracks: [],            // all track records
  filtered: [],
  queue: [],             // array of track ids in play order
  qpos: -1,              // position in queue
  playing: false,
  paused: true,
  shuffle: false,
  repeat: "off",         // off | all | one
  tempo: 1.0,
  favs: new Set(JSON.parse(localStorage.getItem(LS.favs) || "[]")),
  recent: JSON.parse(localStorage.getItem(LS.recent) || "[]"),
  fonts: [],             // soundfont records
  fontId: localStorage.getItem(LS.font) || null,
  sort: "default",
  selGenres: new Set(),
  selTags: new Set(),
  search: "",
  viewMode: "all",       // all | favs | recent
  renderLimit: 0,
  currentTrack: null,
  duration: 0,
  seekLock: false,
};

const $ = (id) => document.getElementById(id);
const el = {
  list: $("trackList"), info: $("listInfo"), sentinel: $("listSentinel"),
  search: $("searchBox"), chips: $("genreChips"),
  mini: $("miniPlayer"), mpTitle: $("mpTitle"), mpSub: $("mpSub"), mpDot: $("mpGenreDot"),
  mpPlay: $("mpPlay"), mpPrev: $("mpPrev"), mpNext: $("mpNext"),
  pSheet: $("playerSheet"), psTitle: $("psTitle"), psMeta: $("psMeta"), psTags: $("psTags"),
  psSeek: $("psSeek"), psCur: $("psCur"), psDur: $("psDur"),
  psTempo: $("psTempo"), psTempoVal: $("psTempoVal"),
  psPlay: $("psPlay"), psPrev: $("psPrev"), psNext: $("psNext"),
  psShuffle: $("psShuffle"), psRepeat: $("psRepeat"), psFav: $("psFav"),
  sfButton: $("sfButton"), sfName: $("sfName"), sfRecommend: $("sfRecommend"),
  sfSheet: $("sfSheet"), sfList: $("sfList"),
  fSheet: $("filterSheet"), fsGenres: $("fsGenres"), fsTags: $("fsTags"), fsSort: $("fsSort"),
  scrim: $("scrim"), toast: $("toast"),
  fileMidi: $("fileMidi"), fileFont: $("fileFont"),
};

/* ---------------- player ---------------- */
const player = {
  ctx: null, synth: null, seq: null,
  fontBuf: null, fontLoading: null,

  async ensure() {
    if (!this.ctx) {
      this.ctx = new AudioContext({ latencyHint: "playback" });
      await this.ctx.audioWorklet.addModule("vendor/spessasynth/spessasynth_processor.min.js");
      this.synth = new WorkletSynthesizer(this.ctx);
      this.seq = new Sequencer(this.synth, { skipToFirstNoteOn: true });
      this.seq.loopCount = 0;
      this.seq.eventHandler.addEvent("songEnded", "ui", () => onSongEnded());
      this.seq.eventHandler.addEvent("midiError", "ui", (e) => toast("MIDI読み込みエラー: " + (e.error?.message || "不明")));
    }
    if (this.ctx.state === "suspended") {
      await this.ctx.resume();
      // resume() can be denied outside a gesture window — retry on next tap
      if (this.ctx.state === "suspended") {
        toast("もう一度タップで音声を有効化");
        document.addEventListener("pointerdown", () => this.ctx.resume(), { once: true });
      }
    }
    await this.ensureFont();
    return this;
  },

  async ensureFont() {
    if (this.fontBuf) return;
    this.fontLoading = loadFont(state.fontId || state.fonts[0]?.id);
    this.fontBuf = await this.fontLoading;
    this.fontLoading = null;
    if (this.fontBuf) {
      await this.synth.soundBankManager.addSoundBank(this.fontBuf, "main");
      await this.synth.isReady;
    }
  },

  async setFont(id) {
    const buf = await loadFont(id);
    if (!buf) return;
    const wasPlaying = state.playing && !this.seq.paused;
    // addSoundBank replaces an existing id in place — no delete needed
    await this.synth.soundBankManager.addSoundBank(buf, "main");
    await this.synth.isReady;
    this.fontBuf = buf;
    state.fontId = id;
    localStorage.setItem(LS.font, id);
    el.sfName.textContent = fontName(id);
    showRecommend();
    if (wasPlaying) { this.seq.play(); }
    toast("SoundFont: " + fontName(id));
  },
};

async function loadFont(id) {
  const f = state.fonts.find((x) => x.id === id) || state.fonts[0];
  if (!f) return null;
  try {
    if (f.file.startsWith("idb:")) {
      const rec = await db.get("userFonts", f.file.slice(4));
      return rec?.data || null;
    }
    const res = await fetch("library/soundfonts/" + f.file);
    if (!res.ok) throw new Error("HTTP " + res.status);
    return await res.arrayBuffer();
  } catch (e) {
    toast("SoundFont 読み込み失敗: " + f.name);
    return null;
  }
}

const fontName = (id) => state.fonts.find((f) => f.id === id)?.name || "—";

/* ---------------- catalog ---------------- */
async function loadCatalog() {
  const [catRes, fontRes] = await Promise.all([
    fetch("library/catalog.json"), fetch("library/soundfonts/fonts.json"),
  ]);
  const cat = await catRes.json();
  const fontsMeta = await fontRes.json();
  state.fonts = fontsMeta.fonts;

  // user fonts
  for (const uf of await db.all("userFonts")) {
    state.fonts.push({
      id: uf.id, name: uf.name, file: "idb:" + uf.id,
      sizeMB: uf.sizeMB, tags: ["user"], userAdded: true,
      notes: "ユーザー追加",
    });
  }
  renderFontList();

  // user midis
  for (const um of await db.all("userMidi")) {
    state.tracks.push({
      id: um.id, title: um.title, file: "idb:userMidi/" + um.id,
      genre: "user", mood: um.mood || "-", bpm: um.bpm || 0,
      tags: um.tags || ["user"], recommendedSoundfonts: [],
      durationSec: um.durationSec || 0, sizeBytes: um.sizeBytes || 0,
      userAdded: true,
    });
  }

  // parts load progressively — UI stays responsive with 1000+ tracks
  const parts = cat.parts.map((p) =>
    fetch("library/" + p.file).then((r) => r.json()).then((rows) => {
      const before = state.tracks.length;
      state.tracks.push(...rows);
      return state.tracks.length - before;
    })
  );
  renderGenreChips(cat);
  applyFilters();
  for (const p of parts) { p.then(() => applyFilters()); }
  await Promise.all(parts);
}

/* ---------------- filtering & list ---------------- */
function applyFilters() {
  const q = state.search.trim().toLowerCase();
  let rows = state.tracks;
  if (state.viewMode === "favs") rows = rows.filter((t) => state.favs.has(t.id));
  else if (state.viewMode === "recent") {
    const order = new Map(state.recent.map((id, i) => [id, i]));
    rows = rows.filter((t) => order.has(t.id));
    rows.sort((a, b) => order.get(a.id) - order.get(b.id));
  }
  if (state.selGenres.size) rows = rows.filter((t) => state.selGenres.has(t.genre));
  if (state.selTags.size) rows = rows.filter((t) => t.tags.some((x) => state.selTags.has(x)));
  if (q) {
    rows = rows.filter((t) =>
      t.title.toLowerCase().includes(q) || t.id.toLowerCase().includes(q) ||
      t.tags.some((x) => x.toLowerCase().includes(q)) ||
      (t.mood || "").toLowerCase().includes(q));
  }
  if (state.viewMode !== "recent") {
    if (state.sort === "title") rows = [...rows].sort((a, b) => a.title.localeCompare(b.title, "ja"));
    else if (state.sort === "bpm") rows = [...rows].sort((a, b) => a.bpm - b.bpm);
    else if (state.sort === "duration") rows = [...rows].sort((a, b) => a.durationSec - b.durationSec);
  }
  state.filtered = rows;
  state.renderLimit = 60;
  renderList();
  updateInfo();
}

function updateInfo() {
  const total = state.tracks.length;
  const shown = state.filtered.length;
  let s = `${shown} 曲`;
  if (shown !== total) s += ` / 全 ${total} 曲`;
  if (state.queue.length) {
    const t = currentTrack();
    if (t) s += ` — ${t.title}`;
  }
  el.info.textContent = s;
}

function renderList() {
  const rows = state.filtered.slice(0, state.renderLimit);
  const frag = document.createDocumentFragment();
  const curId = currentTrack()?.id;
  for (const t of rows) {
    const li = document.createElement("li");
    li.className = "track" + (t.id === curId ? " playing" : "");
    li.dataset.id = t.id;
    const g = GENRE_META[t.genre] || GENRE_META.user;
    const dur = fmtTime(t.durationSec);
    li.innerHTML = `
      <div class="t-dot" style="background:${g.color}"></div>
      <div class="t-meta">
        <div class="t-title"></div>
        <div class="t-sub">
          <span>${g.label}</span><span>${t.bpm} BPM</span><span>${t.mood || ""}</span>
          ${(t.recommendedSoundfonts || []).length ? '<span class="sf-badge">SF推奨</span>' : ""}
        </div>
      </div>
      <button class="t-fav ${state.favs.has(t.id) ? "on" : ""}" aria-label="お気に入り">${state.favs.has(t.id) ? "★" : "☆"}</button>
      <span class="t-dur">${dur}</span>`;
    li.querySelector(".t-title").textContent = t.title;
    li.addEventListener("click", (e) => {
      if (e.target.closest(".t-fav")) { toggleFav(t.id); return; }
      playTrack(t);
    });
    frag.appendChild(li);
  }
  el.list.replaceChildren(frag);
}

const io = new IntersectionObserver((ents) => {
  if (ents[0].isIntersecting && state.renderLimit < state.filtered.length) {
    state.renderLimit += 60;
    renderList();
  }
});
io.observe(el.sentinel);

/* ---------------- chips / filters ---------------- */
function renderGenreChips(cat) {
  const wrap = el.chips;
  wrap.replaceChildren();
  const mk = (label, fn, on) => {
    const b = document.createElement("button");
    b.className = "chip" + (on ? " on" : "");
    b.textContent = label;
    b.onclick = fn;
    wrap.appendChild(b);
  };
  mk("すべて", () => { state.viewMode = "all"; state.selGenres.clear(); syncChips(); applyFilters(); }, state.viewMode === "all" && !state.selGenres.size);
  mk("★ お気に入り", () => { state.viewMode = state.viewMode === "favs" ? "all" : "favs"; syncChips(); applyFilters(); }, state.viewMode === "favs");
  mk("🕒 最近", () => { state.viewMode = state.viewMode === "recent" ? "all" : "recent"; syncChips(); applyFilters(); }, state.viewMode === "recent");
  mk("🎲 ランダム", playRandom, false);
  for (const [g, meta] of Object.entries(GENRE_META)) {
    if (g === "user" && !state.tracks.some((t) => t.genre === "user")) continue;
    if (cat && cat.genres && !cat.genres[g] && g !== "user") continue;
    mk(meta.label, () => {
      state.viewMode = "all";
      if (state.selGenres.has(g)) state.selGenres.delete(g); else { state.selGenres.clear(); state.selGenres.add(g); }
      syncChips(); applyFilters();
    }, state.selGenres.has(g));
  }
}
function syncChips() { renderGenreChips(null); }

function renderFilterSheet() {
  const gWrap = el.fsGenres; gWrap.replaceChildren();
  for (const [g, meta] of Object.entries(GENRE_META)) {
    if (g === "user") continue;
    const b = document.createElement("button");
    b.className = "chip" + (state.selGenres.has(g) ? " on" : "");
    b.textContent = meta.label;
    b.onclick = () => {
      if (state.selGenres.has(g)) state.selGenres.delete(g); else state.selGenres.add(g);
      b.classList.toggle("on"); applyFilters();
    };
    gWrap.appendChild(b);
  }
  const tags = [...new Set(state.tracks.flatMap((t) => t.tags))].sort();
  const tWrap = el.fsTags; tWrap.replaceChildren();
  for (const tag of tags) {
    const b = document.createElement("button");
    b.className = "chip" + (state.selTags.has(tag) ? " on" : "");
    b.textContent = "#" + tag;
    b.onclick = () => {
      if (state.selTags.has(tag)) state.selTags.delete(tag); else state.selTags.add(tag);
      b.classList.toggle("on"); applyFilters();
    };
    tWrap.appendChild(b);
  }
  for (const b of el.fsSort.querySelectorAll(".chip")) {
    b.classList.toggle("on", b.dataset.sort === state.sort);
    b.onclick = () => { state.sort = b.dataset.sort; renderFilterSheet(); applyFilters(); };
  }
}

/* ---------------- playback ---------------- */
function currentTrack() {
  return state.qpos >= 0 && state.qpos < state.queue.length
    ? state.tracks.find((t) => t.id === state.queue[state.qpos]) : null;
}

function buildQueue(fromTrack) {
  if (state.shuffle) {
    state.queue = shuffleArr(state.filtered.map((t) => t.id));
    state.qpos = state.queue.indexOf(fromTrack.id);
    if (state.qpos < 0) { state.queue.unshift(fromTrack.id); state.qpos = 0; }
  } else {
    state.queue = state.filtered.map((t) => t.id);
    state.qpos = state.queue.indexOf(fromTrack.id);
  }
}

async function playTrack(t, autoplay = true) {
  buildQueue(t);
  await loadAndPlay();
}

async function loadAndPlay() {
  const t = currentTrack();
  if (!t) return;
  try {
    await player.ensure();
    const buf = await fetchMidi(t);
    if (!buf) { toast("ファイルを読み込めません: " + t.title); return; }
    player.seq.loadNewSongList([{ binary: buf, fileName: t.title }]);
    player.seq.playbackRate = state.tempo;
    player.seq.play();
    state.playing = true;
    state.paused = false;
    state.currentTrack = t;
    state.duration = t.durationSec || player.seq.midiData?.duration || 0;
    pushRecent(t.id);
    updatePlayerUI();
    updateInfo();
    renderList();
    if ("mediaSession" in navigator) {
      setMediaSession(t);
      navigator.mediaSession.playbackState = "playing";
    }
  } catch (e) {
    console.error(e);
    toast("再生エラー: " + e.message);
  }
}

async function fetchMidi(t) {
  if (t.file.startsWith("idb:userMidi/")) {
    const rec = await db.get("userMidi", t.id);
    return rec?.data || null;
  }
  const res = await fetch("library/" + t.file);
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.arrayBuffer();
}

// timeChange doesn't fire periodically, so the seek bar tracks via rAF
function tickUi() {
  if (player.seq && !state.seekLock) {
    const time = player.seq.currentTime;
    el.psCur.textContent = fmtTime(time);
    if (state.duration > 0) el.psSeek.value = Math.min(1000, Math.round((time / state.duration) * 1000));
  }
  requestAnimationFrame(tickUi);
}
requestAnimationFrame(tickUi);

function onSongEnded() {
  if (state.repeat === "one") { player.seq.currentTime = 0; player.seq.play(); return; }
  step(1);
}

function step(dir) {
  if (!state.queue.length) return;
  let n = state.qpos + dir;
  if (n >= state.queue.length) {
    if (state.repeat === "all" || state.shuffle) n = 0; else return;
  }
  if (n < 0) n = state.queue.length - 1;
  state.qpos = n;
  const t = currentTrack();
  if (t) { state.currentTrack = t; loadAndPlay(); }
}

function togglePlay() {
  if (!state.currentTrack) { playRandom(); return; }
  if (player.seq.paused) { player.seq.play(); state.paused = false; }
  else { player.seq.pause(); state.paused = true; }
  if ("mediaSession" in navigator) {
    navigator.mediaSession.playbackState = state.paused ? "paused" : "playing";
  }
  updatePlayerUI();
}

function playRandom() {
  const rows = state.filtered.length ? state.filtered : state.tracks;
  if (!rows.length) return;
  playTrack(rows[Math.floor(Math.random() * rows.length)]);
}

/* ---------------- favorites / recent ---------------- */
function toggleFav(id) {
  if (state.favs.has(id)) state.favs.delete(id); else state.favs.add(id);
  localStorage.setItem(LS.favs, JSON.stringify([...state.favs]));
  renderList();
  if (state.viewMode === "favs") applyFilters();
  updateFavBtn();
}

function pushRecent(id) {
  state.recent = [id, ...state.recent.filter((x) => x !== id)].slice(0, 100);
  localStorage.setItem(LS.recent, JSON.stringify(state.recent));
}

function updateFavBtn() {
  const on = state.currentTrack && state.favs.has(state.currentTrack.id);
  el.psFav.textContent = on ? "★" : "♡";
  el.psFav.style.color = on ? "#ffd166" : "";
}

/* ---------------- UI updates ---------------- */
function updatePlayerUI() {
  const t = state.currentTrack;
  if (!t) return;
  const g = GENRE_META[t.genre] || GENRE_META.user;
  el.mini.classList.remove("hidden");
  el.mpTitle.textContent = t.title;
  el.mpSub.textContent = `${g.label} · ${t.bpm} BPM · ${fmtTime(t.durationSec)}`;
  el.mpDot.style.background = g.color;
  el.psTitle.textContent = t.title;
  el.psMeta.textContent = `${g.label} · ${t.bpm} BPM · ${t.mood || ""}`;
  el.psTags.replaceChildren(...(t.tags || []).map((x) => {
    const s = document.createElement("span");
    s.className = "tag"; s.textContent = "#" + x; return s;
  }));
  el.psDur.textContent = fmtTime(state.duration || t.durationSec);
  const icon = state.paused ? "▶" : "⏸";
  el.mpPlay.textContent = icon; el.psPlay.textContent = icon;
  el.psShuffle.classList.toggle("on", state.shuffle);
  el.psRepeat.classList.toggle("on", state.repeat !== "off");
  el.psRepeat.textContent = state.repeat === "one" ? "🔂" : "🔁";
  updateFavBtn();
  showRecommend();
}

function showRecommend() {
  const t = state.currentTrack;
  const wrap = el.sfRecommend;
  wrap.replaceChildren();
  const recs = (t?.recommendedSoundfonts || []).filter((id) => state.fonts.some((f) => f.id === id));
  if (!recs.length) { wrap.classList.add("hidden"); return; }
  wrap.classList.remove("hidden");
  const lab = document.createElement("span");
  lab.className = "rlabel"; lab.textContent = "推奨SoundFont:";
  wrap.appendChild(lab);
  for (const id of recs) {
    const b = document.createElement("button");
    b.className = "rchip";
    b.textContent = fontName(id) + (id === state.fontId ? " ✓" : "");
    b.onclick = () => player.setFont(id);
    wrap.appendChild(b);
  }
}

function setMediaSession(t) {
  const g = GENRE_META[t.genre] || {};
  navigator.mediaSession.metadata = new MediaMetadata({
    title: t.title, artist: "MIDI Pocket", album: g.label || "",
  });
  const h = (a, fn) => { try { navigator.mediaSession.setActionHandler(a, fn); } catch (_) {} };
  h("play", () => togglePlay());
  h("pause", () => togglePlay());
  h("previoustrack", () => step(-1));
  h("nexttrack", () => step(1));
  h("seekto", (d) => { if (d.seekTime != null) player.seq.currentTime = d.seekTime; });
}

/* ---------------- sheets ---------------- */
function openSheet(s) { s.classList.remove("hidden"); el.scrim.classList.remove("hidden"); }
function closeSheets() {
  for (const s of [el.pSheet, el.sfSheet, el.fSheet]) s.classList.add("hidden");
  el.scrim.classList.add("hidden");
}

function renderFontList() {
  el.sfList.replaceChildren();
  for (const f of state.fonts) {
    const li = document.createElement("li");
    li.className = "sfitem" + (f.id === state.fontId ? " current" : "");
    const badges = (f.tags || []).map((x) => `<span class="sfbadge">${x}</span>`).join("");
    li.innerHTML = `<div class="sfbody">
      <div class="sfname"></div>
      <div class="sfmeta">${badges}${f.sizeMB ? f.sizeMB + " MB" : ""} ${f.license ? "· " + f.license : ""}</div>
      ${f.notes ? `<div class="sfmeta">${f.notes}</div>` : ""}
    </div>`;
    li.querySelector(".sfname").textContent = f.name;
    li.onclick = async () => { closeSheets(); await player.ensure(); await player.setFont(f.id); renderFontList(); };
    el.sfList.appendChild(li);
  }
  if (state.fonts.length && !state.fontId) {
    state.fontId = state.fonts[0].id;
  }
  el.sfName.textContent = fontName(state.fontId);
}

/* ---------------- file import ---------------- */
async function importMidi(file) {
  const data = await file.arrayBuffer();
  const id = "u-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 7);
  const meta = quickMidiMeta(data);
  const title = file.name.replace(/\.(mid|midi|smf)$/i, "");
  await db.put("userMidi", {
    id, title, data, genre: "user",
    bpm: meta.bpm, durationSec: meta.durationSec,
    tags: ["user", "imported"], mood: "-", sizeBytes: data.byteLength,
  });
  state.tracks.push({
    id, title, file: "idb:userMidi/" + id, genre: "user", mood: "-",
    bpm: meta.bpm, tags: ["user", "imported"], recommendedSoundfonts: [],
    durationSec: meta.durationSec, sizeBytes: data.byteLength, userAdded: true,
  });
}

async function importFont(file) {
  const data = await file.arrayBuffer();
  const magic = new Uint8Array(data.slice(0, 4));
  const ok = (magic[0] === 0x52 && magic[1] === 0x49 && magic[2] === 0x46 && magic[3] === 0x46) || // RIFF (SF2/DLS)
             (magic[0] === 0x73 && magic[1] === 0x46); // "sf" variants
  if (!ok) { toast("SF2/DLS ではないようです: " + file.name); return; }
  const id = "uf-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 7);
  const name = file.name.replace(/\.(sf2|sf3|dls|sfogg)$/i, "");
  await db.put("userFonts", { id, name, data, sizeMB: +(data.byteLength / 1048576).toFixed(1) });
  state.fonts.push({
    id, name, file: "idb:" + id, sizeMB: +(data.byteLength / 1048576).toFixed(1),
    tags: ["user"], userAdded: true, notes: "ユーザー追加",
  });
  renderFontList();
  toast("SoundFont追加: " + name);
}

// minimal MIDI header/division/tempo/length scan — full parse is the synth's job
function quickMidiMeta(buf) {
  try {
    const dv = new DataView(buf);
    const div = dv.getUint16(12);
    const tpb = (div & 0x8000) ? 480 : div; // SMPTE fallback guess
    let bpm = 120, lastTick = 0, tempoUs = 500000;
    const tracks = dv.getUint16(10);
    let off = 14;
    for (let i = 0; i < tracks && off < dv.byteLength - 8; i++) {
      const len = dv.getUint32(off + 4);
      let p = off + 8, end = p + len, tick = 0, running = 0;
      while (p < end) {
        let delta = 0, b;
        do { b = dv.getUint8(p++); delta = (delta << 7) | (b & 0x7f); } while (b & 0x80);
        tick += delta;
        let st = dv.getUint8(p++);
        if (st < 0x80) { st = running; p--; } else running = st;
        if (st === 0xff) {
          const mt = dv.getUint8(p++);
          let l = 0, bb;
          do { bb = dv.getUint8(p++); l = (l << 7) | (bb & 0x7f); } while (bb & 0x80);
          if (mt === 0x51 && l === 3) {
            tempoUs = dv.getUint8(p) << 16 | dv.getUint8(p + 1) << 8 | dv.getUint8(p + 2);
            if (tick === 0) bpm = Math.round(60000000 / tempoUs);
          }
          p += l;
        } else if (st === 0xf0 || st === 0xf7) {
          let l = 0, bb;
          do { bb = dv.getUint8(p++); l = (l << 7) | (bb & 0x7f); } while (bb & 0x80);
          p += l;
        } else {
          const n = (st & 0xf0) === 0xc0 || (st & 0xf0) === 0xd0 ? 1 : 2;
          p += n;
        }
      }
      lastTick = Math.max(lastTick, tick);
      off = end;
    }
    return { bpm, durationSec: Math.round((lastTick / tpb) * (tempoUs / 1e6)) };
  } catch (_) {
    return { bpm: 0, durationSec: 0 };
  }
}

/* ---------------- util ---------------- */
function fmtTime(s) {
  s = Math.max(0, Math.round(s || 0));
  return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
}
function shuffleArr(a) {
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}
let toastTimer;
function toast(msg) {
  el.toast.textContent = msg;
  el.toast.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.toast.classList.add("hidden"), 2600);
}

/* ---------------- events ---------------- */
el.search.addEventListener("input", () => { state.search = el.search.value; applyFilters(); });
$("btnShuffleAll").onclick = playRandom;
$("btnFilter").onclick = () => { renderFilterSheet(); openSheet(el.fSheet); };
$("fsClear").onclick = () => { state.selGenres.clear(); state.selTags.clear(); state.sort = "default"; state.viewMode = "all"; renderFilterSheet(); syncChips(); applyFilters(); };
$("btnAddFiles").onclick = () => el.fileMidi.click();
$("btnAddFont").onclick = () => el.fileFont.click();
el.fileMidi.onchange = async () => {
  for (const f of el.fileMidi.files) { try { await importMidi(f); toast("追加: " + f.name); } catch (e) { toast("追加失敗: " + f.name); } }
  el.fileMidi.value = ""; renderGenreChips(null); applyFilters();
};
el.fileFont.onchange = async () => {
  for (const f of el.fileFont.files) await importFont(f);
  el.fileFont.value = "";
};

el.mini.addEventListener("click", (e) => { if (!e.target.closest("button")) openSheet(el.pSheet); });
el.mini.addEventListener("keydown", (e) => { if (e.key === "Enter") openSheet(el.pSheet); });
$("sheetGrip").onclick = closeSheets;
el.scrim.onclick = closeSheets;
for (const s of [el.pSheet, el.sfSheet, el.fSheet])
  s.querySelector(".sheet-grip")?.addEventListener("click", closeSheets);

el.mpPlay.onclick = togglePlay; el.psPlay.onclick = togglePlay;
el.mpPrev.onclick = () => step(-1); el.psPrev.onclick = () => step(-1);
el.mpNext.onclick = () => step(1); el.psNext.onclick = () => step(1);
el.psFav.onclick = () => state.currentTrack && toggleFav(state.currentTrack.id);
el.psShuffle.onclick = () => {
  state.shuffle = !state.shuffle;
  if (state.currentTrack) buildQueue(state.currentTrack);
  updatePlayerUI();
};
el.psRepeat.onclick = () => {
  state.repeat = state.repeat === "off" ? "all" : state.repeat === "all" ? "one" : "off";
  updatePlayerUI();
};
el.psTempo.oninput = () => {
  state.tempo = el.psTempo.value / 100;
  el.psTempoVal.textContent = el.psTempo.value + "%";
  if (player.seq) player.seq.playbackRate = state.tempo;
  localStorage.setItem(LS.tempo, state.tempo);
};
el.psSeek.oninput = () => { state.seekLock = true; el.psCur.textContent = fmtTime((el.psSeek.value / 1000) * state.duration); };
el.psSeek.onchange = () => {
  if (player.seq && state.duration) player.seq.currentTime = (el.psSeek.value / 1000) * state.duration;
  state.seekLock = false;
};
el.sfButton.onclick = () => { renderFontList(); openSheet(el.sfSheet); };

const savedTempo = parseFloat(localStorage.getItem(LS.tempo) || "1");
if (savedTempo && savedTempo !== 1) {
  state.tempo = savedTempo;
  el.psTempo.value = Math.round(savedTempo * 100);
  el.psTempoVal.textContent = el.psTempo.value + "%";
}

document.addEventListener("visibilitychange", () => {
  // keep audio running in background; nothing to pause
  if (document.visibilityState === "visible" && player.ctx?.state === "suspended" && state.playing) {
    player.ctx.resume();
  }
});

// every touch is a fresh gesture — retry a stuck-suspended AudioContext
for (const ev of ["pointerdown", "touchend"]) {
  document.addEventListener(ev, () => {
    if (player.ctx?.state === "suspended") player.ctx.resume();
  }, { passive: true });
}

/* ---------------- boot ---------------- */
const IS_NATIVE = !!window.Capacitor?.isNativePlatform?.();
loadCatalog().catch((e) => { el.info.textContent = "カタログ読み込み失敗: " + e.message; });
if ("serviceWorker" in navigator) {
  if (IS_NATIVE) {
    // inside the APK assets are always local — a stale SW cache would only
    // serve outdated code after app updates
    navigator.serviceWorker.getRegistrations()
      .then((rs) => rs.forEach((r) => r.unregister())).catch(() => {});
  } else if (location.protocol.startsWith("http")) {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }
}

// introspection handle for automation/E2E
window.MP = { player, state, db };
