/* ============================================================
   スタークエスト - title.js
   タイトル / ゲームオーバー / エンディング
   ============================================================ */

"use strict";

/* ---------------- 星空背景 ---------------- */
const STARS = [];
for (let i = 0; i < 120; i++) {
  const r = mulberry(i * 977 + 13);
  STARS.push({
    x: r() * VW, y: r() * VH,
    sp: 0.15 + r() * 0.5,
    sz: r() < 0.15 ? 2 : 1,
    ph: r() * 6.28,
  });
}
function drawStars(ctx, t, scroll) {
  for (const s of STARS) {
    const y = (s.y + (scroll ? t * s.sp : 0)) % VH;
    const a = 0.35 + 0.55 * Math.abs(Math.sin(t / 30 + s.ph));
    ctx.fillStyle = `rgba(240,240,255,${a})`;
    ctx.fillRect(s.x, y, s.sz, s.sz);
  }
}

/* ---------------- タイトル ---------------- */
function makeTitleScene() {
  const T = { opaque: true, sel: 0, t: 0 };
  AU.bgm("title");
  const opts = [];
  opts.push("はじめから");
  if (hasSave()) opts.push("つづきから");
  opts.push(AU.muted ? "おと：なし" : "おと：あり");
  T.opts = opts;

  T.update = function () {
    T.t++;
    if (Input.p("up")) { T.sel = (T.sel + T.opts.length - 1) % T.opts.length; AU.sfx("cursor"); }
    if (Input.p("down")) { T.sel = (T.sel + 1) % T.opts.length; AU.sfx("cursor"); }
    if (Input.p("ok")) {
      const o = T.opts[T.sel];
      if (o === "はじめから") {
        AU.sfx("ok");
        FX.fadeTo(1, 0.05, () => { Scene.clear(); startNewGame(); });
      } else if (o === "つづきから") {
        const d = loadGame();
        if (!d) { AU.sfx("cancel"); return; }
        AU.sfx("ok");
        FX.fadeTo(1, 0.05, () => {
          Scene.clear();
          G.player = Object.assign(newPlayer(), d.player);
          G.flags = d.flags || {};
          const f = makeFieldScene();
          Scene.push(f);
          f.load(d.pos.map, d.pos.x, d.pos.y, d.pos.dir);
          G.pos = d.pos;
          FX.fadeTo(0, 0.05);
        });
      } else {
        AU.setMuted(!AU.muted);
        T.opts[T.sel] = AU.muted ? "おと：なし" : "おと：あり";
      }
    }
  };

  T.draw = function (ctx) {
    ctx.fillStyle = "#060614"; ctx.fillRect(0, 0, VW, VH);
    drawStars(ctx, T.t, true);
    // 大きな星
    ctx.fillStyle = "#f0e040";
    ctx.save();
    ctx.translate(VW / 2, 118);
    ctx.rotate(Math.PI / 4);
    const sc = 1 + Math.sin(T.t / 40) * 0.05;
    ctx.fillRect(-16 * sc, -16 * sc, 32 * sc, 32 * sc);
    ctx.restore();
    ctx.fillStyle = "#f8f090";
    ctx.fillRect(VW / 2 - 8, 110, 16, 16);

    txt(ctx, "スタークエスト", VW / 2, 168, { align: "center", size: 46, color: "#f0e0a0" });
    txt(ctx, "～ほしのかけらを おいもとめて～", VW / 2, 224, { align: "center", size: 15, color: "#98a8d8" });

    const w = 220, h = T.opts.length * 34 + 22;
    win(ctx, VW / 2 - w / 2, 300, w, h);
    T.opts.forEach((o, i) => {
      txt(ctx, o, VW / 2, 318 + i * 34, { align: "center", size: 18 });
    });
    ctx.fillStyle = "#f0e040";
    const bob = Math.sin(T.t / 7) * 2;
    ctx.beginPath();
    ctx.moveTo(VW / 2 - 88 + bob, 318 + T.sel * 34 + 4);
    ctx.lineTo(VW / 2 - 78 + bob, 318 + T.sel * 34 + 9);
    ctx.lineTo(VW / 2 - 88 + bob, 318 + T.sel * 34 + 14);
    ctx.closePath(); ctx.fill();

    txt(ctx, "Z・Enter：けってい   やじるし：えらぶ   M：おと", VW / 2, VH - 34, { align: "center", size: 12, color: "#6878a0" });
  };
  return T;
}

