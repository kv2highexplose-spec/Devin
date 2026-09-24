"""Parse product name/spec text into structured specs and map to bench keys."""
from __future__ import annotations

import re
import unicodedata

from .bench import CPU, GPU


def norm(s: str) -> str:
    s = re.sub(r"[™®]|\(tm\)|\(r\)", "", s or "")
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"(?<=[a-z])tm(?![a-z0-9])", "", s.lower())
    return s


# ---------------- CPU ----------------
def _m_int(grade: str, model: str) -> str:
    return f"i{grade}-{model}"


def match_cpu(text: str) -> str | None:
    t = norm(text).lower()
    t = t.replace("corei", "core i").replace("core i ", "core i")
    # Intel Core iN - pattern: i7-14650HX / i5 8400 / Core i7 13700
    m = re.search(r"(?:core\s*)?i([3579])\s*[-–]?\s*(\d{4,5}[a-z0-9]*)(?![a-z0-9])", t)
    if m:
        return _m_int(m.group(1), m.group(2))
    # "Core i3" (10th gen hidden) handled below; plain i3-XXX like i3-N305
    m = re.search(r"(?<![a-z0-9])i3-(n305|n300)(?![a-z0-9])", t)
    if m:
        return f"i3-{m.group(1)}"
    # Core Ultra: ultra 7 265K / Ultra 7 155H / Ultra7 258V
    m = re.search(r"(?:core\s*)?ultra\s*([3579])\s*[-–]?\s*(\d{3}[a-z]*)\s*(plus)?", t)
    if m:
        base = f"ultra {m.group(1)} {m.group(2)}"
        if m.group(3):
            base += " plus"
        return base
    # Ryzen AI: "Ryzen AI 9 HX 370" / "Ryzen AI Max+ 395"
    m = re.search(r"ryzen\s*ai\s*max\+?\s*(\d{3})", t)
    if m:
        return f"ryzen ai max {m.group(1)}" if f"ryzen ai max {m.group(1)}" in CPU else f"ryzen ai max+ {m.group(1)}"
    m = re.search(r"ryzen\s*ai\s*(9|7|5)\s*(hx\s*)?(\d{3})", t)
    if m:
        hx = "hx " if m.group(2) else ""
        return f"ryzen ai {m.group(1)} {hx}{m.group(3)}"
    # Ryzen PRO: "Ryzen 5 PRO 4650G" / "R5 PRO 3400GE" / "Ryzen 5 PRO 3400GE"
    m = re.search(r"(?:ryzen\s*|r)([357])\s*pro\s*(\d{4,5}[a-z0-9]*)", t)
    if m:
        key = f"{m.group(1)} pro {m.group(2)}"
        if key in CPU:
            return key
        return m.group(2)  # fall back to bare model e.g. 4650g
    # Ryzen: "Ryzen 7 9700X" / "Ryzen5 5600G" / "R7 5800X3D" / "Ryzen 9 5950X"
    m = re.search(r"(?:ryzen\s*(?:[3579])?\s*|r[3579]\s*)(\d{4,5}[a-z0-9]*)(?![a-z0-9])", t)
    if m:
        model = m.group(1)
        if re.match(r"[1-9]\d{3,4}", model):
            return model
    # Xeon: "Xeon W-2125" / "E5-2690 v4" / "E-2236" / "E3-1230 v5" / "Silver 4310"
    m = re.search(r"xeon\s+(w-?\d{4}|e-?\d{4}[a-z]?|e[35]-\d{4}\s*v?\d|w\d-\d{4}[a-z]*)", t)
    if m:
        g = m.group(1)
        if re.match(r"e\d-", g):
            return g                    # e3-xxxx vN / e5-xxxx vN
        if re.match(r"[we]\d", g):
            return g[0] + "-" + g[1:]   # w2125 -> w-2125, e2236 -> e-2236
        return g
    m = re.search(r"(?<![a-z0-9])(e[35]-\d{4}\s*v\d|w-\d{4}|e-\d{4}[a-z]?)(?![a-z0-9])", t)
    if m:
        return m.group(1)
    # Apple M
    m = re.search(r"(?<![a-z0-9-])m([1-5])\s*(pro|max|ultra)?(?![a-z0-9])", t)
    if m:
        base = f"m{m.group(1)}"
        if m.group(2):
            base += f" {m.group(2)}"
        return base if base in CPU else f"m{m.group(1)}"
    # Pentium/Celeron/N/J series bare models
    m = re.search(r"(?<![a-z0-9])(pentium\s*(?:gold\s*)?|celeron\s*)?([gnj]\d{4,5}u?|n\d{2,4})(?![a-z0-9])", t)
    if m:
        cand = m.group(2)
        if cand in CPU:
            return cand
    return None


