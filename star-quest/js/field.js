/* ============================================================
   スタークエスト - field.js
   フィールド探索 / NPC / 宝箱 / メニュー / ショップ / 宿屋
   ============================================================ */

"use strict";

/* ---------------- アイテム所持 ---------------- */
function addItem(id, n) {
  G.player.items[id] = (G.player.items[id] || 0) + (n || 1);
}
function takeItem(id, n) {
  if (!G.player.items[id]) return false;
  G.player.items[id] -= (n || 1);
  if (G.player.items[id] <= 0) delete G.player.items[id];
  return true;
}
function itemCount(id) { return G.player.items[id] || 0; }

/* ---------------- フィールドシーン ---------------- */
function makeFieldScene() {
  const F = {
    isField: true,
    mapId: null, map: null,
    tx: 0, ty: 0, dir: "down",
    px: 0, py: 0,          // プレイヤー画素位置(左上)
    moving: false, mvFrom: null, mvTo: null, mvT: 0,
    animT: 0,
    npcs: [], chests: [],
    camX: 0, camY: 0,
    toast: "", toastT: 0,
    pendingBattle: null,
    bumpCD: 0,
    busy: false,
  };

  const SPEED = 4; // px/frame (8f/tile)

  F.load = function (mapId, x, y, dir) {
    F.mapId = mapId;
    F.map = MAPS[mapId];
    F.tx = x; F.ty = y;
    F.dir = dir || "down";
    F.px = x * RT; F.py = y * RT;
    F.moving = false;
    F.rebuild();
    F.toast = F.map.name; F.toastT = 110;
    F.bgmName = bgmFor(F.map.tileset);
    AU.bgm(F.bgmName);
  };

  function bgmFor(ts) {
    return { field: "field", town: "town", inside: "town", cave: "dungeon", castle: "dungeon" }[ts] || "field";
  }

  F.rebuild = function () {
    F.npcs = (F.map.npcs || []).filter(n => {
      if (n.talk === "boss" && G.flags.bossDown) return false;
      return true;
    }).map(n => ({ x: n.x, y: n.y, spr: n.spr, name: n.name, talk: n.talk, wander: n.wander, big: n.big, wt: 60 + ((hash2(n.x, n.y) % 120)), bob: 0, hopping: 0 }));
    F.chests = (F.map.chests || []).filter(c => !G.flags["chest_" + c.id]);
  };

  function tileAt(x, y) {
    if (!F.map) return "#";
    if (x < 0 || y < 0 || x >= F.map.tiles[0].length || y >= F.map.tiles.length) return "#";
    return F.map.tiles[y][x];
  }
  F.tileAt = tileAt;

  function npcAt(x, y) {
    for (const n of F.npcs) if (n.x === x && n.y === y) return n;
    return null;
  }
  function chestAt(x, y) {
    for (const c of F.chests) if (c.x === x && c.y === y) return c;
    return null;
  }
  F.npcAt = npcAt; F.chestAt = chestAt;

  F.canWalk = function (x, y) {
    const ch = tileAt(x, y);
    const p = TILE_PROPS[ch];
    if (!p) return false;
    if (ch === "G") return !!G.flags.castleGate;
    if (p.block) return false;
    if (npcAt(x, y) || chestAt(x, y)) return false;
    return true;
  };

  /* ---- ワープ実行 ---- */
  function doWarp(wp) {
    FX.fadeTo(1, 0.09, () => {
      F.load(wp.to, wp.tx, wp.ty, wp.dir);
      G.pos = { map: wp.to, x: wp.tx, y: wp.ty, dir: wp.dir || "down" };
      FX.fadeTo(0, 0.06);
    });
    AU.sfx(tileAt(wp.x, wp.y) === "S" ? "stairs" : "door");
  }

  /* ---- 会話 ---- */
  F.talk = function (npc) {
    npc.hopping = 12;
    runScript(SCRIPTS[npc.talk]);
  };

  /* ---- 宝箱 ---- */
  F.openChest = function (c) {
    G.flags["chest_" + c.id] = true;
    AU.sfx("chest");
    runScript((api) => {
      if (c.key === "hikariKey") {
        api.setFlag("hikariKey", true);
        api.say(["たからばこを あけた！", "…なんと！『ひかりのカギ』を みつけた！！",
                 "これで きたの まおうじょうの もんが ひらくはずだ。"]);
      } else if (c.gold) {
        api.giveGold(c.gold);
        api.say([`たからばこを あけた！`, `${c.gold}G を みつけた！`]);
      } else if (c.item) {
        api.giveItem(c.item, 1);
        api.say([`たからばこを あけた！`, `${ITEMS[c.item].name}を みつけた！`]);
      } else if (c.gear) {
        api.giveGear(c.gear);
        api.say([`たからばこを あけた！`, `${GEAR[c.gear].name}を みつけた！`]);
      }
      api.fn(() => F.rebuild());
    });
  };

  /* ---- 城門 ---- */
  function tryGate(x, y) {
    if (tileAt(x, y) !== "G") return false;
    if (G.flags.castleGate) return false;
    if (!G.flags.hikariKey) {
      runScript((api) => api.say([
        "もんは かたく とざされている…。",
        "『ひかりのカギ』が ひつようだ。にしの どうくつに あるらしい。",
      ]));
      return true;
    }
    G.flags.castleGate = true;
    AU.sfx("chest");
    runScript((api) => api.say([
      "『ひかりのカギ』が ひかりをはなった！",
      "もんが おもそうに ひらいていく…！！",
    ]));
    return true;
  }

  /* ---- 移動 ---- */
  function tryMove(dx, dy, dir) {
    F.dir = dir;
    const nx = F.tx + dx, ny = F.ty + dy;
    if (tryGate(nx, ny)) return;
    if (!F.canWalk(nx, ny)) {
      // 壁ぶつかり: 向きだけ変える
      return;
    }
    F.moving = true;
    F.mvFrom = { x: F.px, y: F.py };
    F.mvTo = { x: nx * RT, y: ny * RT };
    F.mvT = 0;
  }

  /* ---- 着地時処理 ---- */
  function onLand() {
    // ワープ
    for (const wp of (F.map.warps || [])) {
      if (wp.x === F.tx && wp.y === F.ty) { doWarp(wp); return; }
    }
    // トリガー
    for (const tr of (F.map.triggers || [])) {
      if (tr.x === F.tx && tr.y === F.ty) {
        const fn = SCRIPTS[tr.script];
        if (fn) runScript(fn);
        return;
      }
    }
    // エンカウント
    const ch = tileAt(F.tx, F.ty);
    const zone = F.map.zone || (TILE_PROPS[ch] && TILE_PROPS[ch].zone);
    if (zone && Math.random() < (F.map.encRate || 0)) {
      startEncounter(zone);
    }
  }

  function startEncounter(zone) {
    AU.sfx("encounter");
    FX.wipe();
    F.pendingBattle = zone;
  }

  /* ---- 相互作用 ---- */
  function interact() {
    const d = DIRS[F.dir];
    const fx = F.tx + d[0], fy = F.ty + d[1];
    const n = npcAt(fx, fy);
    if (n) { F.talk(n); return true; }
    const c = chestAt(fx, fy);
    if (c) { F.openChest(c); return true; }
    // カウンター越し
    if (tileAt(fx, fy) === "q") {
      const n2 = npcAt(fx + d[0], fy + d[1]);
      if (n2) { F.talk(n2); return true; }
    }
    if (tileAt(fx, fy) === "V") {
      runScript((api) => api.say(["つめたい いどのみずが たたえられている。"]));
      return true;
    }
    return false;
  }

  /* ---- 更新 ---- */
  F.update = function () {
    if (F.pendingBattle && FX.battleWipe >= 1) {
      const z = F.pendingBattle; F.pendingBattle = null;
      FX.battleWipe = -1;
      Scene.push(makeBattleScene(z));
      return;
    }
    if (F.busy) return;

    // メニュー
    if (Input.p("cancel") && !F.moving) { Scene.push(makeMenuScene()); return; }

    if (F.moving) {
      F.mvT += SPEED / RT;
      const t = Math.min(1, F.mvT);
      F.px = F.mvFrom.x + (F.mvTo.x - F.mvFrom.x) * t;
      F.py = F.mvFrom.y + (F.mvTo.y - F.mvFrom.y) * t;
      if (t >= 1) {
        F.moving = false;
        F.px = F.mvTo.x; F.py = F.mvTo.y;
        F.tx = Math.round(F.px / RT); F.ty = Math.round(F.py / RT);
        G.pos = { map: F.mapId, x: F.tx, y: F.ty, dir: F.dir };
        onLand();
      }
      F.animT++;
    } else {
      // 新規移動
      let dx = 0, dy = 0, dir = null;
      if (Input.held.has("up")) { dy = -1; dir = "up"; }
      else if (Input.held.has("down")) { dy = 1; dir = "down"; }
      else if (Input.held.has("left")) { dx = -1; dir = "left"; }
      else if (Input.held.has("right")) { dx = 1; dir = "right"; }
      if (dir) { F.dir = dir; tryMove(dx, dy, dir); }
      if (Input.p("ok")) interact();
      F.animT = 0;
    }

    // NPCうろうろ
    for (const n of F.npcs) {
      if (n.hopping > 0) n.hopping--;
      if (!n.wander) continue;
      if (n.mv) { // NPCも滑らか移動
        n.mvT += SPEED / RT / 1.6;
        const t = Math.min(1, n.mvT);
        n.sx = n.mvF.x + (n.mvT2.x - n.mvF.x) * t;
        n.sy = n.mvF.y + (n.mvT2.y - n.mvF.y) * t;
        if (t >= 1) { n.mv = false; n.x = n.mvT2.x / RT; n.y = n.mvT2.y / RT; }
        continue;
      }
      n.wt--;
      if (n.wt <= 0) {
        n.wt = 90 + ((Math.random() * 120) | 0);
        const d = Object.values(DIRS)[(Math.random() * 4) | 0];
        const nx = n.x + d[0], ny = n.y + d[1];
        const p = TILE_PROPS[tileAt(nx, ny)];
        if (p && !p.block && !npcAt(nx, ny) && !chestAt(nx, ny) &&
            !(nx === F.tx && ny === F.ty) && Math.abs(nx - n.homeX || 0) < 999) {
          n.mv = true; n.mvF = { x: n.x * RT, y: n.y * RT }; n.mvT2 = { x: nx * RT, y: ny * RT }; n.mvT = 0;
          n.sx = n.mvF.x; n.sy = n.mvF.y;
        }
      }
    }

    if (F.toastT > 0) F.toastT--;

    // カメラ
    const mw = F.map.tiles[0].length * RT, mh = F.map.tiles.length * RT;
    F.camX = clamp(F.px - VW / 2 + RT / 2, 0, Math.max(0, mw - VW));
    F.camY = clamp(F.py - VH / 2 + RT / 2, 0, Math.max(0, mh - VH));
    if (mw < VW) F.camX = (mw - VW) / 2;
    if (mh < VH) F.camY = (mh - VH) / 2;
  };

  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

  /* ---- 描画 ---- */
  F.draw = function (ctx) {
    const map = F.map;
    const shX = FX.shakeT > 0 ? (Math.random() - 0.5) * FX.shakeAmt : 0;
    const shY = FX.shakeT > 0 ? (Math.random() - 0.5) * FX.shakeAmt : 0;
    const ox = -F.camX + shX, oy = -F.camY + shY;

    // タイル
    const fr = (G.tick >> 4) & 1;
    const x0 = Math.max(0, (F.camX / RT) | 0 - 1) | 0;
    const y0 = Math.max(0, ((F.camY / RT) | 0) - 1);
    const x1 = Math.min(map.tiles[0].length - 1, x0 + VTW + 2);
    const y1 = Math.min(map.tiles.length - 1, y0 + VTH + 2);
    for (let y = y0; y <= y1; y++) {
      for (let x = x0; x <= x1; x++) {
        const ch = map.tiles[y][x];
        const v = hash2(x, y) % tileVariants(ch);
        const cv = tileCanvas(map.tileset, ch, v, fr, G.flags.castleGate);
        ctx.drawImage(cv, ox + x * RT, oy + y * RT, RT, RT);
      }
    }

    // エンティティ(yソート)
    const ents = [];
    for (const c of F.chests) ents.push({ y: c.y, kind: "c", e: c });
    for (const n of F.npcs) ents.push({ y: n.y, kind: "n", e: n });
    ents.push({ y: F.ty, kind: "p" });
    ents.sort((a, b) => a.y - b.y);

    for (const e of ents) {
      if (e.kind === "c") {
        ctx.drawImage(chestCanvas(!!G.flags["chest_" + e.e.id]), ox + e.e.x * RT, oy + e.e.y * RT, RT, RT);
      } else if (e.kind === "n") {
        const n = e.e;
        const spr = SPR[n.spr];
        const nx = n.mv ? n.sx : n.x * RT;
        const ny = (n.mv ? n.sy : n.y * RT) + (n.hopping > 0 ? -Math.abs(Math.sin(n.hopping / 12 * Math.PI)) * 6 : 0);
        if (n.big) {
          ctx.drawImage(sprCanvas(spr), ox + nx - RT, oy + ny - RT, RT * 2, RT * 2);
        } else {
          ctx.drawImage(sprCanvas(spr), ox + nx, oy + ny, RT, RT);
        }
      } else {
        // プレイヤー
        const moving = F.moving;
        const fr2 = moving ? [1, 0, 2, 0][((F.animT >> 3) & 3)] : 0;
        const spr = SPR[`hero_${F.dir}${fr2}`] || SPR.hero_down0;
        ctx.drawImage(sprCanvas(spr), ox + F.px, oy + F.py - 2, RT, RT);
      }
    }

    // マップ名トースト
    if (F.toastT > 0) {
      const a = Math.min(1, F.toastT / 30, (110 - F.toastT) / 20);
      ctx.globalAlpha = a * 0.85;
      ctx.fillStyle = "#10102a";
      const w = ctx.measureText(F.toast).width + 60;
      ctx.fillRect(VW / 2 - w / 2, 14, w, 30);
      ctx.strokeStyle = "#8088c8"; ctx.strokeRect(VW / 2 - w / 2, 14, w, 30);
      ctx.globalAlpha = a;
      txt(ctx, F.toast, VW / 2, 21, { align: "center", color: "#f0e0a0" });
      ctx.globalAlpha = 1;
    }

    // ミニステータス
    drawMiniStatus(ctx);

    // ダンジョン暗闘ヴィネット
    if (F.map.tileset === "cave" || F.map.tileset === "castle") {
      const g = ctx.createRadialGradient(VW / 2, VH / 2, 140, VW / 2, VH / 2, 420);
      g.addColorStop(0, "rgba(0,0,0,0)");
      g.addColorStop(1, "rgba(0,0,10,0.55)");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, VW, VH);
    }
  };

  function drawMiniStatus(ctx) {
    const p = G.player, st = pStats();
    ctx.fillStyle = "rgba(8,10,30,.72)";
    ctx.fillRect(6, 6, 150, 46);
    ctx.strokeStyle = "rgba(160,170,220,.5)";
    ctx.strokeRect(6, 6, 150, 46);
    txt(ctx, `Lv${p.lv}`, 14, 11, { size: 12, color: "#f0c030" });
    // HP
    txt(ctx, "HP", 14, 27, { size: 10, color: "#70e070" });
    ctx.fillStyle = "#203020"; ctx.fillRect(36, 29, 80, 8);
    ctx.fillStyle = p.hp <= st.maxhp * 0.25 ? "#e04040" : "#50c050";
    ctx.fillRect(36, 29, Math.max(0, 80 * p.hp / st.maxhp), 8);
    txt(ctx, `${p.hp}`, 120, 26, { size: 10 });
    // MP
    txt(ctx, "MP", 14, 38, { size: 10, color: "#7090f0" });
    ctx.fillStyle = "#202840"; ctx.fillRect(36, 40, 80, 7);
    ctx.fillStyle = "#5880e0";
    ctx.fillRect(36, 40, Math.max(0, 80 * p.mp / Math.max(1, st.maxmp)), 7);
    txt(ctx, `${p.mp}`, 120, 38, { size: 10 });
  }

  return F;
}

