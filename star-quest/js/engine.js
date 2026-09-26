/* ============================================================
   スタークエスト - engine.js
   入力 / タイル描画 / スプライト / ウィンドウ / 会話 / 演出
   ============================================================ */

"use strict";

const TS = 16, RT = 32;
const VW = 640, VH = 480;
const VTW = 20, VTH = 15; // 表示タイル数

/* ---------------- 入力 ---------------- */
const Input = { held: new Set(), press: new Set() };
const KEYMAP = {
  ArrowUp: "up", KeyW: "up", ArrowDown: "down", KeyS: "down",
  ArrowLeft: "left", KeyA: "left", ArrowRight: "right", KeyD: "right",
  KeyZ: "ok", Enter: "ok", Space: "ok", KeyJ: "ok",
  KeyX: "cancel", Escape: "cancel", KeyK: "cancel",
  KeyM: "mute",
};
window.addEventListener("keydown", (e) => {
  const k = KEYMAP[e.code];
  if (!k) return;
  e.preventDefault();
  if (!e.repeat) Input.press.add(k); // OSオートリピート抑止(keyup欠落でも再press可)
  Input.held.add(k);
});
window.addEventListener("keyup", (e) => {
  const k = KEYMAP[e.code];
  if (k) Input.held.delete(k);
});
window.addEventListener("blur", () => Input.held.clear());
Input.p = (k) => { if (Input.press.has(k)) { Input.press.delete(k); return true; } return false; };
Input.peek = (k) => Input.press.has(k);
Input.clearFrame = () => Input.press.clear();

const DIRS = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };

