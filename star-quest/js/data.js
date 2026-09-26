/* ============================================================
   スタークエスト - data.js
   パレット / スプライト / マップ / 敵 / アイテム / 魔法 / 会話
   ============================================================ */

"use strict";

/* ---------- スプライト ---------- */
// 文字 -> 色 のパレット。'.' は透明。
// スプライトは {w,h,pal,rows}。rows の各行は w 文字。

const SPR = {};

function mkSpr(rows, pal) {
  return { w: rows[0].length, h: rows.length, rows: rows, pal: pal };
}

// 勇者パレット
const PAL_HERO = {
  k: "#1a1424", // 輪郭
  s: "#ffd9a0", // 肌
  e: "#2a1c10", // 目
  h: "#7a4a1e", // 髪
  b: "#2a5bd7", // 服(青)
  d: "#1c3563", // ズボン
  o: "#5a3418", // ブーツ
  w: "#f0f0f0",
  r: "#c03030",
};

SPR.hero_down0 = mkSpr([
  "................",
  "....kkkkkkkk....",
  "...khhhhhhhhk...",
  "..khhhhhhhhhhk..",
  "..khhsssssshhk..",
  "..khssessesshk..",
  "..khsssssssshk..",
  "...kssssssssk...",
  "....kbbbbbbk....",
  "...kbbbbbbbbk...",
  "..ksbbbbbbbbsk..",
  "..ksbbbbbbbbsk..",
  "...kbbbbbbbbk...",
  "....kddddddk....",
  "....kddkkddk....",
  "....kookkook....",
], PAL_HERO);

SPR.hero_down1 = mkSpr([
  "................",
  "....kkkkkkkk....",
  "...khhhhhhhhk...",
  "..khhhhhhhhhhk..",
  "..khhsssssshhk..",
  "..khssessesshk..",
  "..khsssssssshk..",
  "...kssssssssk...",
  "....kbbbbbbk....",
  "...kbbbbbbbbk...",
  "..ksbbbbbbbbsk..",
  "..ksbbbbbbbbsk..",
  "...kbbbbbbbbk...",
  "....kddddddk....",
  "...kddk..kddk...",
  "...kook..kook...",
], PAL_HERO);

SPR.hero_down2 = mkSpr([
  "................",
  "....kkkkkkkk....",
  "...khhhhhhhhk...",
  "..khhhhhhhhhhk..",
  "..khhsssssshhk..",
  "..khssessesshk..",
  "..khsssssssshk..",
  "...kssssssssk...",
  "....kbbbbbbk....",
  "...kbbbbbbbbk...",
  "..ksbbbbbbbbsk..",
  "..ksbbbbbbbbsk..",
  "...kbbbbbbbbk...",
  "....kddddddk....",
  "....kddkddk.....",
  "....kookook.....",
], PAL_HERO);

SPR.hero_up0 = mkSpr([
  "................",
  "....kkkkkkkk....",
  "...khhhhhhhhk...",
  "..khhhhhhhhhhk..",
  "..khhhhhhhhhhk..",
  "..khhkhhhhkhhk..",
  "..khhhhhhhhhhk..",
  "...khhhhhhhhk...",
  "....kbbbbbbk....",
  "...kbbbbbbbbk...",
  "..ksbbbbbbbbsk..",
  "..ksbbbbbbbbsk..",
  "...kbbbbbbbbk...",
  "....kddddddk....",
  "....kddkkddk....",
  "....kookkook....",
], PAL_HERO);

SPR.hero_up1 = mkSpr([
  "................",
  "....kkkkkkkk....",
  "...khhhhhhhhk...",
  "..khhhhhhhhhhk..",
  "..khhhhhhhhhhk..",
  "..khhkhhhhkhhk..",
  "..khhhhhhhhhhk..",
  "...khhhhhhhhk...",
  "....kbbbbbbk....",
  "...kbbbbbbbbk...",
  "..ksbbbbbbbbsk..",
  "..ksbbbbbbbbsk..",
  "...kbbbbbbbbk...",
  "....kddddddk....",
  "...kddk..kddk...",
  "...kook..kook...",
], PAL_HERO);

