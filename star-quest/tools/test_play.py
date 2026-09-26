#!/usr/bin/env python3
"""Playthrough test for Star Quest via CDP."""
import sys, time
sys.path.insert(0, "/home/ubuntu/repos/Devin/star-quest/tools")
from cdp import CDP

c = CDP()
c.nav("http://localhost:8321/")
time.sleep(1.2)

def shot(name):
    c.shot(f"/tmp/sq_{name}.png")

def scene():
    return c.js("SQ.scene()")

print("== title ==")
print("scene:", scene())
shot("title")

# new game (menu item 0)
c.key("ok")
time.sleep(2.0)   # fade + dialog
print("after newgame:", scene())
shot("intro")

# advance opening dialog (several Z presses)
for i in range(10):
    c.key("ok"); time.sleep(0.45)
print("after dialog:", scene())
shot("field_town")

# walk around town
c.hold("up", 400); c.hold("left", 300)
c.hold("down", 200); c.hold("right", 250)
shot("field_walk")

# open menu
c.key("cancel"); time.sleep(0.5)
shot("menu")
c.key("cancel"); time.sleep(0.3)

# force a battle via debug hook
c.js("SQ.battle('field')")
time.sleep(2.5)
shot("battle_intro")

# pick attack -> target -> confirm; repeat a few rounds
for r in range(8):
    st = scene()
    if "battle" not in st: break
    for k in ["ok", "ok", "ok"]:
        c.key("ok"); time.sleep(0.6)
    shot(f"battle_r{r}")
    time.sleep(1.2)
print("post-battle scene:", scene())

# check errors so far
print("JS errors:", c.errors[:5] or "none")