/* ---------------- 乱数(決定論的) ---------------- */
function mulberry(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const hash2 = (x, y) => ((x * 73856093) ^ (y * 19349663) ^ 0x9e3779b9) >>> 0;

/* ---------------- タイル描画(オフスクリーンキャッシュ) ---------------- */
const tileCache = {};
const ANIM_TILES = new Set(["~", "o", "S"]); // 2フレームアニメ

function px(c, x, y, w, h, col) { c.fillStyle = col; c.fillRect(x, y, w, h); }
function rnd(c, x, y, w, h, col, r) {
  c.fillStyle = col;
  c.beginPath();
  if (c.roundRect) c.roundRect(x, y, w, h, r || 3);
  else c.rect(x, y, w, h);
  c.fill();
}

const TILE_PAINT = {
  ".": (c, R) => {   // 草
    px(c, 0, 0, 16, 16, "#46a04e");
    for (let i = 0; i < 9; i++) px(c, (R() * 16) | 0, (R() * 16) | 0, 1, 1, "#3a8c42");
    for (let i = 0; i < 5; i++) px(c, (R() * 16) | 0, (R() * 16) | 0, 1, 1, "#58b25e");
  },
  ",": (c, R) => {   // 深い草
    px(c, 0, 0, 16, 16, "#2e7a3a");
    for (let i = 0; i < 14; i++) {
      const x = (R() * 16) | 0, y = (R() * 16) | 0;
      px(c, x, y, 1, 2, R() < 0.5 ? "#256a30" : "#3f9048");
    }
  },
  ";": (c, R) => {   // 深い森草
    px(c, 0, 0, 16, 16, "#1e5c2c");
    for (let i = 0; i < 16; i++) {
      const x = (R() * 16) | 0, y = (R() * 16) | 0;
      px(c, x, y, 1, 2, R() < 0.5 ? "#164a22" : "#2e7040");
    }
  },
  "f": (c, R) => {   // 花の草むら
    TILE_PAINT["."](c, R);
    const cols = ["#e04848", "#f0d040", "#f0f0f0", "#e070b0"];
    for (let i = 0; i < 3; i++) {
      const x = 2 + ((R() * 12) | 0), y = 2 + ((R() * 12) | 0), col = cols[(R() * 4) | 0];
      px(c, x, y, 1, 1, "#f0f0f0");
      px(c, x - 1, y, 1, 1, col); px(c, x + 1, y, 1, 1, col);
      px(c, x, y - 1, 1, 1, col); px(c, x, y + 1, 1, 1, col);
    }
  },
  "p": (c, R) => {   // 道
    px(c, 0, 0, 16, 16, "#b89a58");
    for (let i = 0; i < 8; i++) px(c, (R() * 16) | 0, (R() * 16) | 0, 1, 1, "#9e8044");
    px(c, 0, 0, 16, 1, "rgba(0,0,0,.05)");
  },
  "s": (c, R) => {   // 砂/土
    px(c, 0, 0, 16, 16, "#d0b468");
    for (let i = 0; i < 10; i++) px(c, (R() * 16) | 0, (R() * 16) | 0, 1, 1, "#b89c50");
  },
  "~": (c, R, fr) => { // 水
    px(c, 0, 0, 16, 16, "#1e58c0");
    const off = fr ? 4 : 0;
    for (let i = 0; i < 3; i++) {
      const y = 3 + i * 5;
      for (let x = -8; x < 20; x += 8) {
        px(c, x + off, y, 3, 1, "#5a90e8");
        px(c, x + 1 + off, y + 1, 2, 1, "#5a90e8");
      }
    }
    px(c, 0, 0, 16, 1, "#2f6cd0");
  },
  "=": (c, R, fr) => { // 橋
    TILE_PAINT["~"](c, R, fr);
    px(c, 1, 0, 14, 16, "#7a5428");
    for (let y = 0; y < 16; y += 4) px(c, 1, y, 14, 1, "#5a3c18");
    px(c, 1, 0, 1, 16, "#5a3c18"); px(c, 14, 0, 1, 16, "#5a3c18");
  },
  "#": (c, R, fr, ts) => { // 山/岩壁
    if (ts === "cave") {
      px(c, 0, 0, 16, 16, "#38302a");
      for (let i = 0; i < 6; i++) px(c, (R() * 14) | 0, (R() * 14) | 0, 2, 1, "#282019");
      px(c, 0, 15, 16, 1, "#4a4038");
      return;
    }
    TILE_PAINT["."](c, R);
    c.fillStyle = "#707078";
    c.beginPath(); c.moveTo(2, 15); c.lineTo(8, 3); c.lineTo(14, 15); c.closePath(); c.fill();
    c.fillStyle = "#585860";
    c.beginPath(); c.moveTo(8, 3); c.lineTo(14, 15); c.lineTo(8, 15); c.closePath(); c.fill();
    px(c, 7, 3, 3, 3, "#e8e8e8");
    px(c, 6, 5, 5, 1, "#e8e8e8");
  },
  "T": (c, R) => {   // 木
    TILE_PAINT["."](c, R);
    px(c, 7, 11, 3, 5, "#5a3418");
    c.fillStyle = "#1e6030";
    c.beginPath(); c.arc(8, 6, 6, 0, 7); c.fill();
    c.fillStyle = "#2f8444";
    c.beginPath(); c.arc(6, 5, 3, 0, 7); c.fill();
    px(c, 5, 3, 2, 1, "#46a45a");
  },
  "H": (c, R, fr, ts) => { // 家の壁 / 内壁
    if (ts === "inside") {
      px(c, 0, 0, 16, 16, "#4a3020");
      px(c, 0, 0, 16, 2, "#5a3c26");
      for (let x = 0; x < 16; x += 5) px(c, x, 2, 1, 14, "#3a2416");
      return;
    }
    px(c, 0, 0, 16, 16, "#d8c8a0");
    px(c, 0, 0, 16, 1, "#8a6a40"); px(c, 0, 15, 16, 1, "#8a6a40");
    px(c, 0, 0, 1, 16, "#8a6a40"); px(c, 15, 0, 1, 16, "#8a6a40");
    if (((R() * 10) | 0) < 4) { px(c, 5, 5, 6, 6, "#5a80b0"); px(c, 5, 5, 6, 1, "#3a5878"); }
  },
  "R": (c, R) => {   // 屋根
    px(c, 0, 0, 16, 16, "#a03a28");
    for (let y = 1; y < 16; y += 4) px(c, 0, y, 16, 1, "#782818");
    px(c, 0, 0, 16, 2, "#c05038");
  },
  "D": (c, R, fr, ts) => { // ドア
    TILE_PAINT[ts === "inside" ? "H" : "H"](c, R, fr, "inside");
    rnd(c, 4, 3, 8, 13, "#6a4020", 2);
    px(c, 5, 4, 6, 11, "#7a5028");
    px(c, 7, 9, 1, 1, "#f0c030");
  },
  "F": (c, R, fr, ts) => { // 床
    if (ts === "inside") {
      px(c, 0, 0, 16, 16, "#9a7040");
      px(c, 0, 0, 16, 1, "#8a6030"); px(c, 0, 8, 16, 1, "#8a6030");
      px(c, 8, 0, 1, 8, "#8a6030"); px(c, 3, 8, 1, 8, "#8a6030"); px(c, 12, 8, 1, 8, "#8a6030");
      return;
    }
    px(c, 0, 0, 16, 16, "#5c5c6e");
    px(c, 0, 0, 16, 1, "#484860"); px(c, 0, 8, 16, 1, "#484860");
    px(c, 0, 0, 1, 16, "#484860"); px(c, 8, 8, 1, 8, "#484860");
    for (let i = 0; i < 3; i++) px(c, (R() * 15) | 0, (R() * 15) | 0, 1, 1, "#6a6a7e");
  },
  "W": (c, R) => {   // 石壁
    px(c, 0, 0, 16, 16, "#34344a");
    for (let y = 0; y < 16; y += 4) {
      px(c, 0, y, 16, 1, "#4a4a66");
      for (let x = ((y / 4) % 2) * 4; x < 16; x += 8) px(c, x, y + 1, 1, 3, "#4a4a66");
    }
    px(c, 0, 15, 16, 1, "#26263a");
  },
  "P": (c, R, fr, ts) => { // 柱
    TILE_PAINT.F(c, R, fr, ts);
    rnd(c, 5, 0, 6, 16, "#7878a0", 2);
    px(c, 5, 0, 2, 16, "#9090c0");
    px(c, 4, 0, 8, 2, "#9898c0"); px(c, 4, 14, 8, 2, "#9898c0");
  },
  "o": (c, R, fr, ts) => { // たいまつ
    TILE_PAINT[ts === "inside" ? "F" : "W"](c, R, fr, ts);
    px(c, 7, 8, 2, 7, "#5a3418");
    px(c, 6, 7, 4, 2, "#3a2410");
    c.fillStyle = fr ? "#f09020" : "#f0b030";
    c.beginPath(); c.arc(8, 5, 3, 0, 7); c.fill();
    c.fillStyle = "#f0e040";
    c.beginPath(); c.arc(8, 5, 1.5, 0, 7); c.fill();
  },
  "S": (c, R, fr, ts) => { // 階段
    px(c, 0, 0, 16, 16, "#1c1c2a");
    for (let i = 0; i < 4; i++) px(c, 2 + i, 3 + i * 3, 12 - i * 2, 2, "#4e4e68");
    px(c, 13, 2, 2, 2, fr ? "#f0e040" : "#b0a030");
  },
  "q": (c, R, fr, ts) => { // カウンター
    TILE_PAINT.F(c, R, fr, "inside");
    px(c, 0, 4, 16, 8, "#7a4c24");
    px(c, 0, 4, 16, 3, "#a06a34");
    px(c, 0, 11, 16, 1, "#5a3418");
    px(c, 3, 7, 2, 2, "#5a3418"); px(c, 11, 7, 2, 2, "#5a3418");
  },
  "Q": (c, R, fr, ts) => { // ベッド
    TILE_PAINT.F(c, R, fr, "inside");
    rnd(c, 2, 2, 12, 13, "#6a4020", 2);
    px(c, 3, 3, 10, 3, "#f0f0e8");
    px(c, 3, 6, 10, 7, "#c04040");
    px(c, 3, 10, 10, 1, "#e8e0d0");
  },
  "u": (c, R, fr, ts) => { // テーブル
    TILE_PAINT.F(c, R, fr, "inside");
    rnd(c, 3, 3, 10, 10, "#8a5c2c", 4);
    px(c, 5, 4, 6, 2, "#a8763e");
    px(c, 7, 6, 2, 2, "#6a4020");
  },
  "j": (c, R, fr, ts) => { // つぼ
    TILE_PAINT.F(c, R, fr, "inside");
    rnd(c, 5, 4, 7, 9, "#a07040", 3);
    rnd(c, 6, 3, 5, 3, "#784e28", 1);
    px(c, 6, 6, 2, 2, "#c09058");
  },
  "r": (c, R, fr, ts) => { // カーペット
    TILE_PAINT[ts === "inside" ? "F" : "F"](c, R, fr, ts);
    px(c, 0, 0, 16, 16, "#a02838");
    px(c, 0, 0, 16, 1, "#d8a838"); px(c, 0, 15, 16, 1, "#d8a838");
    px(c, 0, 0, 1, 16, "#d8a838"); px(c, 15, 0, 1, 16, "#d8a838");
    px(c, 7, 7, 2, 2, "#d8a838");
  },
  "G": (c, R, fr, ts, open) => { // 城門
    TILE_PAINT.m(c, R);
    if (open) { px(c, 3, 6, 10, 10, "#0e0e18"); }
    else {
      rnd(c, 3, 4, 10, 12, "#3a2a1a", 2);
      for (let x = 4; x < 13; x += 3) px(c, x, 4, 1, 12, "#8a8a9a");
      px(c, 3, 8, 10, 1, "#8a8a9a");
    }
  },
  "B": (c, R) => { px(c, 0, 0, 16, 16, "#2a2a3e"); px(c, 0, 0, 16, 1, "#20203a"); px(c, 0, 0, 1, 16, "#20203a"); },
  "X": (c, R, fr, ts) => { // 岩
    TILE_PAINT.F(c, R, fr, ts);
    c.fillStyle = "#686878";
    c.beginPath(); c.arc(8, 9, 6, 0, 7); c.fill();
    px(c, 5, 5, 4, 3, "#7e7e90");
  },
  "m": (c, R) => {   // 城壁
    px(c, 0, 0, 16, 16, "#565670");
    for (let y = 0; y < 16; y += 4) {
      px(c, 0, y, 16, 1, "#40405a");
      for (let x = ((y / 4) % 2) * 4; x < 16; x += 8) px(c, x, y + 1, 1, 3, "#40405a");
    }
    px(c, 0, 0, 16, 2, "#6e6e8e");
  },
  "V": (c, R) => {   // 井戸
    TILE_PAINT["."](c, R);
    c.fillStyle = "#787878";
    c.beginPath(); c.arc(8, 8, 6, 0, 7); c.fill();
    c.fillStyle = "#101018";
    c.beginPath(); c.arc(8, 8, 4, 0, 7); c.fill();
    px(c, 5, 1, 2, 3, "#7a5428"); px(c, 9, 1, 2, 3, "#7a5428");
    px(c, 4, 0, 8, 1, "#a03a28");
  },
  "n": (c, R) => {   // 洞窟入口
    TILE_PAINT["."](c, R);
    c.fillStyle = "#484038";
    c.beginPath(); c.arc(8, 10, 8, Math.PI, 0); c.fill();
    c.fillStyle = "#080810";
    c.beginPath(); c.arc(8, 10, 5, Math.PI, 0); c.fill();
    px(c, 3, 10, 10, 6, "#080810");
  },
  "!": (c, R, fr, ts) => { // 出口マット
    TILE_PAINT[ts === "field" ? "." : ts === "town" ? "." : "F"](c, R, fr, ts);
    px(c, 0, 0, 16, 16, "rgba(0,0,0,.35)");
    px(c, 4, 7, 8, 2, "#f0e040");
    c.fillStyle = "#f0e040";
    c.beginPath(); c.moveTo(6, 4); c.lineTo(10, 4); c.lineTo(8, 7); c.closePath(); c.fill();
  },
  "x": (c, R) => {   // 柵
    TILE_PAINT["."](c, R);
    px(c, 0, 6, 16, 2, "#8a5c2c"); px(c, 0, 11, 16, 2, "#8a5c2c");
    px(c, 3, 3, 2, 13, "#6a4020"); px(c, 11, 3, 2, 13, "#6a4020");
  },
  "Z": (c, R, fr, ts) => { // ボス扉
    TILE_PAINT.W(c, R);
    rnd(c, 3, 2, 10, 14, "#241e30", 3);
    px(c, 4, 3, 8, 12, "#2e2438");
    px(c, 6, 7, 4, 4, "#8048d0");
    px(c, 7, 8, 2, 2, "#c03030");
  },
  "E": (c, R, fr, ts) => TILE_PAINT.F(c, R, fr, ts),
  "d": (c, R, fr, ts) => TILE_PAINT.F(c, R, fr, ts),
};

function tileCanvas(tileset, ch, variant, frame, openGate) {
  const key = `${tileset}|${ch}|${variant || 0}|${frame || 0}|${openGate ? 1 : 0}`;
  if (tileCache[key]) return tileCache[key];
  const cv = document.createElement("canvas");
  cv.width = 16; cv.height = 16;
  const c = cv.getContext("2d");
  const painter = TILE_PAINT[ch] || TILE_PAINT["."];
  const R = mulberry(hash2(variant || 0, (frame || 0) + ch.charCodeAt(0) * 131));
  painter(c, R, frame || 0, tileset, openGate);
  tileCache[key] = cv;
  return cv;
}

// タイルに応じたバリエーション数
function tileVariants(ch) {
  if (ch === "." || ch === "," || ch === ";") return 3;
  return 1;
}

/* ---------------- スプライト描画 ---------------- */
function sprCanvas(spr) {
  if (spr._cv) return spr._cv;
  const cv = document.createElement("canvas");
  cv.width = spr.w; cv.height = spr.h;
  const c = cv.getContext("2d");
  for (let y = 0; y < spr.h; y++) {
    const row = spr.rows[y];
    for (let x = 0; x < spr.w && x < row.length; x++) {
      const col = spr.pal[row[x]];
      if (col && row[x] !== ".") {
        c.fillStyle = col;
        c.fillRect(x, y, 1, 1);
      }
    }
  }
  spr._cv = cv;
  return cv;
}

function drawSpr(ctx, spr, dx, dy, scale) {
  const s = scale || 2;
  ctx.drawImage(sprCanvas(spr), dx, dy, spr.w * s, spr.h * s);
}

// 宝箱(手続き描画)
function chestCanvas(open) {
  const cv = document.createElement("canvas");
  cv.width = 16; cv.height = 16;
  const c = cv.getContext("2d");
  if (open) {
    px(c, 3, 3, 10, 4, "#8a5c2c");
    px(c, 4, 4, 8, 2, "#6a4020");
    px(c, 3, 8, 10, 6, "#7a4c24");
    px(c, 3, 8, 10, 1, "#a8763e");
    px(c, 7, 9, 2, 2, "#f0c030");
  } else {
    rnd(c, 2, 5, 12, 9, "#8a5c2c", 2);
    px(c, 2, 5, 12, 2, "#a8763e");
    px(c, 2, 8, 12, 1, "#5a3418");
    px(c, 6, 5, 4, 9, "#f0c030");
    px(c, 7, 7, 2, 3, "#5a3418");
  }
  return cv;
}

/* ---------------- テキスト/ウィンドウ ---------------- */
const FONT_FAMILY = '"Hiragino Kaku Gothic ProN","Yu Gothic","Yu Gothic UI",Meiryo,"Noto Sans CJK JP","Noto Sans JP","IPA Gothic",sans-serif';
const FONT = '14px ' + FONT_FAMILY;

function txt(ctx, s, x, y, opt) {
  opt = opt || {};
  ctx.font = (opt.size || 14) + 'px ' + FONT_FAMILY;
  ctx.textBaseline = "top";
  ctx.textAlign = opt.align || "left";
  ctx.fillStyle = opt.shadow === false ? "transparent" : "#000";
  if (opt.shadow !== false) ctx.fillText(s, x + 1, y + 1);
  ctx.fillStyle = opt.color || "#f0f0f8";
  ctx.fillText(s, x, y);
  ctx.textAlign = "left";
}

function win(ctx, x, y, w, h, opt) {
  ctx.fillStyle = (opt && opt.bg) || "rgba(8,10,32,0.93)";
  ctx.fillRect(x, y, w, h);
  ctx.strokeStyle = "#f0f0f8"; ctx.lineWidth = 2;
  ctx.strokeRect(x + 1, y + 1, w - 2, h - 2);
  ctx.strokeStyle = "rgba(160,170,220,.4)"; ctx.lineWidth = 1;
  ctx.strokeRect(x + 4, y + 4, w - 8, h - 8);
}

function cursor(ctx, x, y, t) {
  const bob = Math.sin(t / 6) * 2;
  ctx.fillStyle = "#f0e040";
  ctx.beginPath();
  ctx.moveTo(x + bob, y);
  ctx.lineTo(x + 7 + bob, y + 5);
  ctx.lineTo(x + bob, y + 10);
  ctx.closePath(); ctx.fill();
}

function wrapText(ctx, s, maxW) {
  ctx.font = FONT;
  const lines = [];
  let cur = "";
  for (const ch of s) {
    if (ch === "\n") { lines.push(cur); cur = ""; continue; }
    if (ctx.measureText(cur + ch).width > maxW && cur) { lines.push(cur); cur = ch; }
    else cur += ch;
  }
  if (cur) lines.push(cur);
  return lines;
}

/* ---------------- 演出 ---------------- */
const FX = {
  fade: 1, fadeTarget: 0, fadeSpeed: 0.04, fadeCb: null,
  shakeT: 0, shakeAmt: 0,
  flashA: 0, flashColor: "#fff",
  battleWipe: -1, // -1 無効, 0..1
};

FX.fadeTo = function (target, speed, cb) {
  FX.fadeTarget = target; FX.fadeSpeed = speed || 0.05; FX.fadeCb = cb || null;
  if (FX.fade === FX.fadeTarget && FX.fadeCb) {
    const c2 = FX.fadeCb; FX.fadeCb = null; c2();
  }
};
FX.shake = function (frames, amt) { FX.shakeT = frames; FX.shakeAmt = amt; };
FX.flash = function (a, color) { FX.flashA = a; FX.flashColor = color || "#fff"; };
FX.wipe = function () { FX.battleWipe = 0; };

FX.update = function () {
  if (FX.fade !== FX.fadeTarget) {
    const d = FX.fadeTarget - FX.fade;
    const step = FX.fadeSpeed;
    if (Math.abs(d) <= step) {
      FX.fade = FX.fadeTarget;
      if (FX.fadeCb) { const cb = FX.fadeCb; FX.fadeCb = null; cb(); }
    } else FX.fade += Math.sign(d) * step;
  }
  if (FX.shakeT > 0) FX.shakeT--;
  if (FX.flashA > 0) FX.flashA = Math.max(0, FX.flashA - 0.04);
  if (FX.battleWipe >= 0 && FX.battleWipe < 1) FX.battleWipe = Math.min(1, FX.battleWipe + 0.035);
};

FX.drawOverlay = function (ctx) {
  if (FX.shakeT > 0) { /* shakeは呼び出し側でcameraに反映 */ }
  if (FX.flashA > 0) {
    ctx.fillStyle = FX.flashColor; ctx.globalAlpha = FX.flashA;
    ctx.fillRect(0, 0, VW, VH); ctx.globalAlpha = 1;
  }
  if (FX.battleWipe >= 0) {
    const n = 8, h = VH / n;
    ctx.fillStyle = "#000";
    for (let i = 0; i < n; i++) {
      const w = VW * FX.battleWipe;
      if (i % 2 === 0) ctx.fillRect(0, i * h, w, h);
      else ctx.fillRect(VW - w, i * h, w, h);
    }
  }
  if (FX.fade > 0) {
    ctx.fillStyle = `rgba(0,0,0,${FX.fade})`;
    ctx.fillRect(0, 0, VW, VH);
  }
};

/* ---------------- シーン管理 ---------------- */
const Scene = {
  stack: [],
  push(s) { Scene.stack.push(s); if (s.enter) s.enter(); },
  pop() { const s = Scene.stack.pop(); if (s && s.leave) s.leave(); return s; },
  replace(s) { Scene.pop(); Scene.push(s); },
  top() { return Scene.stack[Scene.stack.length - 1]; },
  clear() { while (Scene.stack.length) Scene.pop(); },
};

/* ---------------- 会話シーン ---------------- */
// scriptFn(api) が api.say/choice/... でステップを積む
function runScript(scriptFn) {
  const sc = {
    isDialog: true,
    queue: [],
    idx: 0,
    page: null,        // {lines, li, ci}
    name: null,
    choiceSel: 0,
    typing: 0,
    done: false,
  };
  const api = makeApi(sc);
  scriptFn(api);
  const closeSelf = () => {
    sc.done = true;
    const i = Scene.stack.indexOf(sc);
    if (i >= 0) Scene.stack.splice(i, 1);
    else Scene.pop();
  };
  sc.close = closeSelf;
  sc.next = () => {
    if (sc.idx >= sc.queue.length) { closeSelf(); return; }
    const st = sc.queue[sc.idx];
    if (st.k === "say") {
      const cv = G.ctx;
      const all = [];
      for (const line of st.lines) for (const l of wrapText(cv, line, 480)) all.push(l);
      sc.name = st.name; sc.page = { lines: all, li: 0, ci: 0 };
    } else if (st.k === "choice") {
      sc.choiceSel = 0; sc.page = null;
    } else if (st.k === "fn") {
      st.f(); sc.idx++; sc.next();
    }
  };
  sc.next();

  sc.update = function () {
    if (this.idx >= this.queue.length) { closeSelf(); return; }
    const st = this.queue[this.idx];
    if (st.k === "say") {
      const p = this.page;
      const line = p.lines[p.li];
      if (p.ci < line.length) {
        p.ci += 0.5;
        if (p.ci >= line.length) p.ci = line.length;
        if ((p.ci | 0) % 4 === 0) AU.sfx("talk");
      }
      if (Input.p("ok")) {
        if (p.ci < line.length) p.ci = line.length;
        else {
          p.li++; p.ci = 0;
          if (p.li >= p.lines.length) { this.idx++; this.next(); }
        }
      }
    } else if (st.k === "choice") {
      if (Input.p("up")) { this.choiceSel = (this.choiceSel + st.opts.length - 1) % st.opts.length; AU.sfx("cursor"); }
      if (Input.p("down")) { this.choiceSel = (this.choiceSel + 1) % st.opts.length; AU.sfx("cursor"); }
      if (Input.p("ok")) {
        const cb = st.cb, sel = this.choiceSel;
        this.idx++; AU.sfx("ok");
        if (cb) cb(sel);
        if (this.idx < this.queue.length || !this.done) this.next();
      }
    } else { this.idx++; this.next(); }
  };

  sc.draw = function (ctx) {
    const st = this.queue[this.idx];
    if (!st) return;
    if (st.k === "say" && this.page) {
      win(ctx, 20, VH - 120, VW - 40, 104);
      if (this.name) {
        win(ctx, 24, VH - 140, ctx.measureText(this.name).width + 44, 26, { bg: "rgba(8,10,32,.93)" });
        txt(ctx, this.name, 46, VH - 135, { color: "#f0c030" });
      }
      const p = this.page;
      for (let i = 0; i <= p.li && i < p.lines.length; i++) {
        const l = i === p.li ? p.lines[i].slice(0, p.ci | 0) : p.lines[i];
        txt(ctx, l, 40, VH - 100 + i * 24);
      }
      if (p.ci >= (p.lines[p.li] || "").length && p.li === p.lines.length - 1) {
        txt(ctx, "▼", VW / 2 - 6, VH - 32, { color: "#f0e040" });
      }
    } else if (st.k === "choice") {
      const w = 180, h = st.opts.length * 26 + 18;
      win(ctx, VW - w - 30, VH - 120 - h - 10, w, h);
      st.opts.forEach((o, i) => {
        txt(ctx, o, VW - w + 14, VH - 120 - h + 10 + i * 26);
      });
      cursor(ctx, VW - w - 14, VH - 120 - h + 11 + this.choiceSel * 26, G.tick);
    }
  };
  Scene.push(sc);
  return sc;
}

/* ---------------- スクリプトAPI ---------------- */
function makeApi(sc) {
  return {
    say: (lines, name) => sc.queue.push({ k: "say", lines: Array.isArray(lines) ? lines : [lines], name }),
    choice: (opts, cb) => sc.queue.push({ k: "choice", opts, cb }),
    fn: (f) => sc.queue.push({ k: "fn", f }),
    flag: (k) => !!G.flags[k],
    setFlag: (k, v) => { G.flags[k] = v; },
    giveItem: (id, n) => { addItem(id, n || 1); },
    giveGold: (g) => { G.player.gold += g; },
    giveGear: (id) => { G.player.bag.push(id); },
    openShop: () => sc.queue.push({ k: "fn", f: () => Scene.push(makeShopScene()) }),
    rest: () => sc.queue.push({ k: "fn", f: innRest }),
    bossBattle: () => sc.queue.push({ k: "fn", f: () => startBossBattle() }),
    heal: () => { G.player.hp = G.player.maxhp; G.player.mp = G.player.maxmp; },
  };
}

// shop/battle/inn は field.js / battle.js で定義(前方宣言的に使う)
let makeShopScene, innRest, startBossBattle;