# ---------------- GPU ----------------
def match_gpu(text: str) -> str | None:
    t = norm(text).lower()
    t = re.sub(r"(geforce|nvidia|radeon|グラフィックス?|graphics)\s*", "", t)
    laptop = bool(re.search(r"laptop|ノート|mobile|搭載gpu|for\s*laptop", t))
    # Quadro / pro first (they contain "rtx"/"radeon" too)
    m = re.search(r"(quadro\s+rtx\s*\d{4}|quadro\s+p\d{3,4}|quadro\s+k\d{4}|rtx\s*a\d{4}(?:\s*\dgb)?|rtx\s*\d{4}\s*(?:sff\s*)?ada|rtx\s*\d{4}\s*ada\s*laptop|\bt\d{3,4}(?:\s*\dgb)?(?:\s*laptop)?|firepro\s*w\d{4}|radeon\s*pro\s*w\d{4}|radeon\s*pro\s*wx\s*\d{4})", t)
    if m:
        return re.sub(r"\s+", " ", m.group(1).strip())
    # RTX xxxx Ti/Super (+optional GB, Laptop)
    m = re.search(r"rtx\s*(\d{4})\s*(ti)?\s*(super)?\s*(\d{1,2}\s*gb)?", t)
    if m:
        num, ti, sup, gb = m.group(1), m.group(2), m.group(3), m.group(4)
        key = f"rtx {num}"
        if ti:
            key += " ti"
        if sup:
            key += " super"
        if gb:
            key += f" {gb.strip()}"
        if laptop and f"{key} laptop" in GPU:
            return f"{key} laptop"
        if key in GPU:
            return key
        if gb and key.rsplit(" ", 1)[0] in GPU:
            return key.rsplit(" ", 1)[0]
        return key
    # GTX xxxx (Ti/Super)
    m = re.search(r"gtx\s*(\d{3,4})\s*(ti)?\s*(super)?", t)
    if m:
        key = f"gtx {m.group(1)}"
        if m.group(2):
            key += " ti"
        if m.group(3):
            key += " super"
        if laptop and f"{key} laptop" in GPU:
            return f"{key} laptop"
        if key in GPU:
            return key
        if num := re.match(r"(.+?)( ti| super)?$", key).group(1):
            if num in GPU:
                return num
        return key
    # Radeon RX xxxx XT/GRE/XTX
    m = re.search(r"rx\s*(\d{4})\s*(xtx|xt|gre|m|s)?\s*(\d{1,2}\s*gb)?", t)
    if m:
        key = f"rx {m.group(1)}"
        suf = m.group(2) or ""
        if suf:
            key += f" {suf}"
        if gb := m.group(3):
            if f"{key} {gb.strip()}" in GPU:
                return f"{key} {gb.strip()}"
        if key in GPU:
            return key
        if suf and key.rsplit(" ", 1)[0] in GPU:
            return key.rsplit(" ", 1)[0]
        return key
    # RX xxx (3-digit: 580/570/480)
    m = re.search(r"rx\s*(\d{3})\s*(xt)?", t)
    if m:
        key = f"rx {m.group(1)}" + (" xt" if m.group(2) else "")
        return key
    # R9 390 etc
    m = re.search(r"(?<![a-z0-9])(r9\s*\d{3}x?)(?![a-z0-9])", t)
    if m:
        return m.group(1)
    # Intel Arc
    m = re.search(r"(?:arc|arc显卡)\s*([ab]\d{3})(?:\s*(\d{1,2})\s*gb)?", t)
    if m:
        key = f"arc {m.group(1)}"
        if m.group(2) and f"{key} {m.group(2)}gb" in GPU:
            return f"{key} {m.group(2)}gb"
        return key
    m = re.search(r"(?<![a-z0-9])([ab]\d{3})(?![a-z0-9])", t)
    if m and f"arc {m.group(1)}" in GPU:
        return f"arc {m.group(1)}"
    # integrated GPUs
    for pat, key in [
        (r"radeon\s*(\d{3,4}m|\d{4}s)(?![a-z0-9])", lambda g: f"radeon {g}"),
        (r"(?<![a-z0-9])(8[4-9]0m|7[68]0m|6[68]0m|610m|8060s|8050s)(?![a-z0-9])", lambda g: f"radeon {g}"),
        (r"vega\s*(\d)", lambda g: f"radeon vega {g}"),
        (r"iris\s*xe", lambda g: "iris xe g7"),
        (r"uhd\s*(graphics\s*)?(\d{3})", lambda g: f"uhd {g.split()[-1]}"),
        (r"hd\s*(graphics\s*)?(\d{4})", lambda g: f"hd {g.split()[-1]}"),
        (r"radeon\s*(graphics|グラフィックス)", lambda g: "radeon graphics"),
        (r"intel\s*(uhd\s*)?graphics|オンボード|内蔵", lambda g: "intel graphics"),
        (r"arc\s*(graphics|グラフィックス)", lambda g: "arc graphics"),
    ]:
        mm = re.search(pat, t)
        if mm:
            g = mm.group(mm.lastindex) if mm.lastindex else mm.group(0)
            return key(g)
    return None


