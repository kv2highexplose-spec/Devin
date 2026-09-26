---
name: testing-star-quest
description: How to run and end-to-end test the star-quest browser RPG (serve dir, drive via CDP, SQ debug API, input pitfalls)
---

# Testing Star Quest (star-quest/)

Static HTML5-canvas JRPG, no build step. Serve with `cd star-quest && python3 -m http.server 8321`, open http://localhost:8321/. file:// works too.

## Driving the game

- `tools/cdp.py` is a minimal CDP driver (needs `python3-websockets`). Point `cdpmod.HTTP` at a Chrome with `--remote-debugging-port`. The visible Devin Chrome runs at `:29229`; a disposable headless one: `chrome --headless=new --remote-debugging-port=9223 --user-data-dir=/tmp/chrome_sq`.
- Driving the **visible** browser lets screen recording capture real gameplay; `Input.dispatchKeyEvent` works regardless of OS focus.
- Keys: arrows/WASD move, Z/Enter/Space = ok, X/Esc = cancel/menu, M = mute. `cdp.key()` only knows a few aliases; for M (or any unmapped key) dispatch manually with `code="KeyM"` — the game reads `e.code`, not `e.key`.

## Debug API (window.SQ)

`SQ.tp(map,x,y)` teleport, `SQ.battle(zone)`, `SQ.boss()`, `SQ.lv(n)`, `SQ.gold(n)`, `SQ.item(id[,n])`, `SQ.gear(id)`, `SQ.equip(id)`, `SQ.learnAll()`, `SQ.save()`, `SQ.newGame()`, `SQ.scene()` (stack names), `SQ.G`, `SQ.Scene`. Maps: world, town, elder, inn, shop, cave, castle, castle2, bossroom. Save key: `localStorage.starquest_save_v1`. Battle internals reachable via `SQ.Scene.top()` (`phase`, `cmdSel`, `selSpell`, `selItem`, `pendingCmd`, `enemies`, `msg`).

## Pitfalls learned

- **Menu cursors persist**: battle `cmdSel`/`selSpell`/`selItem` are NOT reset between rounds or sub-menus — scripted input must set them explicitly (`SQ.Scene.top().cmdSel = n`) or read them first, else "down,ok" lands on the wrong command.
- **Dialog `adv` loops eat choices**: an "advance until no dialog" loop will auto-answer `choice` steps (e.g. inn rest) — an extra ok afterwards reopens the NPC dialog. Check scene between presses.
- **Ending auto-advances**: ending phase 0→1 after ~200 frames; a stray ok at the resulting title screen instantly starts a new game.
- **Force-killing enemies while `phase==='spell'`/`'cmd'` leaves a zombie battle** — win detection only runs in `phase==='run'`. Clean up with `while (SQ.Scene.top().isBattle) SQ.Scene.pop()`.
- **Natural encounters**: cave/castle maps have `zone` at map level (every landing rolls, encRate ~0.11) — most reliable place to trigger a random battle; world only rolls on `,`/`;` grass tiles.
- Fonts: `fonts-noto-cjk` must be installed or all Japanese text renders as tofu boxes.

## Verified-playthrough reference

`/tmp/sq_drive.py` style phased driver + `tools/test_play4.py` in-repo. Full loop: title → town → elder(elder 5,3 talk up) → shop(5,5 counter) → inn(5,5) → gate locked check world(30,5) → cave chest(9,7) → gate unlock → castle → encounters → gameover revive → bossroom(5,7→5,5 trigger) → ending → title → つづきから.
