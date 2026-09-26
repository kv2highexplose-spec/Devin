/* ============================================================
   スタークエスト - audio.js
   Web Audio によるチップチューンBGM & 効果音
   ============================================================ */

"use strict";

const AU = {
  ctx: null, master: null, muted: false,
  song: null, wantBgm: null, seqTimer: null, nextStep: 0, stepIdx: 0,
};
try { AU.muted = localStorage.getItem("starquest_mute") === "1"; } catch (e) {}

AU.init = function () {
  if (AU.ctx) return;
  try {
    AU.ctx = new (window.AudioContext || window.webkitAudioContext)();
    AU.master = AU.ctx.createGain();
    AU.master.gain.value = 0.55;
    AU.master.connect(AU.ctx.destination);
  } catch (e) { /* audio unavailable */ }
  if (AU.ctx && AU.wantBgm) AU.bgm(AU.wantBgm);
};

AU.setMuted = function (m) {
  AU.muted = m;
  if (AU.master) AU.master.gain.value = m ? 0 : 0.55;
  try { localStorage.setItem("starquest_mute", m ? "1" : "0"); } catch (e) {}
};

// midi番号 -> 周波数
function m2f(n) { return 440 * Math.pow(2, (n - 69) / 12); }
const NOTE_MAP = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
function n2m(s) {
  // "C5", "F#4", "Bb3" 等
  const m = /^([A-G])([#b]?)(-?\d)$/.exec(s);
  if (!m) return 0;
  let v = NOTE_MAP[m[1]] + (m[2] === "#" ? 1 : m[2] === "b" ? -1 : 0);
  return (parseInt(m[3], 10) + 1) * 12 + v;
}

// "C5:4 D5:4 R:8" -> [{n:midi,len:16分音符数}]
function T(str) {
  const out = [];
  for (const tok of str.trim().split(/\s+/)) {
    const [n, l] = tok.split(":");
    const len = parseInt(l, 10) || 1;
    out.push({ n: n === "R" ? 0 : n2m(n), len });
  }
  return out;
}

AU.tone = function (freq, dur, type, vol, when, slideTo) {
  if (!AU.ctx || AU.muted) return;
  const t = when || AU.ctx.currentTime;
  const o = AU.ctx.createOscillator();
  const g = AU.ctx.createGain();
  o.type = type || "square";
  o.frequency.setValueAtTime(freq, t);
  if (slideTo) o.frequency.exponentialRampToValueAtTime(Math.max(20, slideTo), t + dur);
  g.gain.setValueAtTime(vol || 0.15, t);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  o.connect(g); g.connect(AU.master);
  o.start(t); o.stop(t + dur + 0.02);
};

AU.noise = function (dur, vol, when, hp) {
  if (!AU.ctx || AU.muted) return;
  const t = when || AU.ctx.currentTime;
  const len = Math.max(1, (dur * AU.ctx.sampleRate) | 0);
  const buf = AU.ctx.createBuffer(1, len, AU.ctx.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / len);
  const src = AU.ctx.createBufferSource(); src.buffer = buf;
  const g = AU.ctx.createGain();
  g.gain.setValueAtTime(vol || 0.1, t);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  const f = AU.ctx.createBiquadFilter();
  f.type = hp ? "highpass" : "lowpass";
  f.frequency.value = hp ? 3000 : 1200;
  src.connect(f); f.connect(g); g.connect(AU.master);
  src.start(t);
};

/* ---------- 効果音 ---------- */
const SFX = {
  cursor:  () => AU.tone(880, 0.05, "square", 0.08),
  ok:      () => { AU.tone(660, 0.06, "square", 0.1); AU.tone(990, 0.1, "square", 0.1, AU.ctx && AU.ctx.currentTime + 0.06); },
  cancel:  () => AU.tone(330, 0.1, "square", 0.1),
  talk:    () => AU.tone(520, 0.03, "square", 0.04),
  door:    () => { AU.noise(0.15, 0.08); AU.tone(220, 0.15, "triangle", 0.1); },
  stairs:  () => { AU.tone(440, 0.12, "triangle", 0.09); AU.tone(330, 0.16, "triangle", 0.09, AU.ctx && AU.ctx.currentTime + 0.1); },
  chest:   () => { AU.tone(523, 0.08, "square", 0.1); AU.tone(659, 0.08, "square", 0.1, AU.ctx && AU.ctx.currentTime + 0.08); AU.tone(784, 0.16, "square", 0.1, AU.ctx && AU.ctx.currentTime + 0.16); },
  hit:     () => { AU.noise(0.12, 0.16); AU.tone(160, 0.1, "sawtooth", 0.12); },
  hurt:    () => { AU.tone(220, 0.12, "sawtooth", 0.12, 0, 90); AU.noise(0.1, 0.1); },
  fire:    () => { AU.noise(0.3, 0.12); AU.tone(300, 0.35, "sawtooth", 0.1, 0, 90); },
  bolt:    () => { AU.tone(1200, 0.25, "sawtooth", 0.1, 0, 200); AU.noise(0.2, 0.14, 0, true); },
  heal:    () => { [523, 659, 784, 1047].forEach((f, i) => AU.tone(f, 0.14, "sine", 0.09, AU.ctx && AU.ctx.currentTime + i * 0.07)); },
  flee:    () => { AU.tone(700, 0.15, "square", 0.1, 0, 1400); },
  encounter: () => { AU.tone(180, 0.4, "sawtooth", 0.12, 0, 60); AU.noise(0.35, 0.1); },
  miss:    () => AU.tone(200, 0.08, "square", 0.08),
  levelup: () => { [523, 587, 659, 784, 880, 1047].forEach((f, i) => AU.tone(f, 0.12, "square", 0.09, AU.ctx && AU.ctx.currentTime + i * 0.08)); },
  victory: () => { [659, 784, 988, 1319].forEach((f, i) => AU.tone(f, 0.18, "square", 0.1, AU.ctx && AU.ctx.currentTime + i * 0.12)); },
  gameover: () => { [392, 330, 262, 196].forEach((f, i) => AU.tone(f, 0.35, "triangle", 0.1, AU.ctx && AU.ctx.currentTime + i * 0.28)); },
  inn:     () => { [523, 494, 440, 523].forEach((f, i) => AU.tone(f, 0.2, "triangle", 0.09, AU.ctx && AU.ctx.currentTime + i * 0.15)); },
  coin:    () => { AU.tone(1047, 0.05, "square", 0.08); AU.tone(1568, 0.12, "square", 0.08, AU.ctx && AU.ctx.currentTime + 0.05); },
  equip:   () => { AU.tone(392, 0.06, "square", 0.1); AU.tone(587, 0.1, "square", 0.1, AU.ctx && AU.ctx.currentTime + 0.06); },
};

AU.sfx = function (name) {
  if (!AU.ctx || AU.muted) return;
  if (AU.ctx.state === "suspended") AU.ctx.resume();
  (SFX[name] || SFX.ok)();
};

/* ---------- BGM ---------- */
// tracks: [{type:'square'|'triangle'|'sawtooth', vol, notes:T(...)}]
// drums: "simple" -> 4つ打ち風
const SONGS = {
  title: {
    tempo: 96,
    tracks: [
      { type: "triangle", vol: 0.16, notes: T("C5:4 G4:4 E4:4 G4:4 A4:4 E4:4 F4:4 D4:4 C5:4 G4:4 E4:4 G4:4 D5:4 B4:4 C5:8") },
      { type: "triangle", vol: 0.10, notes: T("C3:8 F3:8 A3:8 G3:8 C3:8 F3:8 G3:8 C3:8") },
    ],
  },
  town: {
    tempo: 112,
    tracks: [
      { type: "square", vol: 0.11, notes: T("E5:2 E5:2 D5:2 E5:2 C5:4 G4:4 A4:2 G4:2 E4:4 D4:8 E5:2 E5:2 D5:2 E5:2 G5:4 E5:4 D5:2 C5:2 D5:2 E5:2 C5:8") },
      { type: "triangle", vol: 0.11, notes: T("C3:4 G3:4 C4:4 G3:4 F3:4 C4:4 F3:4 A3:4 C3:4 G3:4 E3:4 G3:4 F3:4 G3:4 C4:8") },
    ],
  },
  field: {
    tempo: 128,
    tracks: [
      { type: "square", vol: 0.10, notes: T("G4:2 G4:2 A4:2 B4:2 C5:4 D5:4 E5:2 D5:2 B4:4 G4:8 A4:2 A4:2 B4:2 C5:2 D5:4 B4:4 C5:2 A4:2 G4:8") },
      { type: "triangle", vol: 0.11, notes: T("G3:4 G3:4 C4:4 G3:4 C4:4 D4:4 G3:8 F3:4 F3:4 A3:4 C4:4 D4:4 G3:4 G3:8") },
    ],
    drums: "simple",
  },
  dungeon: {
    tempo: 84,
    tracks: [
      { type: "triangle", vol: 0.13, notes: T("A3:4 A3:4 C4:4 A3:4 D4:4 C4:4 B3:4 A3:4 A3:4 A3:4 C4:4 E4:4 D4:4 C4:4 B3:8") },
      { type: "triangle", vol: 0.09, notes: T("A2:8 F2:8 G2:8 A2:8 A2:8 F2:8 E2:8 A2:8") },
    ],
  },
  battle: {
    tempo: 148,
    tracks: [
      { type: "square", vol: 0.10, notes: T("A4:2 A4:2 C5:2 A4:2 E5:4 D5:4 C5:2 D5:2 E5:4 A4:2 A4:2 C5:2 D5:2 E5:4 D5:4 C5:2 B4:2 A4:4") },
      { type: "sawtooth", vol: 0.08, notes: T("A3:2 A3:2 A3:2 A3:2 F3:2 F3:2 G3:2 G3:2 A3:2 A3:2 A3:2 A3:2 F3:2 G3:2 A3:4") },
    ],
    drums: "battle",
  },
  boss: {
    tempo: 160,
    tracks: [
      { type: "square", vol: 0.11, notes: T("E5:2 E5:2 F5:2 E5:2 D#5:4 E5:4 B4:2 D5:2 C5:4 A4:4 E5:2 E5:2 F5:2 G5:2 A5:4 G5:4 F5:2 E5:2 D#5:4") },
      { type: "sawtooth", vol: 0.09, notes: T("A3:2 A3:2 A3:2 A3:2 A3:2 G#3:2 A3:2 B3:2 A3:2 A3:2 A3:2 A3:2 D3:2 E3:2 A3:4") },
    ],
    drums: "battle",
  },
  ending: {
    tempo: 108,
    tracks: [
      { type: "triangle", vol: 0.15, notes: T("C5:4 D5:2 E5:2 G5:4 A5:4 G5:2 E5:2 C5:8 D5:4 E5:2 D5:2 C5:4 B4:4 C5:12") },
      { type: "triangle", vol: 0.10, notes: T("C3:8 F3:8 G3:8 C4:8 F3:8 G3:8 C4:12") },
    ],
  },
  gameover: {
    tempo: 72,
    tracks: [
      { type: "triangle", vol: 0.13, notes: T("A4:8 F4:4 E4:4 D4:8 C4:4 D4:4 E4:16") },
    ],
  },
};

AU.bgm = function (name) {
  if (!AU.ctx) { AU.wantBgm = name; return; } // init前の要求を保持
  if (AU.song === name) return;
  AU.stopBgm();
  AU.wantBgm = name;
  const s = SONGS[name];
  if (!s) return;
  AU.song = name;
  const spb = 60 / s.tempo / 4; // 16分音符の秒数
  const seqs = s.tracks.map(tr => {
    const ev = [];
    let pos = 0;
    for (const e of tr.notes) { ev.push({ at: pos, n: e.n, len: e.len, type: tr.type, vol: tr.vol }); pos += e.len; }
    return { ev, total: pos, i: 0, next: AU.ctx.currentTime + 0.1 };
  });
  const drum = s.drums;
  let drumStep = 0, drumNext = AU.ctx.currentTime + 0.1;

  AU.seqTimer = setInterval(() => {
    if (!AU.ctx || AU.song !== name) return;
    const horizon = AU.ctx.currentTime + 0.15;
    for (const q of seqs) {
      let guard = 0;
      while (guard++ < 64) {
        const e = q.ev[q.i];
        if (q.next > horizon) break;
        if (e.n) {
          const dur = e.len * spb * 0.92;
          const t = q.next;
          const o = AU.ctx.createOscillator(), g = AU.ctx.createGain();
          o.type = e.type; o.frequency.value = m2f(e.n);
          g.gain.setValueAtTime(e.vol * (AU.muted ? 0 : 1), t);
          g.gain.setValueAtTime(e.vol * (AU.muted ? 0 : 1), t + dur * 0.7);
          g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
          o.connect(g); g.connect(AU.master);
          o.start(t); o.stop(t + dur + 0.02);
        }
        q.next += e.len * spb;
        q.i++;
        if (q.i >= q.ev.length) { q.i = 0; q.next = Math.max(q.next, AU.ctx.currentTime + 0.05); }
      }
    }
    if (drum) {
      let guard = 0;
      while (drumNext <= horizon && guard++ < 64) {
        const st = drumStep % 16;
        if (drum === "battle") {
          if (st % 4 === 0) AU.tone(70, 0.09, "sine", 0.16, drumNext);       // kick
          if (st % 4 === 2) AU.noise(0.06, AU.muted ? 0 : 0.05, drumNext, true); // hat
          if (st === 4 || st === 12) AU.noise(0.12, AU.muted ? 0 : 0.1, drumNext); // snare
        } else {
          if (st % 8 === 0) AU.tone(70, 0.1, "sine", 0.15, drumNext);
          if (st % 4 === 2) AU.noise(0.05, AU.muted ? 0 : 0.04, drumNext, true);
        }
        drumNext += spb;
        drumStep++;
      }
    }
  }, 40);
};

AU.stopBgm = function () {
  if (AU.seqTimer) { clearInterval(AU.seqTimer); AU.seqTimer = null; }
  AU.song = null; AU.wantBgm = null;
};