SPR.hero_up2 = mkSpr([
  "................",
  "....kkkkkkkk....",
  "...khhhhhhhhk...",
  "..khhhhhhhhhhk..",
  "..khhhhhhhhhhk..",
  "..khhkhhhhkhhk..",
  "..khhhhhhhhhhk..",
  "...khhhhhhhhk...",
  "....kbbbbbbk....",
  "...kbbbbbbbbk...",
  "..ksbbbbbbbbsk..",
  "..ksbbbbbbbbsk..",
  "...kbbbbbbbbk...",
  "....kddddddk....",
  "....kddkddk.....",
  "....kookook.....",
], PAL_HERO);

// 右向き(左は反転で生成)
SPR.hero_right0 = mkSpr([
  "................",
  "....kkkkkkk.....",
  "...khhhhhhhk....",
  "..khhhhhhhhhk...",
  "..khhhhhssshk...",
  "..khhhhhssesk...",
  "..khhhhsssshk...",
  "...khhsssssk....",
  "....kbbbbbbk....",
  "...kbbbbbbbk....",
  "..kbbbbbbbksk...",
  "..kbbbbbbbk.....",
  "...kbbbbbbbk....",
  "....kdddddk.....",
  "....kddkddk.....",
  "....kookook.....",
], PAL_HERO);

SPR.hero_right1 = mkSpr([
  "................",
  "....kkkkkkk.....",
  "...khhhhhhhk....",
  "..khhhhhhhhhk...",
  "..khhhhhssshk...",
  "..khhhhhssesk...",
  "..khhhhsssshk...",
  "...khhsssssk....",
  "....kbbbbbbk....",
  "...kbbbbbbbk....",
  "..kbbbbbbbksk...",
  "..kbbbbbbbk.....",
  "...kbbbbbbbk....",
  "....kdddddk.....",
  "...kddk.kddk....",
  "...kook.kook....",
], PAL_HERO);

SPR.hero_right2 = mkSpr([
  "................",
  "....kkkkkkk.....",
  "...khhhhhhhk....",
  "..khhhhhhhhhk...",
  "..khhhhhssshk...",
  "..khhhhhssesk...",
  "..khhhhsssshk...",
  "...khhsssssk....",
  "....kbbbbbbk....",
  "...kbbbbbbbk....",
  "..kbbbbbbbksk...",
  "..kbbbbbbbk.....",
  "...kbbbbbbbk....",
  "....kdddddk.....",
  ".....kdddk......",
  "....kook.ook....",
], PAL_HERO);

// 左向き = 右向きの左右反転(起動時に生成)
function mirrorSpr(s) {
  const rows = s.rows.map(r => r.split("").reverse().join(""));
  return mkSpr(rows, s.pal);
}

/* ---------- NPC スプライト ---------- */
function npcPal(cloth, hair, extra) {
  return Object.assign({
    k: "#1a1424", s: "#ffd9a0", e: "#2a1c10",
    h: hair, b: cloth, d: "#333", o: "#4a3418", w: "#f0f0f0",
  }, extra || {});
}

SPR.npc_elder = mkSpr([
  "................",
  "....kkkkkkk.....",
  "...khhhhhhhk....",
  "..khhhhhhhhhk...",
  "..khssssssshk...",
  "..khsessesshk...",
  "..khssssssshk...",
  "...ksswwwwsk....",  // 白いひげ
  "....kwwwwwk.....",
  "...kwpwwpwk.....",
  "..kppppppppk....",
  "..kspppppppsk...",
  "..kspppppppsk...",
  "...kpppppppk....",
  "...kpppppppk....",
  "...kpppkpppk....",
], npcPal("#8048d0", "#c8c8d8", { p: "#8048d0" }));

SPR.npc_inn = mkSpr([
  "................",
  "....kkkkkkk.....",
  "...khhhhhhhk....",
  "..khhhhhhhhhk...",
  "..khssssssshk...",
  "..khsessesshk...",
  "..khssssssshk...",
  "...ksssssssk....",
  "....kgggggk.....",
  "...kgggggggk....",
  "..kggggggggk....",
  "..ksggggggsk....",
  "..ksggggggsk....",
  "...kggggggk.....",
  "...kggggggk.....",
  "...kkkkkkkk.....",
], npcPal("#38a038", "#5a3418", { g: "#38a038" }));