/* ---------------- プレイヤー能力値 ---------------- */
function pStats() {
  const p = G.player || { lv: 1, weapon: null, armor: null };
  const b = baseStats(p.lv);
  const w = GEAR[p.weapon] || { atk: 0 };
  const a = GEAR[p.armor] || { def: 0 };
  return {
    maxhp: b.maxhp, maxmp: b.maxmp,
    atk: b.atk + w.atk, def: b.def + a.def, spd: b.spd,
  };
}

/* ---------------- フィールドメニュー ---------------- */
function makeMenuScene() {
  const M = { isMenu: true, isOverlay: true, panels: [] };
  AU.sfx("ok");

  const root = {
    title: "コマンド",
    items: ["どうぐ", "そうび", "まほう", "ステータス", "セーブ", "ヘルプ", "とじる"],
    sel: 0, x: VW - 200, y: 40, w: 170,
    onPick(i) {
      AU.sfx("ok");
      if (i === 0) openItems();
      else if (i === 1) openEquip();
      else if (i === 2) openSpells();
      else if (i === 3) openStatus();
      else if (i === 4) doSave();
      else if (i === 5) openHelp();
      else Scene.pop();
    },
    onCancel() { Scene.pop(); },
  };
  M.panels.push(root);

  function listPanel(title, items, x, y, w, onPick, onCancel, fmt) {
    const p = { title, items, sel: 0, x, y, w, onPick, onCancel, fmt };
    M.panels.push(p);
    return p;
  }

  function closePanel() { M.panels.pop(); }

  /* -- どうぐ -- */
  function openItems() {
    const ids = Object.keys(G.player.items);
    const items = ids.length ? ids : ["(なにも もっていない)"];
    listPanel("どうぐ", items, VW - 320, 40, 290, (i) => {
      if (!ids.length) return;
      const id = ids[i], it = ITEMS[id];
      if (it.hp || it.full) {
        const st = pStats();
        if (G.player.hp >= st.maxhp) { AU.sfx("cancel"); return; }
        takeItem(id, 1);
        G.player.hp = Math.min(st.maxhp, G.player.hp + (it.full ? st.maxhp : it.hp));
        AU.sfx("heal");
      } else if (it.mp || it.full) {
        const st = pStats();
        takeItem(id, 1);
        if (it.full) { G.player.hp = st.maxhp; G.player.mp = st.maxmp; }
        else G.player.mp = Math.min(st.maxmp, G.player.mp + it.mp);
        AU.sfx("heal");
      } else { AU.sfx("cancel"); return; }
      M.panels.pop(); openItems();
    }, closePanel, (id) => ITEMS[id] ? `${ITEMS[id].name} ×${itemCount(id)}` : id);
  }

  /* -- そうび -- */
  function openEquip() {
    listPanel("そうび", ["ぶき", "よろい"], VW - 320, 40, 290, (i) => {
      const type = i === 0 ? "w" : "a";
      const owned = G.player.bag.filter(g => GEAR[g].type === type);
      const cur = type === "w" ? G.player.weapon : G.player.armor;
      listPanel(type === "w" ? "ぶき" : "よろい", owned, VW - 320, 130, 290, (j) => {
        const gid = owned[j];
        if (gid === cur) { AU.sfx("cancel"); return; }
        if (type === "w") G.player.weapon = gid; else G.player.armor = gid;
        AU.sfx("equip");
        M.panels.pop(); M.panels.pop(); openEquip();
      }, () => { M.panels.pop(); }, (gid) => {
        const g = GEAR[gid];
        const mark = gid === cur ? "E " : "  ";
        return `${mark}${g.name} ${g.atk ? "攻+" + g.atk : "防+" + g.def}`;
      });
    }, closePanel);
  }

  /* -- まほう -- */
  function openSpells() {
    const sp = G.player.spells;
    const items = sp.length ? sp : ["(まだ おぼえていない)"];
    listPanel("まほう", items, VW - 320, 40, 290, (i) => {
      if (!sp.length) return;
      const s = SPELLS[sp[i]];
      if (s.kind !== "heal") { AU.sfx("cancel"); return; }
      const st = pStats();
      if (G.player.mp < s.mp || G.player.hp >= st.maxhp) { AU.sfx("cancel"); return; }
      G.player.mp -= s.mp;
      G.player.hp = Math.min(st.maxhp, G.player.hp + s.pow);
      AU.sfx("heal");
      M.panels.pop(); openSpells();
    }, closePanel, (id) => `${SPELLS[id].name} (MP${SPELLS[id].mp})`);
  }

  /* -- ステータス -- */
  function openStatus() {
    M.panels.push({ type: "status", x: 40, y: 40, w: VW - 420, h: 300, onCancel: closePanel });
  }

  /* -- セーブ -- */
  function doSave() {
    listPanel("セーブ", ["セーブする", "やめる"], VW - 320, 40, 290, (i) => {
      if (i === 0) {
        saveGame();
        AU.sfx("chest");
        Scene.pop(); // メニュー全体を閉じる
        runScript((api) => api.say(["ぼうけんの きろくを ほぞんした！"]));
      } else closePanel();
    }, closePanel);
  }

  /* -- ヘルプ -- */
  function openHelp() {
    M.panels.push({ type: "help", x: 60, y: 60, w: VW - 120, h: 240, onCancel: closePanel });
  }

  /* ---- 入力/更新 ---- */
  M.update = function () {
    const p = M.panels[M.panels.length - 1];
    if (p.type === "status" || p.type === "help") {
      if (Input.p("ok") || Input.p("cancel")) { AU.sfx("cancel"); closePanel(); }
      return;
    }
    if (Input.p("up")) { p.sel = (p.sel + p.items.length - 1) % p.items.length; AU.sfx("cursor"); }
    if (Input.p("down")) { p.sel = (p.sel + 1) % p.items.length; AU.sfx("cursor"); }
    if (Input.p("ok")) p.onPick(p.sel);
    if (Input.p("cancel")) { AU.sfx("cancel"); (p.onCancel || closePanel)(); if (!M.panels.length) Scene.pop(); }
  };

  /* ---- 描画 ---- */
  M.draw = function (ctx) {
    for (const p of M.panels) {
      if (p.type === "status") {
        win(ctx, p.x, p.y, p.w, p.h);
        const pl = G.player, st = pStats();
        txt(ctx, "ゆうしゃ", p.x + 20, p.y + 14, { color: "#f0c030", size: 16 });
        const lines = [
          `レベル: ${pl.lv}`,
          `HP: ${pl.hp} / ${st.maxhp}`,
          `MP: ${pl.mp} / ${st.maxmp}`,
          `こうげき: ${st.atk}   ぼうぎょ: ${st.def}   すばやさ: ${st.spd}`,
          `EXP: ${pl.exp}  (つぎのレベルまで ${Math.max(0, expForLevel(pl.lv + 1) - pl.exp)})`,
          `ゴールド: ${pl.gold}G`,
          ``,
          `ぶき: ${GEAR[pl.weapon].name}`,
          `よろい: ${GEAR[pl.armor].name}`,
          `まほう: ${pl.spells.map(s => SPELLS[s].name).join("・") || "なし"}`,
        ];
        lines.forEach((l, i) => txt(ctx, l, p.x + 20, p.y + 44 + i * 22));
      } else if (p.type === "help") {
        win(ctx, p.x, p.y, p.w, p.h);
        txt(ctx, "あそびかた", p.x + 20, p.y + 14, { color: "#f0c030", size: 16 });
        const lines = [
          "←→↑↓ / WASD: いどう",
          "Z / Enter: しらべる・はなす・けってい",
          "X / Esc: メニューをひらく / キャンセル",
          "M: おんがくON/OFF",
          "",
          "ふかい くさむら・どうくつ・しろでは まものが でる。",
          "たたかいに かつと EXPとゴールドを える。",
          "やどやで やすむと かいふく＆セーブできる。",
          "もくてき: ほしのかけらを とりもどせ！",
        ];
        lines.forEach((l, i) => txt(ctx, l, p.x + 20, p.y + 44 + i * 20, { size: 12 }));
      } else {
        const h = p.items.length * 26 + 42;
        win(ctx, p.x, p.y, p.w, h);
        txt(ctx, p.title, p.x + 14, p.y + 10, { color: "#f0c030" });
        p.items.forEach((it, i) => {
          const label = p.fmt ? p.fmt(it) : it;
          txt(ctx, label, p.x + 26, p.y + 38 + i * 26, { color: "#f0f0f8" });
        });
        cursor(ctx, p.x + 12, p.y + 38 + p.sel * 26 + 3, G.tick);
      }
    }
    // ゴールド表示
    if (M.panels.length) {
      win(ctx, 20, VH - 60, 140, 40);
      txt(ctx, `${G.player.gold} G`, 40, VH - 48, { color: "#f0c030" });
    }
  };

  return M;
}

