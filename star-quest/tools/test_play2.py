#!/usr/bin/env python3
"""Full playthrough verification on headless Chrome (:9223)."""
import sys, time
sys.path.insert(0, "/home/ubuntu/repos/Devin/star-quest/tools")
import cdp as cdpmod
cdpmod.HTTP = "http://localhost:9223"
from cdp import CDP

c = CDP()
time.sleep(1.0)

def shot(n):
    c.shot(f"/tmp/sq2_{n}.png")

def scene():
    return c.js("SQ.scene()")

def key(k, s=0.35):
    c.key(k); time.sleep(s)

print("== 1. title -> new game ==")
key("ok", 1.8)   # はじめから
shot("intro")
print("scene:", scene())
for i in range(12):
    key("ok", 0.5)
    if "dialog" not in (scene() or []): break
print("after intro:", scene())
shot("town_start")

print("== 2. walk around town ==")
c.hold("up", 500); time.sleep(0.2)
c.hold("left", 400); time.sleep(0.2)
shot("walk1")
print("pos:", c.js("JSON.stringify(G.pos)"))

print("== 3. talk to guard NPC ==")
# teleport near guard at town (13,14)-> stand at (13,15) facing up... spawn was (12,15)
c.js("SQ.tp('town',12,13)")
time.sleep(0.5)
c.hold("right", 300); time.sleep(0.2)
key("up", 0.1)
key("ok", 0.6)
shot("talk_guard")
for i in range(6):
    key("ok", 0.5)
    if "dialog" not in (scene() or []): break

print("== 4. menu ==")
key("cancel", 0.6)
shot("menu")
key("down", 0.3); key("ok", 0.6)
shot("menu_items")
key("cancel", 0.3); key("cancel", 0.3); key("cancel", 0.4)

print("== 5. world warp (leave town) ==")
c.js("SQ.tp('town',12,15)")
time.sleep(0.3)
c.hold("down", 700)   # walk to exit row
time.sleep(1.5)
print("pos:", c.js("JSON.stringify(G.pos)"), "scene:", scene())
shot("world")

print("== 6. force battle ==")
c.js("SQ.battle('field')")
time.sleep(2.8)
shot("battle_intro")
# fight several rounds
for r in range(12):
    st = scene() or []
    if "battle" not in st:
        print("battle ended at round", r); break
    key("ok", 0.7); key("ok", 0.7); key("ok", 1.4)
    if r % 3 == 0: shot(f"battle_{r}")
print("scene:", scene(), "hp:", c.js("G.player.hp"), "lv:", c.js("G.player.lv"), "exp:", c.js("G.player.exp"))

print("== 7. flee test (new battle) ==")
c.js("SQ.battle('field')")
time.sleep(2.5)
key("down", 0.3); key("down", 0.3); key("down", 0.3); key("down", 0.3)  # にげる
key("ok", 1.5)
for i in range(4): key("ok", 0.8)
print("after flee attempt:", scene())

print("== 8. shop test ==")
c.js("SQ.tp('town',17,12)")   # in front of shop door tile? door at (17,12)
time.sleep(0.4)
key("up", 0.2); c.hold("up", 350); time.sleep(1.2)
print("pos:", c.js("JSON.stringify(G.pos)"), scene())
shot("shop_interior")
# face shopkeeper across counter: warp puts at (5,6) facing up, counter row y=4, npc (5,3)
c.js("SQ.tp('shop',5,6)")
time.sleep(0.3)
c.hold("up", 400); time.sleep(0.4)  # move to y=5 facing up toward counter
key("up", 0.15)
key("ok", 0.8)
shot("shop_talk")
for i in range(8):
    key("ok", 0.5)
    if "dialog" not in (scene() or []): break
shot("shop_menu")
print("scene:", scene())

print("== 9. inn ==")
key("cancel", 0.3); key("cancel", 0.3)
c.js("SQ.tp('inn',5,6)")
time.sleep(0.4)
c.hold("up", 350); time.sleep(0.3); key("up", 0.15); key("ok", 0.8)
shot("inn_talk")
for i in range(3): key("ok", 0.6)
shot("inn_choice")
key("ok", 1.2)  # やすむ
for i in range(6): key("ok", 0.6)
print("scene:", scene(), "save:", c.js("!!localStorage.getItem('starquest_save_v1')"))

print("== 10. elder quest ==")
key("cancel", 0.3)
c.js("SQ.tp('elder',5,6)")
time.sleep(0.4)
c.hold("up", 700); time.sleep(0.3); key("up",0.15); key("ok", 0.8)
shot("elder")
for i in range(14):
    key("ok", 0.5)
    if "dialog" not in (scene() or []): break
print("flags:", c.js("JSON.stringify(G.flags)"), "gold:", c.js("G.player.gold"), "items:", c.js("JSON.stringify(G.player.items)"))

print("== 11. boss battle ==")
c.js("SQ.lv(12); SQ.learnAll(); SQ.equip('w_steel'); SQ.equip('a_iron')")
c.js("SQ.boss()")
time.sleep(3)
shot("boss_intro")
for r in range(40):
    st = scene() or []
    if not any('battle' == s for s in st): print("battle over at", r); break
    key("ok", 0.6); key("ok", 0.6); key("ok", 1.0)
    if r % 6 == 0: shot(f"boss_{r}")
print("end scene:", scene(), "bossDown:", c.js("G.flags.bossDown"), "hp:", c.js("G.player.hp"))
shot("boss_end")

print("== JS ERRORS ==")
print(c.errors[:10] or "none")