SPR.npc_shop = mkSpr([
  "................",
  "....krrrrrk.....",
  "...krrrrrrrk....",
  "..krrrrrrrrk...",
  "..khssssssshk...",
  "..khsessesshk...",
  "..khssssssshk...",
  "...ksssssssk....",
  "....kbbbbbk.....",
  "...kbbbbbbbk....",
  "..kbbbbbbbbbk...",
  "..ksbbbbbbssk...",
  "..ksbbbbbbssk...",
  "...kbbbbbbk.....",
  "...kddddddk.....",
  "...kookkook.....",
], npcPal("#2a5bd7", "#1a1424", { r: "#c03030", d: "#3a2f5e", o: "#5a3418" }));

SPR.npc_vil1 = mkSpr([
  "................",
  "....kkkkkkk.....",
  "...khhhhhhhk....",
  "..khhhhhhhhhk...",
  "..khssssssshk...",
  "..khsessesshk...",
  "..khssssssshk...",
  "...ksssssssk....",
  "....koooooo.....",
  "...kooooook....",
  "..koooooooo k...",
  "..ksoooooosk....",
  "..ksoooooosk....",
  "...kooooook.....",
  "...kddkdddk.....",
  "...kookookk.....",
], npcPal("#b06818", "#402810", { o: "#b06818", d: "#5a3a20" }));

SPR.npc_vil2 = mkSpr([
  "................",
  "....kkkkkkk.....",
  "...khhhhhhhk....",
  "..khhhhhhhhhk...",
  "..khssssssshk...",
  "..khsessesshk...",
  "..khssssssshk...",
  "...ksssssssk....",
  "...khhhhhhhk....",
  "..khhppppphhk...",
  "..khppppppphk...",
  "..kpppppppppk...",
  "..kpppppppppk...",
  "...kpppppppk....",
  "...kpppppppk....",
  "...kpkkkpkk.....",
], npcPal("#e060a0", "#c89030", { p: "#e060a0" }));

SPR.npc_guard = mkSpr([
  "................",
  "....kkkkkkk.....",
  "...kEEEEEEk.....",
  "..kEwwwwwEk.....",
  "..kEskkkksEk....",
  "..kEsesesesEk...",
  "..kEsssssssEk...",
  "...kssssssk.....",
  "....kEEEEEk.....",
  "...kEEEEEEEk....",
  "..kEEEEEEEEEk...",
  "..ksEEEEEEEsk...",
  "..ksEEEEEEEsk...",
  "...kEEEEEEEk....",
  "...kddkdddk.....",
  "...kookookk.....",
], npcPal("#9098a8", "#404048", { E: "#9098a8", d: "#404048", o: "#282828" }));

/* ---------- 敵スプライト ---------- */
const PAL_ENEMY = {
  k: "#101018", w: "#f0f0f0", e: "#101018", r: "#e03030",
};

SPR.en_slime = mkSpr([
  "................",
  "................",
  "................",
  "................",
  ".....kkkk.......",
  "....kBBBBk......",
  "...kBBBBBBk.....",
  "..kBwkBBwkBBk...",
  "..kBBkBBkBBB k..",
  ".kBBBBBBBBBBBk..",
  ".kBBBkBBBkBBBk..",
  ".kBBBBBBBBBBBk..",
  "kBBBBBBBBBBBBBk.",
  "kBBBkBBBBBkBBBkk",
  ".kkkkkkkkkkkkkk.",
  "................",
], { k: "#101018", B: "#38a8d8", w: "#f0f0f0", e: "#101018" });

SPR.en_bat = mkSpr([
  "................",
  "................",
  "..k..........k..",
  ".kPk........Pk.",
  ".kPPk......kPPk.",
  "kPPPPk....kPPPPk",
  "kPPrPPk..kPPrPPk",
  "kPPPPPPkkPPPPPPk",
  ".kPPPPPPPPPPPPk.",
  "..kPPkBBeBkPPk..",
  "...kPPBBBBPPk...",
  "....kPBBBBPk....",
  ".....kBBBBk.....",
  "......kBBk......",
  ".......kk.......",
  "................",
], { k: "#101018", P: "#7048b0", B: "#402870", e: "#f0f0f0" });

