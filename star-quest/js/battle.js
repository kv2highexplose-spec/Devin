/* ============================================================
   スタークエスト - battle.js
   ターン制バトル
   ============================================================ */

"use strict";

function spawnGroup(zone) {
  const tbl = ZONES[zone];
  let r = Math.random() * 100;
  for (const row of tbl) {
    r -= row[0];
    if (r <= 0) return row.slice(1);
  }
  return tbl[0].slice(1);
}

function makeBattleScene(zone) {
  const isBoss = zone === "boss";
  const ids = isBoss ? ["boss"] : spawnGroup(zone);

  const nameCount = {}, nameTotal = {};
  ids.forEach(id => nameTotal[id] = (nameTotal[id] || 0) + 1);
  const enemies = ids.map((id, i) => {
    const d = ENEMIES[id];
    nameCount[id] = (nameCount[id] || 0) + 1;
    const suffix = nameTotal[id] > 1 ? String.fromCharCode(65 + nameCount[id] - 1) : "";
    return {
      id, def: d, name: d.name + suffix,
      hp: d.hp, maxhp: d.hp, mp: d.mp || 0,
      alive: true, x: 0, y: 0,
      flash: 0, lunge: 0, dieT: 0, charge: false, healedOnce: false,
      idx: i,
    };
  });

  const slots = [[320], [215, 425], [150, 320, 490]];
  const xs = isBoss ? [320] : slots[Math.min(3, enemies.length) - 1];
  enemies.forEach((e, i) => {
    e.x = xs[i];
    e.y = isBoss ? 165 : 180;
  });

  const B = {
    isBattle: true, opaque: true,
    enemies, isBoss, zone,
    phase: "intro", t: 0,
    msg: "", msgT: 0,
    cmdSel: 0,
    cmds: ["こうげき", "まほう", "どうぐ", "ぼうぎょ", "にげる"],
    order: [], oi: 0,
    queue: [],
    heroDef: false, heroLunge: 0, heroFlash: 0,
    popups: [], parts: [],
    selTarget: 0, selSpell: 0, selItem: 0,
    pendingCmd: null,
    fleeing: false, endFired: false,
  };

  AU.stopBgm();
  AU.bgm(isBoss ? "boss" : "battle");

  /* ---------------- ダメージ ---------------- */
  function physDmg(atk, def, mult) {
    const base = Math.max(1, atk - def * 0.5);
    return Math.max(1, Math.round(base * (0.85 + Math.random() * 0.3) * (mult || 1)));
  }
  function magDmg(pow) {
    return Math.max(1, Math.round(pow * (0.9 + Math.random() * 0.4)));
  }

  function say(m, wait) { B.queue.push({ type: "msg", m, wait: wait || 50 }); }
  function firstAlive(i) {
    if (i != null && enemies[i] && enemies[i].alive) return enemies[i];
    return enemies.find(e => e.alive) || null;
  }
  function firstAliveIdx() { return enemies.findIndex(e => e.alive); }

  /* ---------------- 敵AI ---------------- */
  function enemyAction(e) {
    const id = e.id;
    if (id === "boss") {
      if (!e.healedOnce && e.hp < e.maxhp * 0.35) {
        e.healedOnce = true;
        return { kind: "heal", amt: 70, msg: "魔王は やみのちからで きずを いやした！" };
      }
      const r = Math.random();
      if (r < 0.5) return { kind: "attack", mult: 1.0, msg: "魔王の こうげき！" };
      if (r < 0.75) return { kind: "attack", mult: 1.45, fx: "fire", msg: "魔王は まっこくの ほのおを はいた！" };
      if (r < 0.9) return { kind: "attack", mult: 1.7, fx: "dark", msg: "魔王は あんこくの はどうを はなった！" };
      return { kind: "charge", msg: "魔王は すさまじい いきおいを ためている…" };
    }
    if (id === "mage" && e.mp >= 5 && Math.random() < 0.55)
      return { kind: "spell", spell: "fire", msg: `${e.name}は ファイアを となえた！` };
    if (id === "wolf" && Math.random() < 0.3)
      return { kind: "attack", mult: 1.3, msg: `${e.name}は はげしく かみついた！` };
    if (id === "darkknight" && Math.random() < 0.22)
      return { kind: "charge", msg: `${e.name}は ちからを ためている…` };
    if (id === "gargoyle" && Math.random() < 0.2)
      return { kind: "attack", mult: 1.25, fx: "bolt", msg: `${e.name}は いなずまを はいた！` };
    return { kind: "attack", mult: 1.0, msg: `${e.name}の こうげき！` };
  }

  /* ---------------- 行動処理 ---------------- */
  function processUnit(u) {
    const P = G.player, st = pStats();
    if (u.hero) {
      const c = B.pendingCmd;
      if (!c) return;
      if (c.type === "attack") {
        const tgt = firstAlive(c.target);
        if (!tgt) return;
        B.heroLunge = 14;
        const crit = Math.random() < 0.08;
        const dmg = physDmg(st.atk, tgt.def.def, crit ? 1.7 : 1);
        say(`${crit ? "かいしんの いちげき！ " : ""}${tgt.name}に ${dmg}の ダメージ！`);
        B.queue.push({ type: "hitE", tgt, dmg, kind: "slash" });
      } else if (c.type === "spell") {
        const s = SPELLS[c.spell];
        P.mp -= s.mp;
        if (s.kind === "heal") {
          const healed = Math.min(s.pow, st.maxhp - P.hp);
          P.hp += healed;
          B.heroFlash = 18;
          spawnParts(108, 315, "#60e080", 14);
          AU.sfx("heal");
          say(`ゆうしゃは ${s.name}を となえた！ HPが ${healed} かいふくした！`);
        } else if (s.all) {
          AU.sfx(s.fx);
          FX.flash(0.5, "#f0f0ff");
          say(`ゆうしゃは ${s.name}を となえた！`);
          enemies.filter(e => e.alive).forEach(tgt => {
            spawnParts(tgt.x, tgt.y - 20, "#a0c0f0", 10);
            B.queue.push({ type: "hitE", tgt, dmg: magDmg(s.pow), kind: "bolt" });
          });
        } else {
          const tgt = firstAlive(c.target);
          if (!tgt) return;
          AU.sfx(s.fx);
          spawnParts(tgt.x, tgt.y - 20, "#f08030", 16);
          say(`ゆうしゃは ${s.name}を となえた！`);
          B.queue.push({ type: "hitE", tgt, dmg: magDmg(s.pow), kind: "fire" });
        }
      } else if (c.type === "item") {
        const it = ITEMS[c.item];
        takeItem(c.item, 1);
        if (it.smoke) {
          if (B.isBoss) say("けむりだま！ …しかし やみのちからに けされてしまった！");
          else { say("けむりだま！ ゆうしゃは けむりに まぎれて にげだした！"); B.fleeing = true; }
        } else {
          if (it.full) { P.hp = st.maxhp; P.mp = st.maxmp; }
          else if (it.hp) P.hp = Math.min(st.maxhp, P.hp + it.hp);
          else if (it.mp) P.mp = Math.min(st.maxmp, P.mp + it.mp);
          B.heroFlash = 14;
          AU.sfx("heal");
          say(`${it.name}を つかった！`);
        }
      } else if (c.type === "defend") {
        B.heroDef = true;
        say("ゆうしゃは みをまもっている！");
      } else if (c.type === "flee") {
        if (B.isBoss) say("にげられない！！");
        else if (Math.random() < 0.55 + st.spd * 0.01) { say("うまく にげきった！"); B.fleeing = true; }
        else say("しかし まわりこまれてしまった！");
      }
      B.pendingCmd = null;
    } else {
      const e = u;
      if (!e.alive || G.player.hp <= 0) return;
      const act = enemyAction(e);
      if (act.kind === "attack") {
        e.lunge = 14;
        const mult = (act.mult || 1) * (e.charge ? 1.6 : 1);
        e.charge = false;
        let dmg = physDmg(e.def.atk, st.def, mult);
        if (B.heroDef) dmg = Math.max(1, Math.round(dmg * 0.45));
        say(act.msg);
        B.queue.push({ type: "hitP", dmg });
      } else if (act.kind === "spell") {
        e.mp -= SPELLS[act.spell].mp;
        e.lunge = 14;
        let dmg = magDmg(SPELLS[act.spell].pow);
        if (B.heroDef) dmg = Math.max(1, Math.round(dmg * 0.45));
        say(act.msg);
        spawnParts(108, 315, "#f08030", 14);
        AU.sfx("fire");
        B.queue.push({ type: "hitP", dmg });
      } else if (act.kind === "charge") {
        e.charge = true;
        say(act.msg);
      } else if (act.kind === "heal") {
        e.hp = Math.min(e.maxhp, e.hp + act.amt);
        spawnParts(e.x, e.y - 30, "#9060e0", 16);
        AU.sfx("heal");
        say(act.msg);
      }
    }
  }

  function applyHitE(q) {
    const t = q.tgt;
    if (!t.alive) return;
    t.hp -= q.dmg;
    t.flash = 12;
    FX.shake(6, 4);
    AU.sfx(q.kind === "bolt" ? "bolt" : q.kind === "fire" ? "fire" : "hit");
    spawnPopup(t.x, t.y - 40, q.dmg + "", "#f0e040");
    if (t.hp <= 0) {
      t.hp = 0; t.alive = false; t.dieT = 20;
      say(`${t.name}を たおした！`, 44);
    }
  }
  function applyHitP(q) {
    G.player.hp -= q.dmg;
    B.heroFlash = 14;
    FX.shake(8, 5);
    AU.sfx("hurt");
    spawnPopup(108, 270, q.dmg + "", "#f06060");
  }

  function spawnPopup(x, y, s, col) { B.popups.push({ x, y, s, col, t: 42 }); }
  function spawnParts(x, y, col, n) {
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI * 2, v = 1 + Math.random() * 2.5;
      B.parts.push({ x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 1, life: 24 + Math.random() * 20, col });
    }
  }

  /* ---------------- 勝利処理 ---------------- */
  function winSequence() {
    const expG = enemies.reduce((s, e) => s + e.def.exp, 0);
    const goldG = enemies.reduce((s, e) => s + e.def.gold, 0);
    say("たたかいに かった！", 56);
    if (!isBoss) say(`${expG}の EXPと ${goldG}Gを かくとく！`, 56);
    B.queue.push({ type: "fn", f: () => doLevelUps(expG, goldG) });
    B.queue.push({ type: "end" });
  }

  function doLevelUps(expG, goldG) {
    const p = G.player;
    p.exp += expG; p.gold += goldG;
    while (p.exp >= expForLevel(p.lv + 1)) {
      p.lv++;
      const st = pStats();
      p.hp = st.maxhp; p.mp = st.maxmp;
      AU.sfx("levelup");
      say(`レベルが ${p.lv}に あがった！`, 64);
      for (const sid in SPELLS) {
        const s = SPELLS[sid];
        if (s.learn === p.lv && !p.spells.includes(sid)) {
          p.spells.push(sid);
          say(`まほう「${s.name}」を おぼえた！`, 64);
        }
      }
    }
  }

  function endBattle() {
    if (B.endFired) return;
    B.endFired = true;
    if (isBoss) {
      G.flags.bossDown = true;
      AU.stopBgm();
      Scene.clear();
      Scene.push(makeEndingScene());
      return;
    }
    Scene.pop();
    FX.fade = 1; FX.fadeTo(0, 0.08);
    const f = Scene.top();
    if (f && f.isField) AU.bgm(f.bgmName || "field");
  }

  function finishWin() { AU.sfx("victory"); endBattle(); }

  /* ---------------- キュー消化 ---------------- */
  function pumpQueue() {
    if (B.msgT > 0) {
      B.msgT--;
      if (Input.p("ok")) B.msgT = 0;
      return "wait";
    }
    if (!B.queue.length) return "empty";
    const q = B.queue.shift();
    if (q.type === "msg") { B.msg = q.m; B.msgT = q.wait; }
    else if (q.type === "hitE") applyHitE(q);
    else if (q.type === "hitP") applyHitP(q);
    else if (q.type === "fn") q.f();
    else if (q.type === "end") { return "end"; }
    return "ok";
  }

  function aliveEnemies() { return enemies.filter(e => e.alive); }

  /* ---------------- 更新 ---------------- */
  B.update = function () {
    B.t++;
    B.parts = B.parts.filter(p => (p.life-- > 0));
    for (const p of B.parts) { p.x += p.vx; p.y += p.vy; p.vy += 0.06; }
    B.popups = B.popups.filter(p => (p.t-- > 0));
    for (const p of B.popups) p.y -= 0.8;
    for (const e of B.enemies) {
      if (e.flash > 0) e.flash--;
      if (e.lunge > 0) e.lunge--;
      if (e.dieT > 0) e.dieT--;
    }
    if (B.heroLunge > 0) B.heroLunge--;
    if (B.heroFlash > 0) B.heroFlash--;

    switch (B.phase) {
      case "intro":
        if (B.t === 30) {
          const names = {};
          enemies.forEach(e => names[e.def.name] = (names[e.def.name] || 0) + 1);
          const parts = Object.keys(names).map(n => `${n}${names[n] > 1 ? "×" + names[n] : ""}`);
          B.msg = isBoss ? "魔王ヴァルドラスが おおきな かげから あらわれた！！" : `${parts.join("・")} が あらわれた！`;
        }
        if (B.t > 120 || (B.t > 40 && Input.p("ok"))) {
          B.phase = "cmd"; B.msg = "ゆうしゃは どうする？";
        }
        return;

      case "cmd": case "target": case "spell": case "item":
        cmdHandlers[B.phase]();
        return;

      case "run": {
        const r = pumpQueue();
        if (r === "wait") return;
        if (r === "end") { /* 勝利キューはwinフェーズで来ない */ }
        if (!aliveEnemies().length) { B.phase = "win"; winSequence(); return; }
        if (G.player.hp <= 0) { G.player.hp = 0; B.queue = []; B.msg = "ゆうしゃは ちからつきた…"; B.msgT = 90; B.phase = "lose"; return; }
        if (B.fleeing && !B.queue.length) { B.phase = "flee"; return; }
        if (r === "empty" || r === "ok") {
          if (B.fleeing) { B.phase = "flee"; return; }
          if (B.oi < B.order.length) {
            const u = B.order[B.oi++];
            processUnit(u);
          } else {
            B.heroDef = false;
            B.phase = "cmd";
            B.msg = "ゆうしゃは どうする？";
          }
        }
        return;
      }

      case "win": {
        const r = pumpQueue();
        if (r === "end") finishWin();
        else if (r === "empty") B.queue.push({ type: "end" });
        return;
      }

      case "lose":
        if (B.msgT > 0) {
          B.msgT--;
          if (B.msgT === 0) {
            FX.fadeTo(1, 0.03, () => {
              Scene.clear();
              Scene.push(makeGameOverScene());
              FX.fadeTo(0, 0.05);
            });
          }
        }
        return;

      case "flee":
        endBattle();
        return;
    }
  };

  /* ---------------- コマンド入力 ---------------- */
  const cmdHandlers = {
    cmd() {
      if (Input.p("up")) { B.cmdSel = (B.cmdSel + 4) % 5; AU.sfx("cursor"); }
      if (Input.p("down")) { B.cmdSel = (B.cmdSel + 1) % 5; AU.sfx("cursor"); }
      if (Input.p("ok")) {
        const c = B.cmdSel;
        if (c === 0) { B.phase = "target"; B.selTarget = firstAliveIdx(); AU.sfx("ok"); }
        else if (c === 1) {
          if (!G.player.spells.length) { B.msg = "まほうを おぼえていない！"; AU.sfx("cancel"); }
          else { B.phase = "spell"; B.selSpell = 0; AU.sfx("ok"); }
        } else if (c === 2) {
          if (!Object.keys(G.player.items).length) { B.msg = "どうぐを もっていない！"; AU.sfx("cancel"); }
          else { B.phase = "item"; B.selItem = 0; AU.sfx("ok"); }
        } else if (c === 3) { B.pendingCmd = { type: "defend" }; AU.sfx("ok"); startRound(); }
        else if (c === 4) { B.pendingCmd = { type: "flee" }; AU.sfx("ok"); startRound(); }
      }
    },
    target() {
      const alive = enemies.map((e, i) => e.alive ? i : -1).filter(i => i >= 0);
      if (!alive.length) return;
      const cur = Math.max(0, alive.indexOf(B.selTarget));
      if (Input.p("left") || Input.p("up")) { B.selTarget = alive[(cur + alive.length - 1) % alive.length]; AU.sfx("cursor"); }
      if (Input.p("right") || Input.p("down")) { B.selTarget = alive[(cur + 1) % alive.length]; AU.sfx("cursor"); }
      if (Input.p("cancel")) { B.phase = "cmd"; AU.sfx("cancel"); }
      if (Input.p("ok")) { B.pendingCmd = { type: "attack", target: B.selTarget }; AU.sfx("ok"); startRound(); }
    },
    spell() {
      const sp = G.player.spells;
      if (Input.p("up")) { B.selSpell = (B.selSpell + sp.length - 1) % sp.length; AU.sfx("cursor"); }
      if (Input.p("down")) { B.selSpell = (B.selSpell + 1) % sp.length; AU.sfx("cursor"); }
      if (Input.p("cancel")) { B.phase = "cmd"; AU.sfx("cancel"); }
      if (Input.p("ok")) {
        const sid = sp[B.selSpell], s = SPELLS[sid];
        if (G.player.mp < s.mp) { AU.sfx("cancel"); return; }
        if (s.kind === "heal" && G.player.hp >= pStats().maxhp) { AU.sfx("cancel"); return; }
        if (s.kind === "dmg" && !s.all) { B.pendingCmd = { type: "spell", spell: sid }; B.phase = "target"; }
        else { B.pendingCmd = { type: "spell", spell: sid }; startRound(); }
        AU.sfx("ok");
      }
    },
    item() {
      const ids = Object.keys(G.player.items);
      if (Input.p("up")) { B.selItem = (B.selItem + ids.length - 1) % ids.length; AU.sfx("cursor"); }
      if (Input.p("down")) { B.selItem = (B.selItem + 1) % ids.length; AU.sfx("cursor"); }
      if (Input.p("cancel")) { B.phase = "cmd"; AU.sfx("cancel"); }
      if (Input.p("ok")) { B.pendingCmd = { type: "item", item: ids[B.selItem] }; AU.sfx("ok"); startRound(); }
    },
  };

  function startRound() {
    const units = [{ hero: true }].concat(enemies.filter(e => e.alive));
    const spdOf = (u) => u.hero ? pStats().spd + Math.random() * 4 : u.def.spd + Math.random() * 4;
    units.sort((a, b) => spdOf(b) - spdOf(a));
    B.order = units; B.oi = 0;
    B.queue = [];
    B.phase = "run";
  }

  /* ---------------- 描画 ---------------- */
  B.draw = function (ctx) {
    const grad = ctx.createLinearGradient(0, 0, 0, VH);
    if (B.isBoss) { grad.addColorStop(0, "#1a0620"); grad.addColorStop(0.6, "#30103a"); grad.addColorStop(1, "#100418"); }
    else if (["castle", "castle2", "cave"].includes(B.zone)) { grad.addColorStop(0, "#0c0c1c"); grad.addColorStop(0.6, "#202038"); grad.addColorStop(1, "#0a0a14"); }
    else { grad.addColorStop(0, "#0e1a3a"); grad.addColorStop(0.55, "#1a3a6a"); grad.addColorStop(1, "#0c2418"); }
    ctx.fillStyle = grad; ctx.fillRect(0, 0, VW, VH);

    ctx.fillStyle = ["castle", "castle2", "cave"].includes(B.zone) ? "#3a3a50" : "#2e6a3a";
    ctx.beginPath(); ctx.ellipse(VW / 2, 210, VW / 2 + 60, 95, 0, 0, 7); ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,.05)";
    ctx.beginPath(); ctx.ellipse(VW / 2, 210, VW / 2 - 40, 68, 0, 0, 7); ctx.fill();

    for (const e of B.enemies) {
      if (!e.alive && e.dieT <= 0) continue;
      const spr = SPR[e.def.spr];
      const sc = e.def.boss ? 4 : 3;
      const w = spr.w * sc, h = spr.h * sc;
      let dx = e.x - w / 2, dy = e.y - h;
      if (e.lunge > 0) dx -= Math.sin(e.lunge / 14 * Math.PI) * 22;
      let alpha = e.dieT > 0 ? e.dieT / 20 : 1;
      if (B.phase === "intro") {
        const slide = Math.min(1, Math.max(0, (B.t - 10 - e.idx * 9) / 32));
        if (slide <= 0) continue;
        dx += (1 - slide) * 220;
        alpha *= slide;
      }
      ctx.globalAlpha = alpha;
      if (e.flash > 0 && (e.flash % 4 < 2)) ctx.globalAlpha = alpha * 0.35;
      ctx.drawImage(sprCanvas(spr), dx, dy, w, h);
      ctx.globalAlpha = 1;
      if (B.phase === "target" && B.selTarget === e.idx && e.alive) {
        cursor(ctx, e.x - w / 2 - 22, e.y - h / 2 - 6 + Math.sin(B.t / 6) * 2, B.t);
        txt(ctx, e.name, e.x, e.y + 10, { align: "center", color: "#f0e040", size: 13 });
      }
      if (e.alive) {
        const bw = Math.min(80, w);
        ctx.fillStyle = "rgba(0,0,0,.5)";
        ctx.fillRect(e.x - bw / 2, e.y + 6, bw, 5);
        ctx.fillStyle = "#e05050";
        ctx.fillRect(e.x - bw / 2, e.y + 6, Math.max(0, bw * e.hp / e.maxhp), 5);
      }
    }

    for (const p of B.parts) {
      ctx.globalAlpha = Math.min(1, p.life / 18);
      ctx.fillStyle = p.col;
      ctx.fillRect(p.x - 1.5, p.y - 1.5, 3, 3);
    }
    ctx.globalAlpha = 1;

    { // 勇者
      const spr = SPR.hero_right0, sc = 3;
      const dx = 66 + (B.heroLunge > 0 ? Math.sin(B.heroLunge / 14 * Math.PI) * 26 : 0);
      const dy = 285;
      if (B.heroFlash > 0 && (B.heroFlash % 4 < 2)) ctx.globalAlpha = 0.4;
      ctx.drawImage(sprCanvas(spr), dx, dy, spr.w * sc, spr.h * sc);
      ctx.globalAlpha = 1;
      if (B.heroDef) {
        ctx.strokeStyle = "#80c8f0"; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(dx + 24, dy + 24, 34, 0, 7); ctx.stroke();
      }
    }

    for (const p of B.popups) {
      ctx.globalAlpha = Math.min(1, p.t / 15);
      txt(ctx, p.s, p.x, p.y, { align: "center", size: 20, color: p.col });
    }
    ctx.globalAlpha = 1;

    win(ctx, 20, VH - 115, VW - 40, 96);
    txt(ctx, B.msg, 40, VH - 90, { size: 15 });

    if (B.phase === "cmd") {
      const w = 140, h = 5 * 26 + 18;
      win(ctx, VW - w - 30, VH - 115 - h - 10, w, h);
      B.cmds.forEach((c, i) => txt(ctx, c, VW - w - 4, VH - 115 - h + 12 + i * 26));
      cursor(ctx, VW - w - 22, VH - 115 - h + 13 + B.cmdSel * 26, B.t);
      drawStatusPlate(ctx);
    }
    if (B.phase === "target") {
      drawStatusPlate(ctx);
      txt(ctx, "◀ てきを えらぶ ▶", VW - 290, VH - 140, { color: "#f0e040", size: 12 });
    }
    if (B.phase === "spell") {
      const sp = G.player.spells;
      const w = 260, h = sp.length * 26 + 18;
      win(ctx, VW - w - 30, VH - 115 - h - 10, w, h);
      sp.forEach((sid, i) => {
        const s = SPELLS[sid];
        const ok = G.player.mp >= s.mp;
        txt(ctx, s.name, VW - w - 4, VH - 115 - h + 12 + i * 26, { color: ok ? "#f0f0f8" : "#787888" });
        txt(ctx, `MP${s.mp}`, VW - 70, VH - 115 - h + 12 + i * 26, { color: ok ? "#80c8f0" : "#787888" });
      });
      cursor(ctx, VW - w - 22, VH - 115 - h + 13 + B.selSpell * 26, B.t);
      drawStatusPlate(ctx);
    }
    if (B.phase === "item") {
      const ids = Object.keys(G.player.items);
      const w = 260, h = ids.length * 26 + 18;
      win(ctx, VW - w - 30, VH - 115 - h - 10, w, h);
      ids.forEach((id, i) => txt(ctx, `${ITEMS[id].name} ×${G.player.items[id]}`, VW - w - 4, VH - 115 - h + 12 + i * 26));
      cursor(ctx, VW - w - 22, VH - 115 - h + 13 + B.selItem * 26, B.t);
      drawStatusPlate(ctx);
    }
  };

  function drawStatusPlate(ctx) {
    if (!G.player) return;
    const st = pStats();
    win(ctx, 20, 20, 220, 70);
    txt(ctx, `ゆうしゃ  Lv${G.player.lv}`, 36, 27, { color: "#f0c030" });
    txt(ctx, "HP", 36, 46, { size: 11, color: "#70e070" });
    ctx.fillStyle = "#203020"; ctx.fillRect(60, 48, 130, 8);
    ctx.fillStyle = G.player.hp <= st.maxhp * 0.25 ? "#e05050" : "#50c050";
    ctx.fillRect(60, 48, Math.max(0, 130 * G.player.hp / st.maxhp), 8);
    txt(ctx, `${G.player.hp}/${st.maxhp}`, 196, 45, { size: 10 });
    txt(ctx, "MP", 36, 64, { size: 11, color: "#80b8f0" });
    ctx.fillStyle = "#202840"; ctx.fillRect(60, 66, 130, 8);
    ctx.fillStyle = "#5880e0"; ctx.fillRect(60, 66, Math.max(0, 130 * G.player.mp) / Math.max(1, st.maxmp), 8);
    txt(ctx, `${G.player.mp}/${st.maxmp}`, 196, 63, { size: 10 });
  }

  return B;
}

/* ---------------- ボス戦開始 ---------------- */
startBossBattle = function () {
  Scene.push(makeBattleScene("boss"));
};