# ---------------- RAM / storage ----------------
def _near(keyword: str, text: str, window: int = 30) -> str:
    i = text.find(keyword)
    return text[max(0, i - 5): i + window] if i >= 0 else ""


def parse_ram(text: str) -> float | None:
    t = norm(text).lower()
    # find regions near メモリ / RAM / memory
    total = 0.0
    found = False
    for m in re.finditer(r"(メモリ|memory|ram)[:：]?\s*(\d{1,3})\s*gb", t):
        total += float(m.group(2)); found = True
    if not found:
        # pattern like "8GBメモリ" or "16GB RAM" or "32GB (32GB x1) メモリ"
        for m in re.finditer(r"(\d{1,3})\s*gb.{0,25}?(メモリ|ram|ddr[345]?)", t):
            total += float(m.group(1)); found = True
    if not found:
        # "メモリ 32GB" / "メモリ：32GB" with text between
        for m in re.finditer(r"(メモリ|memory|ram)[^\d]{0,15}(\d{1,3})\s*gb", t):
            total += float(m.group(2)); found = True
    if not found:
        # "16GB (16GB×1 / シングルチャネル)" / "32GB DDR5" — GB module spec
        m = re.search(r"(\d{1,3})\s*gb\s*[\(（](\d{1,3})\s*gb|(\d{1,3})\s*gb\s*(?=×|ddr|sodimm|dimm|シングル|デュアル)", t)
        if m:
            total += float(m.group(1) or m.group(3)); found = True
    if not found:
        # "DDR4 16GB" or bare "16G" near メモリ
        for m in re.finditer(r"ddr[345]?(?:-\d{3,4})?\s*(\d{1,3})\s*g", t):
            total += float(m.group(1)); found = True
    if not found:
        # used-PC spec style: "16GB/512GB", "8G/256G", "32GB/1TB" — RAM is the smaller first number
        nums = [float(m.group(1) or m.group(3)) * (1024 if m.group(3) else 1)
                for m in re.finditer(r"(?<![a-z0-9])(\d{1,4})\s*(gb|g)(?![a-z0-9])|(?<![a-z0-9])(\d{1,4})\s*(tb|t)(?![a-z0-9])", t)]
        if len(nums) >= 2:
            first = nums[0]
            if first <= 256 and max(nums) >= first * 2:
                total = first; found = True
    if not found:
        # Apple-style "16GB/256GB" = RAM/storage
        m = re.search(r"(\d{1,3})\s*gb\s*/\s*\d{3,4}\s*gb", t)
        if m and re.search(r"m[1-5]|apple|mac", t):
            total = float(m.group(1)); found = True
    if not found:
        # "16GB 512GB SSD" - small value then storage
        m = re.search(r"(\d{1,3})\s*gb[ /,]+\d{3,4}\s*gb\s*(ssd|hdd|nvme|m\.2)", t)
        if m:
            total = float(m.group(1)); found = True
    return total if found and total <= 1024 else None


def parse_storage(text: str) -> tuple[float | None, str | None]:
    """Return (total GB, 'ssd'|'hdd'|'mixed'|None)."""
    t = norm(text).lower()
    vals = []
    kinds = set()
    for m in re.finditer(r"(?<![a-z0-9])(\d{1,4})\s*(tb|gb|g|t)(?![a-z0-9])\s*(ssd|hdd|nvme|m\.2|gen\d|pcie|ufs|emmc)?", t):
        v = float(m.group(1))
        unit = m.group(2)
        if unit.startswith("t"):
            v *= 1024
        kind = m.group(3)
        if kind in ("hdd",):
            kinds.add("hdd")
        elif kind:
            kinds.add("ssd")
        else:
            # near context: check following 12 chars for SSD/HDD hints
            ctx = t[m.end():m.end() + 15]
            if "ssd" in ctx or "nvme" in ctx:
                kinds.add("ssd")
            elif "hdd" in ctx:
                kinds.add("hdd")
        if 64 <= v <= 32768:
            vals.append((v, kind))
    # storage: keyword'd
    for m in re.finditer(r"(ストレージ|storage)[:：]?\s*(\d{3,4})\s*(gb|tb)", t):
        v = float(m.group(2)) * (1024 if m.group(3) == "tb" else 1)
        vals.append((v, "ssd"))
        kinds.add("ssd")
    if not vals:
        return None, None
    total = max(v for v, _ in vals)  # take the largest as primary storage
    k = "mixed" if "ssd" in kinds and "hdd" in kinds else ("ssd" if "ssd" in kinds else ("hdd" if "hdd" in kinds else None))
    return total, k