SPR.en_goblin = mkSpr([
  "................",
  "................",
  "....kkkkkkk.....",
  "..kkGGGGGGGkk...",
  ".kGkGGGGGGGkGk..",
  ".kkGGrGGGrGGk...",
  "..kGGGGGGGGGk...",
  "..kGGGkkkGGGk...",
  "...kGGGGGGGk....",
  "....kkkkkkk.....",
  "...kGGGGGGGk....",
  "..kGGGGGGGGGk...",
  "..kGkkkkkkkGk...",
  "..kGGGGGGGGGk...",
  "...kGGk.kGGk....",
  "...kkk...kkk....",
], { k: "#101018", G: "#48a038", r: "#e03030" });

SPR.en_wolf = mkSpr([
  "................",
  "................",
  "................",
  "..kk............",
  ".kGGk...........",
  "kGrGGk...kkkkk..",
  "kGGGGGkkGGGGGGk.",
  ".kGGGGGGGGGGGGk.",
  "..kGGGGGGGGGGk..",
  "...kGGGGGGGGk...",
  "...kGGk..kGGk...",
  "...kGGk..kGGk...",
  "...kGk....kGk...",
  "...kkk....kkk...",
  "................",
  "................",
], { k: "#101018", G: "#9098a8", r: "#e03030" });

SPR.en_skeleton = mkSpr([
  "................",
  "....kkkkkkk.....",
  "...kwwwwwwwk....",
  "..kwwwwwwwwwk...",
  "..kweewweewwk...",
  "..kwwwkkkwwwk...",
  "..kwwwwwwwwwk...",
  "...kkwkwkwkk....",
  "....kwwwwwk.....",
  "...kwwwwwwwk....",
  "..kwkwkwkwkwk...",
  "..kwwwwwwwwwk...",
  "..kwkwwwwwkwk...",
  "...kwk...kwk....",
  "...kwk...kwk....",
  "...kkk...kkk....",
], { k: "#101018", w: "#e8e8d8", e: "#101018" });

SPR.en_mage = mkSpr([
  "................",
  ".....kkkkk......",
  "....kPPPPPk.....",
  "...kPPPPPPPk....",
  "..kPPPPPPPPPk...",
  "..kPPPPPPPPPk...",
  "...ksssssssk....",
  "...ksessesk.....",
  "...ksssssssk....",
  "..kPPPPPPPPPk...",
  "..kPPPYYPPPPk...",
  ".kPPPPYYPPPPPk..",
  ".kPsPPPPPPPsPk..",
  ".kPPPPPPPPPPPk..",
  ".kPPPPPPPPPPPk..",
  ".kkkkkkkkkkkkk..",
], { k: "#101018", P: "#6030a0", s: "#ffd9a0", e: "#101018", Y: "#f0c030" });

SPR.en_gargoyle = mkSpr([
  "................",
  ".kk..........kk.",
  ".kEk........kEk.",
  ".kEEk..kk..kEEk.",
  ".kEEEkkEGEkkEEEk",
  "..kEEEGGGGGEEEk.",
  "..kkEGreerGEkk..",
  "...kGGGGGGGGk...",
  "...kGGkGGkGGk...",
  "..kEGGGGGGGGEk..",
  "..kEGkGGGGkGEk..",
  "...kGGGGGGGGk...",
  "...kGGk..kGGk...",
  "..kGGk....kGGk..",
  "..kkk......kkk..",
  "................",
], { k: "#101018", E: "#787888", G: "#585868", r: "#e03030" });

SPR.en_darkknight = mkSpr([
  "................",
  "....kkkkkkk.....",
  "...kDDDDDDDk....",
  "..kDDDDDDDDDk...",
  "..kDrrrrrrrDk...",
  "..kDDDDDDDDDk...",
  "..kDDkkkkkDDk...",
  "...kDDDDDDDk....",
  "..kDDDDDDDDDk...",
  ".kDDDDDDDDDDDk..",
  ".kDDDkkkkkDDDs k",
  ".ksDDDDDDDDDDsk.",
  ".ksDDDDDDDDDDsk.",
  "..kDDDDDDDDDk...",
  "..kDDk...kDDk...",
  "..kkk.....kkk...",
], { k: "#080810", D: "#282838", r: "#d81818", s: "#c0c0d0" });

