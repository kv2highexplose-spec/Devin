/* ============================================================
   スタークエスト - main.js
   起動・グローバル状態・メインループ
   ============================================================ */

"use strict";

const cv = document.getElementById("game");
const ctx = cv.getContext("2d");
ctx.imageSmoothingEnabled = false;

/* ---------------- グローバル状態 ---------------- */
const G = {
  player: null,
  pos: { map: "town", x: 12, y: 15, dir: "up" },
  flags: {},
  tick: 0,
  ctx,
};

function newPlayer() {
  return {
    lv: 1, exp: 0, gold: 30, hp: 20, mp: 0,
    weapon: "w_stick", armor: "a_cloth",
    bag: ["w_stick", "a_cloth"],
    items: { potion: 1 },
    spells: [],
  };
}

/* ---------------- ニューゲーム ---------------- */
function startNewGame() {
  G.player = newPlayer();
  G.flags = {};
  const f = makeFieldScene();
  Scene.push(f);
  f.load("town", 12, 15, "up");
  G.pos = { map: "town", x: 12, y: 15, dir: "up" };
  FX.fade = 1;
  FX.fadeTo(0, 0.05);
  runScript((api) => {
    api.say([
      "むかしむかし、ルミナの大地は ほしのひかりに まもられていた。",
      "しかし 魔王ヴァルドラスが『ほしのかけら』を うばい、",
      "せかいは くらい かげに おおわれてしまった…。",
    ]);
    api.say([
      "ゆうしゃは ルミナの村に たちあがる。",
      "まずは にしにある ちょうろうの家へ むかおう。",
    ]);
  });
}

/* ---------------- データ検証 ---------------- */
const dataErr = validateData();
if (dataErr.length) console.error("DATA ERRORS:", dataErr);

/* ---------------- メインループ ---------------- */
Scene.push(makeTitleScene());
FX.fade = 1;
FX.fadeTo(0, 0.04);

function frame() {
  try {
    G.tick++;
    FX.update();
    const top = Scene.top();
    if (top && top.update) top.update();
    if (Input.p("mute")) AU.setMuted(!AU.muted);

    // 描画: 最後のopaqueシーンから上を描く
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, VW, VH);
    let start = 0;
    for (let i = Scene.stack.length - 1; i >= 0; i--) {
      if (Scene.stack[i].opaque) { start = i; break; }
    }
    ctx.save();
    if (FX.shakeT > 0) {
      ctx.translate((Math.random() - 0.5) * 2 * FX.shakeAmt, (Math.random() - 0.5) * 2 * FX.shakeAmt);
    }
    for (let i = start; i < Scene.stack.length; i++) Scene.stack[i].draw(ctx);
    ctx.restore();

    FX.drawOverlay(ctx);
  } catch (e) {
    console.error("frame error:", e);
  }
  Input.clearFrame();
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

/* ---------------- デバッグ/検証フック ---------------- */
window.SQ = {
  G, Scene, FX, Input,
  tp(map, x, y) {
    const f = Scene.stack.find(s => s.isField);
    if (f) f.load(map, x, y, "down");
    G.pos = { map, x, y, dir: "down" };
  },
  battle(zone) { if (!G.player) return false; Scene.push(makeBattleScene(zone)); return true; },
  boss() { if (!G.player) return false; Scene.push(makeBattleScene("boss")); return true; },
  lv(n) { G.player.lv = n; const st = pStats(); G.player.hp = st.maxhp; G.player.mp = st.maxmp; },
  gold(n) { G.player.gold = n; },
  item(id, n) { addItem(id, n || 1); },
  gear(id) { G.player.bag.push(id); },
  equip(id) { const g = GEAR[id]; if (!g) return; if (g.type === "w") G.player.weapon = id; else G.player.armor = id; },
  learnAll() { for (const s in SPELLS) if (!G.player.spells.includes(s)) G.player.spells.push(s); },
  newGame() { startNewGame(); },
  save() { saveGame(); },
  scene() {
    return Scene.stack.map(s => s.isField ? "field:" + s.mapId :
      s.isBattle ? "battle" : s.isDialog ? "dialog" :
      s.isShop ? "shop" : s.isMenu ? "menu" : "scene");
  },
};
