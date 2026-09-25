#!/usr/bin/env python3
"""スタークエスト マップジェネレータ
タイルマップを組み立てて js/maps.gen.js に書き出す。
実行: python3 tools/gen_maps.py
生成後に全マップの到達可能性をBFSで検証する。
"""

import json, random
from collections import deque

random.seed(7)

BLOCK = set("#T~HRWPoqujmxVX Gq".replace(" ", "")) - set("G")
# 通行不可タイル(Gはカギで開くので到達扱い)
BLOCKS = set("#T~HhRWPoqujmxVXx")
WALK_OK = set(".,f;psDFSo!nGZBder")  # 歩ける/乗れるタイル

class M:
    def __init__(self, w, h, base="."):
        self.w, self.h = w, h
        self.g = [[base] * w for _ in range(h)]
    def set(self, x, y, ch): self.g[y][x] = ch
    def get(self, x, y): return self.g[y][x]
    def fill(self, x, y, w, h, ch):
        for j in range(y, y + h):
            for i in range(x, x + w):
                self.g[j][i] = ch
    def box(self, x, y, w, h, ch):
        for i in range(x, x + w):
            self.g[y][i] = ch; self.g[y + h - 1][i] = ch
        for j in range(y, y + h):
            self.g[j][x] = ch; self.g[j][x + w - 1] = ch
    def blob(self, cx, cy, rx, ry, ch, prob=1.0):
        for j in range(cy - ry, cy + ry + 1):
            for i in range(cx - rx, cx + rx + 1):
                if 0 <= i < self.w and 0 <= j < self.h:
                    if ((i - cx) / (rx + 0.4)) ** 2 + ((j - cy) / (ry + 0.4)) ** 2 <= 1.0:
                        if self.g[j][i] in ".,f;s" and random.random() < prob:
                            self.g[j][i] = ch
    def hline(self, x0, x1, y, ch):
        for i in range(min(x0, x1), max(x0, x1) + 1):
            self.g[y][i] = ch
    def vline(self, y0, y1, x, ch):
        for j in range(min(y0, y1), max(y0, y1) + 1):
            self.g[j][x] = ch
    def scatter(self, ch, pts):
        for x, y in pts: self.g[y][x] = ch
    def rows(self): return ["".join(r) for r in self.g]


MAPS = {}
def reg(id, name, tileset, m, warps, chests, npcs, enc=0.0, zone=None, triggers=None):
    MAPS[id] = dict(name=name, tileset=tileset, tiles=m.rows(), encRate=enc,
                    zone=zone, warps=warps, chests=chests, npcs=npcs,
                    triggers=triggers or [])