// ボス: 魔王ヴァルドラス 32x32
SPR.en_boss = mkSpr([
  "................................",
  "......kk..................kk....",
  ".....kRRk................kRRk...",
  "....kRRRRk..............kRRRRk..",
  "....kRRRRRk............kRRRRRk..",
  "...kRRRRRRk..kkkkkk..kRRRRRRk...",
  "...kRRRRRk..kDDDDDDk..kRRRRRk...",
  "....kkkk...kDDDDDDDDk...kkkk....",
  "..........kDDrrDDrrDDk..........",
  "..........kDDDDDDDDDDk..........",
  "..kk......kDDkDDDDkDDk......kk..",
  ".kPPk.....kDDDDDDDDDDk.....kPPk.",
  ".kPPPk.....kDDDDDDDDk.....kPPPk.",
  "kPPPPPk.....kDDDDDDk.....kPPPPPk",
  "kPPPPPPk..kkkkkkkkkkk...kPPPPPPk",
  "kPPPPPPPk.kDDDDDDDDDk.kPPPPPPPPk",
  "kPPPPPPPPkkDDDDDDDDDkkPPPPPPPPk",
  ".kPPPPPPPPDDDDDkDDDDDPPPPPPPPk.",
  "..kPPPPPPDDDDDDkDDDDDDPPPPPPk..",
  "...kPPPPDDDDDDDDD DDDDPPPPk...",
  "....kPPDDDDDDrDDDDDDDDPPk.....",
  ".....kPDDDDDrDrDDDDDDDPk......",
  ".....kDDDDDDrDrDDDDDDDk.......",
  "....kDDDDDDDrDrDDDDDDDDk......",
  "...kDDDDDDDDrDrDDDDDDDDDk.....",
  "...kDDDDDDDDDrDDDDDDDDDDk.....",
  "..kDDDDDDDDDDrDDDDDDDDDDDDk...",
  "..kDDDDDDDDDDrDDDDDDDDDDDDk...",
  "..kDDDDDDDDDDrDDDDDDDDDDDDk...",
  "...kkkkkkkkkkkkkkkkkkkkkkkk...",
  "................................",
  "................................",
], { k: "#080810", R: "#c01818", D: "#301838", P: "#501868", r: "#ff2828" });

// 左向き生成
SPR.hero_left0 = mirrorSpr(SPR.hero_right0);
SPR.hero_left1 = mirrorSpr(SPR.hero_right1);
SPR.hero_left2 = mirrorSpr(SPR.hero_right2);

/* ---------- タイル定義 ---------- */
// block: 通行不可, zone: エンカウントゾーン名, anim: 水など
const TILE_PROPS = {
  "#": { block: true },   // 山 / 岩壁
  "T": { block: true },   // 木
  ".": { block: false },  // 草
  ",": { block: false, zone: "field" }, // 深い草むら(弱)
  ";": { block: false, zone: "forest" }, // 深い森草(中)
  "f": { block: false },  // 花
  "p": { block: false },  // 道
  "~": { block: true },   // 水
  "=": { block: false },  // 橋
  "s": { block: false },  // 土/砂
  "H": { block: true },   // 家の壁
  "R": { block: true },   // 屋根
  "D": { block: false },  // ドア(ワープ)
  "F": { block: false },  // 石の床
  "W": { block: true },   // 石壁
  "P": { block: true },   // 柱
  "o": { block: true },   // たいまつ
  "S": { block: false },  // 階段(ワープ)
  "q": { block: true },   // カウンター
  "Q": { block: true },   // ベッド
  "u": { block: true },   // テーブル
  "j": { block: true },   // つぼ
  "r": { block: false },  // カーペット
  "G": { block: true },   // 城の門
  "B": { block: false },  // 暗い床
  "X": { block: true },   // 岩
  "m": { block: true },   // 城壁
  "V": { block: true },   // 井戸/装飾
  "n": { block: false },  // 洞窟入口(ワープ)
  "!": { block: false },  // 出口マット(ワープ)
  "x": { block: true },   // 柵
  "Z": { block: false },  // ボスの間への扉
  "E": { block: false },  // 城入口(ワープ用)
};