/* ---------------- ショップ ---------------- */
makeShopScene = function () {
  const S = { isShop: true, isOverlay: true };
  let mode = "root"; // root / buy / sell
  let sel = 0, tab = 0;
  AU.sfx("ok");

  const tabs = ["かう", "うる", "やめる"];
  function stock() { return SHOP_STOCK; }
  function sellables() {
    const l = [];
    for (const id of Object.keys(G.player.items)) l.push({ id, item: true });
    for (const id of G.player.bag) {
      if (id === G.player.weapon || id === G.player.armor) continue;
      l.push({ id, item: false });
    }
    return l;
  }
  function priceOf(id, item) {
    const d = item ? ITEMS[id] : GEAR[id];
    return d.price;
  }
  function nameOf(id, item) { return (item ? ITEMS[id] : GEAR[id]).name; }

  S.update = function () {
    if (mode === "root") {
      if (Input.p("up")) { tab = (tab + tabs.length - 1) % tabs.length; AU.sfx("cursor"); }
      if (Input.p("down")) { tab = (tab + 1) % tabs.length; AU.sfx("cursor"); }
      if (Input.p("cancel")) { AU.sfx("cancel"); Scene.pop(); return; }
      if (Input.p("ok")) {
        AU.sfx("ok");
        if (tab === 0) { mode = "buy"; sel = 0; }
        else if (tab === 1) { mode = "sell"; sel = 0; }
        else Scene.pop();
      }
    } else {
      const list = mode === "buy" ? stock() : sellables();
      if (Input.p("up")) { sel = (sel + list.length - 1) % list.length; AU.sfx("cursor"); }
      if (Input.p("down")) { sel = (sel + 1) % list.length; AU.sfx("cursor"); }
      if (Input.p("cancel")) { AU.sfx("cancel"); mode = "root"; return; }
      if (Input.p("ok") && list.length) {
        if (mode === "buy") {
          const id = list[sel];
          const isItem = !!ITEMS[id];
          const price = priceOf(id, isItem);
          if (G.player.gold < price) { AU.sfx("cancel"); return; }
          G.player.gold -= price;
          if (isItem) addItem(id, 1); else G.player.bag.push(id);
          AU.sfx("coin");
        } else {
          const e = list[sel];
          const d = e.item ? ITEMS[e.id] : GEAR[e.id];
          const price = Math.max(1, (d.price / 2) | 0);
          if (e.item) takeItem(e.id, 1);
          else G.player.bag.splice(G.player.bag.indexOf(e.id), 1);
          G.player.gold += price;
          AU.sfx("coin");
        }
      }
    }
  };

  S.draw = function (ctx) {
    // 商品リスト
    win(ctx, 20, 20, 150, 118);
    tabs.forEach((t, i) => txt(ctx, t, 50, 34 + i * 26, { color: i === tab ? "#f0e040" : "#f0f0f8" }));
    if (mode === "root") cursor(ctx, 32, 35 + tab * 26, G.tick);

    win(ctx, 20, VH - 60, 140, 40);
    txt(ctx, `${G.player.gold} G`, 40, VH - 48, { color: "#f0c030" });

    if (mode !== "root") {
      const list = mode === "buy" ? stock() : sellables();
      const h = Math.min(14, list.length) * 24 + 20;
      win(ctx, 190, 20, VW - 210, Math.max(h, 120));
      if (!list.length) txt(ctx, "(うれるものが ない)", 210, 40);
      list.slice(0, 14).forEach((e, i) => {
        const id = e.id !== undefined ? e.id : e;
        const isItem = mode === "buy" ? !!ITEMS[id] : e.item;
        const d = isItem ? ITEMS[id] : GEAR[id];
        const price = mode === "buy" ? d.price : Math.max(1, (d.price / 2) | 0);
        const cnt = mode === "sell" && e.item ? ` ×${itemCount(id)}` : "";
        txt(ctx, `${d.name}${cnt}`, 216, 34 + i * 24);
        txt(ctx, `${price}G`, VW - 46, 34 + i * 24, { align: "right" });
      });
      cursor(ctx, 198, 36 + sel * 24 + 2, G.tick);
      // 説明
      if (list.length) {
        const e = list[sel];
        const id = e.id !== undefined ? e.id : e;
        const isItem = mode === "buy" ? !!ITEMS[id] : e.item;
        const d = isItem ? ITEMS[id] : GEAR[id];
        win(ctx, 190, VH - 90, VW - 210, 70);
        txt(ctx, d.desc || "", 208, VH - 76, { size: 12 });
        if (!isItem) txt(ctx, d.atk ? `こうげきりょく +${d.atk}` : `ぼうぎょりょく +${d.def}`, 208, VH - 56, { size: 12, color: "#80c8f0" });
      }
    }
  };

  return S;
};