def house(m, x, y, w):
    m.hline(x, x + w - 1, y, "R")
    m.hline(x, x + w - 1, y + 1, "H")
    m.set(x + w // 2, y + 1, "D")

# ============================ WORLD ============================
m = M(40, 30, ".")
m.box(0, 0, 40, 30, "#")

river = [(21, 5), (21, 6), (22, 7), (22, 8), (22, 9), (23, 10), (23, 11),
         (23, 12), (23, 13), (22, 14), (23, 15), (23, 16), (24, 17), (24, 18)]
for x, y in river:
    m.set(x, y, "~"); m.set(x + 1, y, "~")
m.blob(33, 24, 5, 5, "~")
m.blob(35, 28, 3, 2, "~")

m.blob(9, 8, 5, 4, "T", 0.85)
m.blob(13, 3, 3, 2, "T", 0.9)
m.blob(34, 8, 4, 4, "T", 0.75)
m.blob(5, 18, 3, 3, "T", 0.7)
m.scatter("T", [(18, 8), (26, 7), (30, 10), (15, 11), (11, 20), (36, 14), (26, 18), (19, 5)])

m.blob(10, 15, 6, 3, ",", 0.7)
m.blob(6, 21, 3, 2, ",", 0.6)
m.blob(29, 15, 5, 3, ";", 0.7)
m.blob(33, 18, 3, 2, ";", 0.6)
m.blob(31, 5, 1, 0, ";", 0.8)

m.scatter("f", [(4, 23), (11, 23), (15, 21), (19, 20), (12, 13), (20, 24)])
m.blob(15, 15, 3, 2, "s")
m.blob(26, 26, 3, 2, "s")

# 洞窟入口(森の中の空き地)
m.fill(6, 7, 4, 3, ".")
m.scatter("#", [(5, 6), (10, 6), (5, 10), (10, 10)])
m.set(7, 8, "n"); m.set(8, 8, "n")

# 村
m.blob(7, 25, 5, 3, "p", 0.9)
m.set(5, 24, "R"); m.set(6, 24, "R"); m.set(7, 24, "R")
m.set(5, 25, "H"); m.set(6, 25, "H"); m.set(7, 25, "H")
m.set(9, 24, "R"); m.set(10, 24, "R"); m.set(11, 24, "R")
m.set(9, 25, "H"); m.set(10, 25, "H"); m.set(11, 25, "H")
m.set(8, 26, "D")
m.scatter("x", [(3, 23), (3, 24), (3, 25), (3, 26), (12, 26), (12, 25)])
m.set(8, 23, "V")

# メイン道
m.vline(13, 26, 17, "p")
m.hline(6, 17, 27, "p")
m.hline(17, 22, 12, "p")
m.hline(25, 30, 12, "p")
m.vline(5, 12, 30, "p")
m.hline(8, 17, 13, "p")
m.vline(9, 13, 8, "p")

# 橋
m.set(23, 12, "="); m.set(24, 12, "=")

# 魔王城(最後)
m.fill(27, 1, 9, 4, "m")
m.fill(28, 2, 7, 2, "F")
m.set(30, 4, "G")
m.set(30, 5, "p")
m.scatter("#", [(25, 1), (37, 1), (25, 3), (37, 3), (36, 5)])

world_warps = [
    dict(x=8, y=26, to="town", tx=12, ty=15, dir="down"),
    dict(x=7, y=8, to="cave", tx=9, ty=13, dir="up"),
    dict(x=8, y=8, to="cave", tx=10, ty=13, dir="up"),
    dict(x=30, y=4, to="castle", tx=14, ty=19, dir="up", gate="castleGate"),
]
world_chests = [
    dict(x=14, y=15, id="w_c1", gold=120),
    dict(x=16, y=16, id="w_c2", item="hipotion"),
    dict(x=15, y=17, id="w_c3", item="ether"),
    dict(x=26, y=26, id="w_c4", gold=200),
]
reg("world", "ルミナの大地", "field", m, world_warps, world_chests, [], enc=0.085)

# ============================ TOWN ============================
m = M(24, 18, ".")
m.box(0, 0, 24, 18, "T")

m.vline(4, 8, 4, "p")
m.vline(4, 8, 19, "p")
m.hline(4, 19, 8, "p")
m.vline(9, 13, 12, "p")
m.hline(12, 17, 13, "p")
m.vline(14, 15, 13, "p")
m.hline(10, 16, 16, "!")
m.set(17, 13, "p")

house(m, 2, 2, 5)
house(m, 17, 2, 5)
house(m, 15, 11, 4)

m.set(11, 5, "V")
m.scatter("x", [(2, 9), (3, 9), (20, 9), (21, 9), (21, 10)])
m.scatter("f", [(6, 6), (8, 6), (14, 6), (16, 7), (5, 10), (18, 9), (8, 14), (19, 14)])

town_warps = [
    dict(x=4, y=3, to="elder", tx=5, ty=6, dir="up"),
    dict(x=19, y=3, to="inn", tx=5, ty=6, dir="up"),
    dict(x=17, y=12, to="shop", tx=5, ty=6, dir="up"),
] + [dict(x=x, y=16, to="world", tx=8, ty=27, dir="down") for x in range(10, 17)]
town_npcs = [
    dict(x=13, y=14, spr="npc_guard", name="もりのへいし", talk="guard"),
    dict(x=7, y=7, spr="npc_vil1", name="むらびと", talk="vil1", wander=True),
    dict(x=16, y=9, spr="npc_vil2", name="むらびと", talk="vil2", wander=True),
    dict(x=13, y=6, spr="npc_vil2", name="おばあさん", talk="vil3"),
]
reg("town", "ルミナの村", "town", m, town_warps, [], town_npcs)

# ============================ INTERIORS ============================
def interior(counter=True, deco=None):
    m = M(11, 8, "F")
    m.box(0, 0, 11, 8, "H")
    if counter:
        m.hline(2, 8, 4, "q")
    m.fill(4, 5, 3, 2, "r")
    m.hline(4, 6, 7, "!")
    if deco:
        for ch, pts in deco:
            m.scatter(ch, pts)
    return m

reg("inn", "宿屋", "inside",
    interior(deco=[("Q", [(1, 1), (2, 1)]), ("u", [(8, 2)]), ("j", [(9, 1)])]),
    [dict(x=x, y=7, to="town", tx=19, ty=4, dir="down") for x in range(4, 7)],
    [], [dict(x=5, y=3, spr="npc_inn", name="やどやの しゅじん", talk="inn", counter=(4, 5))])

reg("shop", "ぶきぐ屋", "inside",
    interior(deco=[("u", [(1, 2), (9, 2)]), ("j", [(1, 1), (9, 1)])]),
    [dict(x=x, y=7, to="town", tx=17, ty=13, dir="down") for x in range(4, 7)],
    [], [dict(x=5, y=3, spr="npc_shop", name="てんしゅ", talk="shop", counter=(4, 5))])

reg("elder", "ちょうろうの家", "inside",
    interior(counter=False, deco=[("Q", [(9, 2)]), ("u", [(2, 2)]), ("j", [(9, 1)]), ("u", [(8, 5)])]),
    [dict(x=x, y=7, to="town", tx=4, ty=4, dir="down") for x in range(4, 7)],
    [], [dict(x=5, y=2, spr="npc_elder", name="ちょうろう", talk="elder")])

# ============================ CAVE ============================
m = M(20, 16, "#")
m.fill(1, 1, 18, 14, "s")
m.vline(3, 9, 5, "#");   m.set(5, 6, "s")
m.vline(6, 12, 14, "#"); m.set(14, 9, "s")
m.hline(7, 12, 4, "#");  m.set(10, 4, "s")
m.fill(8, 6, 4, 3, "F")
m.set(7, 6, "P"); m.set(12, 6, "P")
m.scatter("o", [(2, 2), (17, 2), (2, 12), (17, 12), (9, 2)])
m.set(9, 14, "!"); m.set(10, 14, "!")

cave_chests = [
    dict(x=9, y=6, id="cv_c1", key="hikariKey"),
    dict(x=10, y=6, id="cv_c2", gold=250),
    dict(x=1, y=1, id="cv_c3", item="elixir"),
    dict(x=18, y=13, id="cv_c4", item="hipotion"),
]
reg("cave", "北の洞窟", "cave", m,
    [dict(x=9, y=14, to="world", tx=7, ty=9, dir="down"),
     dict(x=10, y=14, to="world", tx=7, ty=9, dir="down")],
    cave_chests, [], enc=0.11, zone="cave")

# ============================ CASTLE 1F ============================
m = M(30, 22, "F")
m.box(0, 0, 30, 22, "W")
m.vline(2, 9, 5, "W");   m.set(5, 5, "F")
m.vline(8, 17, 5, "W");  m.set(5, 12, "F")
m.hline(5, 11, 9, "W");  m.set(9, 9, "F")
m.vline(2, 6, 11, "W");  m.set(11, 4, "F")
m.hline(13, 18, 4, "W"); m.set(16, 4, "F")
m.vline(4, 10, 18, "W"); m.set(18, 7, "F")
m.hline(18, 24, 10, "W"); m.set(21, 10, "F")
m.vline(12, 18, 24, "W"); m.set(24, 15, "F")
m.hline(20, 25, 17, "W"); m.set(22, 17, "F")
m.hline(7, 13, 17, "W");  m.set(10, 17, "F")
m.vline(18, 19, 13, "W"); m.set(13, 18, "F")
m.scatter("P", [(3, 3), (26, 3), (3, 18), (27, 18), (15, 6), (7, 15)])
m.scatter("o", [(1, 5), (1, 14), (28, 5), (28, 14), (8, 20), (20, 20)])
m.set(15, 2, "S")
m.hline(13, 16, 20, "!")

castle_chests = [
    dict(x=2, y=2, id="cs_c1", gold=500),
    dict(x=27, y=2, id="cs_c2", item="elixir"),
    dict(x=26, y=14, id="cs_c3", gear="w_light"),
    dict(x=3, y=20, id="cs_c4", item="ether"),
]
reg("castle", "魔王城 いっかい", "castle", m,
    [dict(x=15, y=2, to="castle2", tx=10, ty=13, dir="up")] +
    [dict(x=x, y=20, to="world", tx=30, ty=5, dir="down") for x in range(13, 17)],
    castle_chests, [], enc=0.11, zone="castle")

# ============================ CASTLE 2F ============================
m = M(22, 16, "F")
m.box(0, 0, 22, 16, "W")
m.vline(3, 11, 5, "W");   m.set(5, 7, "F")
m.vline(4, 13, 9, "W");   m.set(9, 10, "F")
m.hline(9, 14, 6, "W");   m.set(11, 6, "F")
m.vline(2, 9, 15, "W");   m.set(15, 5, "F")
m.hline(15, 19, 9, "W");  m.set(17, 9, "F")
m.vline(10, 13, 17, "W")
m.scatter("P", [(3, 3), (18, 3), (3, 12), (18, 13)])
m.scatter("o", [(1, 4), (1, 11), (20, 4), (20, 12), (7, 2), (13, 2)])
m.set(10, 14, "S")
m.set(10, 1, "Z")

castle2_chests = [
    dict(x=19, y=2, id="c2_c1", gear="a_dragon"),
    dict(x=1, y=13, id="c2_c2", item="elixir"),
]
reg("castle2", "魔王城 にかい", "castle", m,
    [dict(x=10, y=14, to="castle", tx=15, ty=3, dir="down"),
     dict(x=10, y=1, to="bossroom", tx=5, ty=7, dir="up")],
    castle2_chests, [], enc=0.12, zone="castle2")

# ============================ BOSS ROOM ============================
m = M(11, 9, "F")
m.box(0, 0, 11, 9, "W")
m.fill(4, 2, 3, 5, "r")
m.scatter("P", [(2, 2), (8, 2), (2, 6), (8, 6)])
m.hline(4, 6, 8, "!")
reg("bossroom", "魔王の間", "castle", m,
    [dict(x=x, y=8, to="castle2", tx=10, ty=2, dir="down") for x in range(4, 7)],
    [], [dict(x=5, y=2, spr="en_boss", name="魔王ヴァルドラス", talk="boss", big=True)],
    triggers=[dict(x=5, y=5, script="bossApproach")])

# ============================ 到達性チェック ============================
def reachable(mapid):
    """マップ内のワープ到着点からBFS。戻り値: 到達可能タイル集合"""
    tiles = MAPS[mapid]["tiles"]
    h, w = len(tiles), len(tiles[0])
    entries = []
    for mid, mm in MAPS.items():
        for wp in mm["warps"]:
            if wp["to"] == mapid:
                entries.append((wp["tx"], wp["ty"]))
    # 入口が無いマップ(world)は全タイルから探索してもいいが、村Dから入るので world→town の戻り点等で網羅される
    seen = set(entries)
    dq = deque(entries)
    npcblock = {(n["x"], n["y"]) for n in MAPS[mapid]["npcs"]}
    chestblock = {(c["x"], c["y"]) for c in MAPS[mapid]["chests"]}
    while dq:
        x, y = dq.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < w and 0 <= ny < h) or (nx, ny) in seen:
                continue
            ch = tiles[ny][nx]
            if ch not in WALK_OK:  # G含む(カギで開く)
                continue
            if (nx, ny) in npcblock or (nx, ny) in chestblock:
                continue
            seen.add((nx, ny))
            dq.append((nx, ny))
    return seen, entries