/* ---------- アイテム ---------- */
const ITEMS = {
  potion:   { name: "ポーション",   price: 20,  hp: 50,  desc: "HPを50かいふく" },
  hipotion: { name: "ハイポーション", price: 80, hp: 160, desc: "HPを160かいふく" },
  ether:    { name: "エーテル",     price: 60,  mp: 20,  desc: "MPを20かいふく" },
  elixir:   { name: "エリクサー",   price: 400, full: 1, desc: "HP・MPをぜんかいふく" },
  smoke:    { name: "けむりだま",   price: 30,  smoke: 1, desc: "たたかいからかならずにげる" },
};

/* ---------- 装備 ---------- */
const GEAR = {
  w_stick:  { name: "ひのきのぼう", type: "w", atk: 2,  price: 10,  desc: "たいした いりょくはない" },
  w_copper: { name: "どうのつるぎ", type: "w", atk: 6,  price: 90,  desc: "どうでできた つるぎ" },
  w_iron:   { name: "てつのつるぎ", type: "w", atk: 11, price: 260, desc: "てつでできた つるぎ" },
  w_steel:  { name: "はがねのつるぎ", type: "w", atk: 17, price: 700, desc: "はがねでできた つるぎ" },
  w_light:  { name: "ひかりのつるぎ", type: "w", atk: 26, price: 0,   desc: "せいなる ひかりをやどすつるぎ" },
  a_cloth:  { name: "ぬののふく",   type: "a", def: 2,  price: 10,  desc: "ふつうの ふく" },
  a_leather:{ name: "かわのよろい", type: "a", def: 5,  price: 110, desc: "かわでできた よろい" },
  a_chain:  { name: "くさりかたびら", type: "a", def: 9, price: 320, desc: "くさりを あんだ かたびら" },
  a_iron:   { name: "てつのよろい", type: "a", def: 14, price: 900, desc: "てつでできた よろい" },
  a_dragon: { name: "ドラゴンメイル", type: "a", def: 20, price: 0,   desc: "りゅうの うろこでできたよろい" },
};

/* ---------- 魔法 ---------- */
const SPELLS = {
  fire:     { name: "ファイア",   mp: 5,  kind: "dmg",  pow: 17, all: false, learn: 2, fx: "fire",  desc: "てき1たいに ほのおのダメージ" },
  heal:     { name: "ヒール",     mp: 4,  kind: "heal", pow: 45, learn: 3,  fx: "heal", desc: "HPを45かいふく" },
  bolt:     { name: "サンダー",   mp: 8,  kind: "dmg",  pow: 20, all: true,  learn: 6,  fx: "bolt",  desc: "てきぜんたいに かみなりのダメージ" },
  megaheal: { name: "メガヒール", mp: 12, kind: "heal", pow: 9999, learn: 9, fx: "heal", desc: "HPをぜんかいふく" },
};

/* ---------- レベル ---------- */
function expForLevel(lv) { return lv * lv * 3 + lv * 5; } // 次のレベルに必要な累計EXP
function baseStats(lv) {
  return {
    maxhp: 20 + lv * 9,
    maxmp: lv >= 2 ? 2 + lv * 2 : 0,
    atk: 4 + lv * 2,
    def: 2 + lv,
    spd: 4 + Math.floor(lv * 1.5),
  };
}