def parse_vram(text: str) -> float | None:
    t = norm(text).lower()
    m = re.search(r"(?:vram|ビデオメモリ)[:：]?\s*(\d{1,3})\s*gb", t)
    if m:
        return float(m.group(1))
    # "RTX 4060 8GB" pattern handled by GPU table; explicit "8GB" after gpu name
    m = re.search(r"(rtx|rx|gtx|arc)\s*\d{3,4}\s*(?:ti|super|xtx|xt|gre)?\s*(\d{1,2})\s*gb", t)
    if m:
        return float(m.group(2))
    return None


def parse_display(text: str) -> float | None:
    t = norm(text).lower()
    m = re.search(r"(\d{2}\.?\d?)\s*(?:インチ|型|\"|inch)", t)
    if m:
        v = float(m.group(1))
        return v if 7 <= v <= 30 else None
    return None


PERIPHERAL_PAT = re.compile(
    r"キーボード|keyboard|テンキー|number\s*pad|マウスパッド|ゲーミングマウス|gaming\s*mouse|"
    r"ケーブル|cable\b|アダプタ|adapter|変換アダプタ|ハブ|\bhub\b|ヘッドセット|headset|"
    r"webカメラ|ウェブカメラ|webcam|スピーカー|speaker|充電器|charger|ドッキング|"
    r"docking|保護フィルム|フィルム|カバー|バッグ|バックパック|ストラップ|液晶モニタ|"
    r"モニター(?!搭載|付き)|monitor\b|ディスプレイ(?!搭載)|プリンタ|スキャナ|"
    r"ゲームパッド|コントローラー|タッチペン|スタイラス|冷却台|クーラーパッド|"
    r"スタンド|stand\b|マウント|mount\b|ブラケット|bracket|ピンセット|ネジ|screw|"
    r"取り付け|取付|交換用|交換部品|修理用|保護ケース|ケースカバー|インナーケース|"
    r"ルーター|router|アンテナ|antenna|リムーバー|クリーナー|掃除|セット(?!.*搭載)|"
    r"対応品|for\s*mac\s*(mini|studio|pro)|スキンシール|ケーブルボックス|延長コード",
    re.I)
PC_SIGNAL_PAT = re.compile(
    r"パソコン|デスクトップpc|ノートpc|ノートパソコン|ゲーミングpc|ワークステーション|"
    r"ベアボーン|ミニpc|スモールフォーム|スリムタワー|タワー型|ビジネスpc|"
    r"サーバー|ラップトップ|laptop\b|desktop\b|notebook\b|macbook|imac|"
    r"mac\s*mini|mac\s*pro|mac\s*studio|thinkpad|ideapad|thinkcentre|"
    r"optiplex|prodesk|elitedesk|inspiron|xps\b|latitude|precision|"
    r"esprimo|lavie|dynabook|vaio|fmv|fmvs|lets\s*note|surface\b|"
    r"nuc\b|搭載モデル|os搭載|windows11搭載|win11搭載|自作pc|bto",
    re.I)


def parse_specs(text: str, category_hint: str = "") -> dict:
    t = norm(text)
    cpu = match_cpu(t)
    gpu = match_gpu(t)
    ram = parse_ram(t)
    storage, storage_type = parse_storage(t)
    vram = parse_vram(t)
    disp = parse_display(t)
    if not vram and gpu and gpu in GPU:
        vram = GPU[gpu][2] or None
    # category inference
    cat = category_hint
    if not cat:
        if disp:
            cat = "laptop"
        elif gpu and not cpu and gpu in GPU:
            cat = "gpu"
        elif ram and re.search(r"メモリ|memory|(?<!g)ddr[345]", t):
            cat = "ram"
        elif storage and re.search(r"ssd|m\.2|nvme|hdd|ストレージ", t):
            cat = "ssd"
        elif cpu and not PC_SIGNAL_PAT.search(text):
            cat = "cpu"
        elif PC_SIGNAL_PAT.search(text):
            cat = "desktop"
    elif cat == "pc":
        cat = "laptop" if disp else "desktop"
    # demote pc-category to a part when the name is just a bare chip
    if cat in ("desktop", "laptop") and not PC_SIGNAL_PAT.search(text):
        bare = not (ram and storage) and not disp
        if gpu and gpu in GPU and not cpu and bare:
            cat = "gpu"
        elif cpu and not (gpu and gpu in GPU) and bare:
            cat = "cpu"
    if PERIPHERAL_PAT.search(text) and not ((ram and storage) or disp):
        cat = "peripheral"
    return {
        "cpu": cpu, "gpu": gpu, "ram_gb": ram,
        "storage_gb": storage, "storage_type": storage_type,
        "vram_gb": vram, "display": disp,
        "category": cat, "os": ("windows" if re.search(r"win|windows|windows11|win11|win10", t, re.I) else None),
    }