problems = []
for mid, mm in MAPS.items():
    reach, entries = reachable(mid)
    tiles = mm["tiles"]
    name = mm["name"]
    # ワープ設置タイルが到達可能か(自分のマップ内)
    for i, wp in enumerate(mm["warps"]):
        if (wp["x"], wp["y"]) not in reach and tiles[wp["y"]][wp["x"]] != "G":
            problems.append(f"{mid}: warp{i}({wp['x']},{wp['y']}) '{tiles[wp['y']][wp['x']]}' unreachable")
        if tiles[wp["y"]][wp["x"]] in BLOCKS:
            problems.append(f"{mid}: warp{i} on blocking tile '{tiles[wp['y']][wp['x']]}'")
        # 到着先マップでの座標が通行可能か
        tt = MAPS[wp["to"]]["tiles"][wp["ty"]][wp["tx"]]
        if tt in BLOCKS or tt in "!":
            problems.append(f"{mid}: warp{i} target '{wp['to']}' lands on '{tt}'")
    for i, c in enumerate(mm["chests"]):
        ok = any((c["x"] + dx, c["y"] + dy) in reach for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)))
        if not ok:
            problems.append(f"{mid}: chest{i}({c['x']},{c['y']}) unreachable")
    for i, n in enumerate(mm["npcs"]):
        # NPCは隣接かカウンター越し(2マス)で話せればOK
        near = any((n["x"] + dx, n["y"] + dy) in reach for dx, dy in ((1,0),(-1,0),(0,1),(0,-1),(2,0),(-2,0),(0,2),(0,-2)))
        if not near:
            problems.append(f"{mid}: npc{i}({n['x']},{n['y']}) unreachable")
    for i, t in enumerate(mm["triggers"]):
        if (t["x"], t["y"]) not in reach:
            problems.append(f"{mid}: trigger{i}({t['x']},{t['y']}) unreachable")

if problems:
    print("!!! REACHABILITY PROBLEMS")
    for p in problems:
        print("  -", p)
else:
    print("reachability: all OK")

# ============================ 出力 ============================
out = "// GENERATED by tools/gen_maps.py — do not edit by hand\n"
out += "const MAPS_GEN = " + json.dumps(MAPS, ensure_ascii=False, indent=1) + ";\n"
with open("js/maps.gen.js", "w", encoding="utf-8") as f:
    f.write(out)
print("written js/maps.gen.js")
for name in ["world", "town", "cave", "castle", "castle2", "bossroom", "inn", "elder"]:
    print("=" * 42)
    print("--", name)
    for r in MAPS[name]["tiles"]:
        print(r)