/* ---------- 敵 ---------- */
const ENEMIES = {
  slime:      { name: "スライム",       spr: "en_slime",      hp: 16,  mp: 0, atk: 7,  def: 2,  spd: 3,  exp: 5,   gold: 6 },
  bat:        { name: "こうもり",       spr: "en_bat",        hp: 14,  mp: 0, atk: 9,  def: 1,  spd: 10, exp: 6,   gold: 5 },
  goblin:     { name: "ゴブリン",       spr: "en_goblin",     hp: 27,  mp: 0, atk: 12, def: 4,  spd: 5,  exp: 12,  gold: 13 },
  wolf:       { name: "おおかみ",       spr: "en_wolf",       hp: 32,  mp: 0, atk: 15, def: 4,  spd: 13, exp: 16,  gold: 11 },
  skeleton:   { name: "スケルトン",     spr: "en_skeleton",   hp: 42,  mp: 0, atk: 17, def: 8,  spd: 6,  exp: 24,  gold: 24 },
  mage:       { name: "まほうつかい",   spr: "en_mage",       hp: 36,  mp: 30, atk: 11, def: 5,  spd: 8,  exp: 30,  gold: 34, spell: "fire" },
  gargoyle:   { name: "ガーゴイル",     spr: "en_gargoyle",   hp: 58,  mp: 0, atk: 21, def: 11, spd: 12, exp: 40,  gold: 46 },
  darkknight: { name: "ダークナイト",   spr: "en_darkknight", hp: 85,  mp: 0, atk: 26, def: 15, spd: 9,  exp: 60,  gold: 75 },
  boss:       { name: "魔王ヴァルドラス", spr: "en_boss",     hp: 380, mp: 99, atk: 30, def: 16, spd: 14, exp: 650, gold: 0, boss: true },
};

// ゾーン別出現テーブル [重み, 敵id...]
const ZONES = {
  field: [
    [35, "slime"], [20, "bat"], [15, "slime", "slime"],
    [15, "goblin"], [10, "slime", "bat"], [5, "goblin", "slime"],
  ],
  forest: [
    [25, "goblin"], [20, "wolf"], [15, "bat", "bat"],
    [15, "goblin", "goblin"], [15, "wolf", "bat"], [10, "goblin", "wolf"],
  ],
  cave: [
    [20, "bat", "bat"], [20, "skeleton"], [15, "wolf"],
    [15, "skeleton", "bat"], [15, "wolf", "wolf"], [15, "skeleton", "skeleton"],
  ],
  castle: [
    [20, "skeleton", "skeleton"], [20, "gargoyle"], [15, "mage"],
    [15, "gargoyle", "skeleton"], [15, "darkknight"], [15, "mage", "gargoyle"],
  ],
  castle2: [
    [25, "darkknight"], [20, "gargoyle", "gargoyle"], [20, "mage", "darkknight"],
    [20, "darkknight", "skeleton"], [15, "darkknight", "darkknight"],
  ],
};

/* ---------- ショップ ---------- */
const SHOP_STOCK = [
  "w_copper", "w_iron", "w_steel",
  "a_leather", "a_chain", "a_iron",
  "potion", "hipotion", "ether", "smoke",
];

/* ---------- マップ ---------- */
// マップは tools/gen_maps.py が生成する js/maps.gen.js (MAPS_GEN)
const MAPS = MAPS_GEN;

/* ---------- 会話スクリプト ---------- */
// api: { say(lines[,name]), choice(options), give(...), openShop(), rest(), flag(k), setFlag(k,v), endBattle(), heal(), warp(...) }
const SCRIPTS = {};

SCRIPTS.elder = (api) => {
  if (api.flag("bossDown")) {
    api.say([
      "ゆうしゃよ… よくぞ まおうを たおしてくれた。",
      "ほしのかけらの ひかりが せかいを てらしている。",
      "わしらは なんどでも あなたに かんしゃするだろう。",
    ], "ちょうろう");
    return;
  }
  if (!api.flag("started")) {
    api.setFlag("started", true);
    api.say([
      "おお… ゆうしゃよ、よく きてくれた。",
      "このせかいの そらから 『ほしのかけら』が うばわれ、",
      "まおうヴァルドラスが きたのしろに すみついたのじゃ。",
      "かれの やみによって、まものが どんどん ふえておる…。",
      "しろの もんは 『ひかりのカギ』で かたく とざされておる。",
      "カギは むらの にし、きたのもりの どうくつに ねむっておる。",
      "まずは どうくつへ むかい、カギを てにいれるのじゃ！",
      "これを もっていきなさい。",
    ], "ちょうろう");
    api.giveItem("potion", 3);
    api.giveGold(80);
    api.say(["ポーション×3 と 80G を うけとった！"]);
  } else if (!api.flag("hikariKey")) {
    api.say([
      "『ひかりのカギ』は にしの きたのもり、",
      "いわに かこまれた どうくつの おくに ねむっておる。",
      "どうくつは あぶない。じゅんびを ととのえて いきなさい。",
    ], "ちょうろう");
  } else {
    api.say([
      "『ひかりのカギ』を もっておるのか！ さすがじゃ。",
      "かわを わたり、きたの まおうじょうへ むかうのじゃ。",
      "まおうは つよい。レベルを あげ、よい ぶきを そなえるのだぞ。",
      "…どうか、きをつけて。",
    ], "ちょうろう");
  }
};