/* ---------------- 宿屋 ---------------- */
innRest = function () {
  const p = G.player;
  if (p.gold < 10) {
    runScript((api) => api.say(["おかねが たりないようだね…"], "やどやの しゅじん"));
    return;
  }
  p.gold -= 10;
  FX.fadeTo(1, 0.05, () => {
    p.hp = pStats().maxhp; p.mp = pStats().maxmp;
    AU.sfx("inn");
    saveGame();
    setTimeout(() => { }, 0);
    FX.fadeTo(0, 0.04);
    runScript((api) => api.say(["ゆっくり やすんだ！", "ぼうけんの きろくも ほぞんされた。"], "やどやの しゅじん"));
  });
};

/* ---------------- セーブ ---------------- */
function saveGame() {
  const p = G.player;
  const data = {
    v: 1,
    player: {
      lv: p.lv, exp: p.exp, gold: p.gold, hp: p.hp, mp: p.mp,
      weapon: p.weapon, armor: p.armor, bag: p.bag, items: p.items,
      spells: p.spells,
    },
    pos: G.pos,
    flags: G.flags,
  };
  try { localStorage.setItem("starquest_save_v1", JSON.stringify(data)); } catch (e) {}
}
function hasSave() {
  try { return !!localStorage.getItem("starquest_save_v1"); } catch (e) { return false; }
}
function loadGame() {
  try {
    const d = JSON.parse(localStorage.getItem("starquest_save_v1"));
    if (!d || d.v !== 1) return null;
    return d;
  } catch (e) { return null; }
}
