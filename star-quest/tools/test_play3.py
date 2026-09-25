#!/usr/bin/env python3
"""Careful playthrough v3: robust dialog advancing."""
import sys, time
sys.path.insert(0, "/home/ubuntu/repos/Devin/star-quest/tools")
import cdp as cdpmod
cdpmod.HTTP = "http://localhost:9223"
from cdp import CDP

c = CDP()
c.send("Page.navigate", url="http://localhost:8321/")
time.sleep(2)

def shot(n):
    c.shot(f"/tmp/sq3_{n}.png")

def scene():
    return c.js("SQ.scene()") or []

def adv_dialog(maxp=50):
    for i in range(maxp):
        if "dialog" not in scene():
            return True
        c.key("ok"); time.sleep(0.42)
    return "dialog" not in scene()

def key(k, s=0.4):
    c.key(k); time.sleep(s)

def fight(maxrounds=60, shot_every=0, prefix="f"):
    for r in range(maxrounds):
        st = scene()
        if not any(s == "battle" for s in st):
            return st
        c.key("ok"); time.sleep(0.55)
        c.key("ok"); time.sleep(0.55)
        for _ in range(3):
            st = scene()
            if not any(s == "battle" for s in st):
                return st
            c.key("ok"); time.sleep(0.5)
        if shot_every and r % shot_every == 0:
            shot(f"{prefix}_{r}")
    return scene()

print("== new game ==")
key("ok", 1.8)
print("dialog done:", adv_dialog(60))
shot("town")

print("== elder: enter house ==")
c.js("SQ.tp('elder',5,6)")
time.sleep(0.4)
c.hold("up", 600); time.sleep(0.3)
key("ok", 0.5)
shot("elder_talk")
adv_dialog(60)
print("flags:", c.js("JSON.stringify(G.flags)"))
print("gold:", c.js("G.player.gold"), "items:", c.js("JSON.stringify(G.player.items)"))
shot("elder_done")

print("== shop ==")
c.js("SQ.tp('shop',5,5)")
time.sleep(0.4)
c.hold("up", 200); time.sleep(0.2)
key("ok", 0.7)
shot("shop_talk")
adv_dialog(30)
print("scene after shop talk:", scene())
shot("shop_ui")
key("ok", 0.4)   # かう
shot("shop_buy")
key("ok", 0.5)   # buy first item
shot("shop_bought")
for _ in range(4): key("cancel", 0.35)
print("after shop:", scene(), "bag:", c.js("JSON.stringify(G.player.bag)"), "gold:", c.js("G.player.gold"))

print("== inn ==")
c.js("SQ.tp('inn',5,5)")
time.sleep(0.4)
key("ok", 0.7)
adv_dialog(20)
shot("inn_choice")
key("ok", 1.5)  # やすむ
adv_dialog(30)
print("save exists:", c.js("!!localStorage.getItem('starquest_save_v1')"))
shot("inn_done")

print("== chest in cave ==")
c.js("SQ.tp('cave',9,7)")
time.sleep(0.4)
key("up", 0.15); key("ok", 0.8)
shot("chest")
adv_dialog(30)
print("hikariKey:", c.js("G.flags.hikariKey"), "flags:", c.js("JSON.stringify(G.flags)"))

print("== field battle -> victory+level ==")
c.js("SQ.lv(3)")
c.js("SQ.battle('field')")
time.sleep(1.5)
fight(30, shot_every=10, prefix="fb")
print("after:", scene(), "lv:", c.js("G.player.lv"), "exp:", c.js("G.player.exp"), "hp:", c.js("G.player.hp"))

print("== boss ==")
c.js("SQ.lv(14); SQ.learnAll(); SQ.equip('w_steel'); SQ.equip('a_iron')")
c.js("SQ.boss()")
time.sleep(1.5)
for r in range(60):
    st = scene()
    if not any(s == "battle" for s in st):
        print("boss done at", r); break
    c.key("ok"); time.sleep(0.5); c.key("ok"); time.sleep(0.5)
    for _ in range(4):
        if not any(s == "battle" for s in scene()): break
        c.key("ok"); time.sleep(0.45)
    if r % 8 == 0: shot(f"boss_{r}")
print("post-boss:", scene(), "bossDown:", c.js("G.flags.bossDown"))
adv_dialog(20)
shot("ending_or_title")
time.sleep(2)
shot("ending2")
print("final:", scene())

print("== ERRORS ==")
print(c.errors[:10] or "none")
