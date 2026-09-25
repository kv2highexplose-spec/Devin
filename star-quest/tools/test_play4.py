#!/usr/bin/env python3
"""Playthrough v4: corrected NPC positions + scene verification."""
import sys, time
sys.path.insert(0, "/home/ubuntu/repos/Devin/star-quest/tools")
import cdp as cdpmod
cdpmod.HTTP = "http://localhost:9223"
from cdp import CDP

c = CDP()
c.send("Page.navigate", url="http://localhost:8321/")
time.sleep(2.5)

def shot(n):
    c.shot(f"/tmp/sq4_{n}.png")

def scene():
    return c.js("SQ.scene()") or []

def adv_dialog(maxp=60):
    for i in range(maxp):
        if "dialog" not in scene():
            return True
        c.key("ok"); time.sleep(0.42)
    return False

def key(k, s=0.4):
    c.key(k); time.sleep(s)

def drive_battle(maxrounds=50, shot_every=0, prefix="f"):
    for r in range(maxrounds):
        if not any(s == "battle" for s in scene()):
            return scene()
        c.key("ok"); time.sleep(0.55)
        c.key("ok"); time.sleep(0.55)
        for _ in range(4):
            if not any(s == "battle" for s in scene()):
                return scene()
            c.key("ok"); time.sleep(0.45)
        if shot_every and r % shot_every == 0:
            shot(f"{prefix}_{r}")
    return scene()

print("== title -> new game ==")
key("ok", 1.8)
print("intro closed:", adv_dialog())
shot("town")
print("pos:", c.js("JSON.stringify(G.pos)"))

print("== walk test ==")
c.hold("up", 600); time.sleep(0.3)
print("pos after up:", c.js("JSON.stringify(G.pos)"))

print("== elder ==")
c.js("SQ.tp('elder',5,3)")
time.sleep(0.5)
key("up", 0.2); key("ok", 0.7)
shot("elder_talk")
adv_dialog()
print("flags:", c.js("JSON.stringify(G.flags)"), "gold:", c.js("G.player.gold"), "items:", c.js("JSON.stringify(G.player.items)"))
shot("elder_done")

print("== shop ==")
c.js("SQ.tp('shop',5,5)")
time.sleep(0.5)
key("up", 0.2); key("ok", 0.7)
shot("shop_talk")
adv_dialog(30)
time.sleep(0.4)
shot("shop_ui")
print("shop scene:", scene())
key("ok", 0.5)   # かう -> buy mode
shot("shop_buy")
key("down", 0.3); key("down", 0.3); key("down", 0.3); key("down", 0.3); key("down", 0.3); key("down", 0.3)  # move to potion
key("ok", 0.6)   # buy item
shot("shop_bought")
print("items:", c.js("JSON.stringify(G.player.items)"), "gold:", c.js("G.player.gold"))
for _ in range(5): key("cancel", 0.35)
print("after shop:", scene(), "bag:", c.js("JSON.stringify(G.player.bag)"), "gold:", c.js("G.player.gold"))

print("== inn ==")
c.js("SQ.tp('inn',5,5)")
time.sleep(0.5)
key("up", 0.2); key("ok", 0.7)
adv_dialog(25)
shot("inn_choice")
key("ok", 1.6)  # やすむ
adv_dialog(30)
time.sleep(1)
print("save:", c.js("!!localStorage.getItem('starquest_save_v1')"), "scene:", scene())
shot("inn_done")

print("== cave chest (hikariKey) ==")
c.js("SQ.tp('cave',9,7)")
time.sleep(0.5)
key("up", 0.2); key("ok", 0.8)
shot("chest")
adv_dialog(30)
print("flags:", c.js("JSON.stringify(G.flags)"))

print("== castle gate ==")
c.js("SQ.tp('world',30,5)")
time.sleep(0.5)
key("up", 0.2)
shot("gate")
adv_dialog(20)
print("castleGate flag:", c.js("G.flags.castleGate"))

print("== random encounter check ==")
# walk on world grass; encounters are random so try a few steps
c.js("SQ.tp('world',20,20)")
time.sleep(0.3)
enc = False
for i in range(30):
    if any(s == "battle" for s in scene()):
        enc = True; break
    c.hold("left", 220); time.sleep(0.15)
    c.hold("right", 220); time.sleep(0.15)
print("natural encounter happened:", enc, "scene:", scene())
if enc:
    shot("encounter")
    drive_battle(40, shot_every=12, prefix="enc")
    print("after enc battle:", scene())

print("== level/spell battle ==")
c.js("SQ.lv(5); SQ.learnAll()")
c.js("SQ.battle('field')")
time.sleep(1.2)
shot("spell_cmd")
key("down", 0.3)  # まほう
key("ok", 0.5)
shot("spell_list")
key("ok", 0.4)   # fire -> target
key("ok", 0.4)
drive_battle(40)
print("after:", scene(), "lv:", c.js("G.player.lv"), "exp:", c.js("G.player.exp"), "hp:", c.js("G.player.hp"), "mp:", c.js("G.player.mp"))

print("== gameover check (suicide) ==")
c.js("G.player.hp = 1")
c.js("SQ.battle('castle')")
time.sleep(1.5)
for r in range(30):
    st = scene()
    if not any(s == "battle" for s in st):
        break
    key("down", 0.15); key("down", 0.15); key("down", 0.15); key("down", 0.15)
    key("ok", 0.6)  # にげる -> wait for hits
    for _ in range(4):
        if not any(s == "battle" for s in scene()): break
        c.key("ok"); time.sleep(0.4)
print("after death:", scene(), "pos:", c.js("JSON.stringify(G.pos)"))
adv_dialog(15)
time.sleep(1)
shot("after_death")
print("scene:", scene(), "hp:", c.js("G.player.hp"), "pos:", c.js("JSON.stringify(G.pos)"))

print("== boss + ending ==")
c.js("SQ.lv(14); SQ.learnAll(); SQ.equip('w_steel'); SQ.equip('a_iron'); G.player.hp=pStats().maxhp")
c.js("SQ.boss()")
time.sleep(2)
shot("boss_fight")
for r in range(60):
    if not any(s == "battle" for s in scene()):
        break
    c.key("ok"); time.sleep(0.5); c.key("ok"); time.sleep(0.5)
    for _ in range(4):
        if not any(s == "battle" for s in scene()): break
        c.key("ok"); time.sleep(0.45)
    if r % 10 == 0: shot(f"boss_{r}")
print("post-boss:", scene(), "bossDown:", c.js("G.flags.bossDown"))
for _ in range(8): key("ok", 0.6)
shot("ending1")
time.sleep(4)
shot("ending2")
# ending skip
for i in range(3):
    key("ok", 1.5)
    st = scene()
    if "scene" in st and "battle" not in st:
        break
time.sleep(2)
shot("back_title")
print("final:", scene(), "hp:", c.js("G.player.hp"))

print("== continue (save) ==")
key("down", 0.3)  # つづきから
key("ok", 2.0)
print("continued:", scene(), "pos:", c.js("JSON.stringify(G.pos)"), "lv:", c.js("G.player.lv"))

print("== ERRORS ==")
print(c.errors[:12] or "none")