SCRIPTS.inn = (api) => {
  api.say(["いらっしゃい。10Gで やすんでいきますかい？"], "やどやの しゅじん");
  api.choice(["やすむ (10G)", "やめとく"], (i) => {
    if (i === 0) api.rest();
    else api.say(["また どうぞ。"], "やどやの しゅじん");
  });
};

SCRIPTS.shop = (api) => {
  api.say(["いらっしゃい！ よい ぶきが はいったよ。"], "てんしゅ");
  api.openShop();
};

SCRIPTS.guard = (api) => {
  if (api.flag("bossDown")) {
    api.say(["ゆうしゃさま！ へいわが もどったんですね！！"], "もりのへいし");
  } else {
    api.say([
      "きたには まおうじょう。まものが うようよ います。",
      "じゅんびが できたら、ちょうろうさまの ところへ いくんだ。",
    ], "もりのへいし");
  }
};

SCRIPTS.vil1 = (api) => {
  api.say([
    "このむらは へいわだったのに… まものが ふえて こわいよ。",
    "そういえば にしの どうくつに、たからものが あるらしい。",
  ], "むらびと");
};

SCRIPTS.vil2 = (api) => {
  api.say([
    "まものは ふかい くさむらに ひそんでいるわ。",
    "くさむらを あるくときは きをつけてね。",
  ], "むらびと");
};

SCRIPTS.vil3 = (api) => {
  api.say([
    "ゆうしゃさま… ほしのかけらを とりもどしてね。",
    "まおうは ほのおと やみを あやつるそうよ… こわいわねぇ。",
  ], "おばあさん");
};

SCRIPTS.boss = (api) => {
  api.bossBattle();
};

// ボスの間に足を踏み入れたときの自動イベント
SCRIPTS.bossApproach = (api) => {
  if (api.flag("bossDown")) return;
  if (api.flag("bossIntroSeen")) return;
  api.setFlag("bossIntroSeen", true);
  api.say([
    "フフフ… よくぞ ここまで たどりついたな、ちいさな ゆうしゃよ。",
    "ほしのかけらは わがてに ある。せかいは やみに しずむのだ！",
    "こい、ゆうしゃ！！ その ちから、みせてみよ！！",
  ], "魔王ヴァルドラス");
  api.bossBattle();
};

/* ---------- ボス戦後 ---------- */
SCRIPTS.ending = [];

/* ---------- マップ整合チェック ---------- */
function validateData() {
  const errs = [];
  for (const id in MAPS) {
    const m = MAPS[id];
    const w = m.tiles[0].length;
    m.tiles.forEach((row, y) => {
      if (row.length !== w) errs.push(`${id}: row ${y} width ${row.length} != ${w}`);
      for (const ch of row) {
        if (!(ch in TILE_PROPS)) errs.push(`${id}: unknown tile '${ch}' at y=${y}`);
      }
    });
    const H = m.tiles.length;
    const chk = (x, y, what) => {
      if (x < 0 || y < 0 || x >= w || y >= H) errs.push(`${id}: ${what} out of bounds (${x},${y})`);
    };
    (m.warps || []).forEach((wp, i) => {
      chk(wp.x, wp.y, `warp${i}`);
      if (!MAPS[wp.to]) errs.push(`${id}: warp${i} to unknown map '${wp.to}'`);
    });
    (m.chests || []).forEach((c, i) => chk(c.x, c.y, `chest${i}`));
    (m.npcs || []).forEach((n, i) => chk(n.x, n.y, `npc${i}`));
  }
  for (const z in ZONES) {
    ZONES[z].forEach((g, i) => g.slice(1).forEach(e => {
      if (!ENEMIES[e]) errs.push(`zone ${z}[${i}]: unknown enemy '${e}'`);
    }));
  }
  for (const id in GEAR) if (!GEAR[id].name) errs.push(`gear ${id}: no name`);
  return errs;
}