/* ---------------- ゲームオーバー ---------------- */
function makeGameOverScene() {
  const S = { opaque: true, t: 0 };
  AU.sfx("gameover");
  AU.bgm("gameover");
  S.update = function () {
    S.t++;
    if (S.t > 80 && Input.p("ok")) {
      // 村でふっかつ(おかね半分)
      const st = pStats();
      G.player.hp = st.maxhp;
      G.player.mp = st.maxmp;
      G.player.gold = Math.floor(G.player.gold * 0.5);
      Scene.clear();
      const f = makeFieldScene();
      Scene.push(f);
      f.load("town", 12, 15, "up");
      G.pos = { map: "town", x: 12, y: 15, dir: "up" };
      FX.fade = 1; FX.fadeTo(0, 0.05);
      runScript((api) => api.say([
        "ゆうしゃは ちょうろうの いのりで よみがえった。",
        "おかねを はんぶん うしなってしまった… きを つけよう！",
      ]));
    }
  };
  S.draw = function (ctx) {
    ctx.fillStyle = "#08080e"; ctx.fillRect(0, 0, VW, VH);
    if (S.t > 30) {
      txt(ctx, "GAME OVER", VW / 2, 190, { align: "center", size: 42, color: "#b03030" });
    }
    if (S.t > 80) {
      txt(ctx, "Z を おしてください", VW / 2, 300, { align: "center", size: 15, color: "#9090a8" });
    }
  };
  return S;
}

/* ---------------- エンディング ---------------- */
function makeEndingScene() {
  const E = { opaque: true, t: 0, phase: 0, phaseT: 0 };
  AU.sfx("victory");
  AU.bgm("ending");
  saveGame(); // セーブしておく(ボス撃破済みフラグ込み)

  const CREDITS = [
    "",
    "",
    "スタークエスト",
    "",
    "～ほしのかけらを おいもとめて～",
    "",
    "",
    "ほしのかけらは そらへ もどり",
    "ルミナの大地に ひかりが もどった。",
    "",
    "ちょうろう「よくやった ゆうしゃよ…",
    "　　　　 まことの ゆうきを もつものだ。」",
    "",
    "むらびと「ありがとう ゆうしゃ！」",
    "",
    "",
    "　　企画・制作　Devin",
    "　　シナリオ　　きみの ぼうけん",
    "　　音楽　　　　Web Audio API",
    "　　キャラ絵　　プロシージャル",
    "",
    "",
    "　　魔王ヴァルドラス",
    "　　あんこくのさけび",
    "",
    "",
    "",
    "おしまい",
    "",
    "　　ありがとう！",
  ];

  E.update = function () {
    E.t++;
    if (E.phase === 0) {
      E.phaseT++;
      if (E.phaseT > 200) { E.phase = 1; }
      if (Input.p("ok")) E.phase = 1;
    } else {
      E.phaseT++;
      if (Input.p("ok") || E.phaseT > 1400) {
        FX.fadeTo(1, 0.03, () => {
          Scene.clear();
          Scene.push(makeTitleScene());
          FX.fade = 1; FX.fadeTo(0, 0.04);
        });
        E.phase = 2;
      }
    }
  };

  E.draw = function (ctx) {
    ctx.fillStyle = "#050510"; ctx.fillRect(0, 0, VW, VH);
    drawStars(ctx, E.t, E.phase === 1);

    if (E.phase === 0) {
      // おひさまがのぼる
      const a = Math.min(1, E.phaseT / 160);
      const g = ctx.createRadialGradient(VW / 2, 420, 10, VW / 2, 420, 260);
      g.addColorStop(0, `rgba(255,220,120,${0.9 * a})`);
      g.addColorStop(0.4, `rgba(240,160,80,${0.5 * a})`);
      g.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, VW, VH);
      txt(ctx, "ほしのかけらを てにいれた！！", VW / 2, 200, { align: "center", size: 22, color: "#f0e0a0" });
    } else if (E.phase === 1) {
      // スタッフロール
      const baseY = VH - E.phaseT * 0.55;
      CREDITS.forEach((l, i) => {
        const y = baseY + i * 30;
        if (y > -20 && y < VH + 20) {
          const big = l === "スタークエスト" || l === "おしまい";
          txt(ctx, l, VW / 2, y, { align: "center", size: big ? 28 : 15, color: big ? "#f0e0a0" : "#d0d8f0" });
        }
      });
      // ゆうしゃが前を歩く
      const frame = [1, 0, 2, 0][(E.t >> 3) & 3];
      drawSpr(ctx, SPR["hero_up" + frame], VW / 2 - 16, VH - 80, 2);
    }
  };
  return E;
}
