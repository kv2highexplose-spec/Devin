"""Cost-performance metrics and anomaly detection."""
from __future__ import annotations

import math
import statistics
from collections import defaultdict

from .bench import cpu_lookup, gpu_lookup
from .models import Listing, ScoredListing


def _cpu_score(key: str | None):
    e = cpu_lookup(key) if key else None
    return e[0] if e else None


def _gpu_score(key: str | None):
    e = gpu_lookup(key) if key else None
    return e[0] if e else None


def _cpu_tdp(key: str | None):
    e = cpu_lookup(key) if key else None
    return e[1] if e else None


def _gpu_tdp(key: str | None):
    e = gpu_lookup(key) if key else None
    return e[1] if e else None


def _gpu_vram(key: str | None):
    e = gpu_lookup(key) if key else None
    return e[2] if e else None


def _cpu_year(key):
    e = cpu_lookup(key) if key else None
    return e[2] if e else None


def _gpu_year(key):
    e = gpu_lookup(key) if key else None
    return e[3] if e else None


def is_unified(cpu_key: str | None) -> bool:
    return bool(cpu_key and cpu_key.startswith("m"))


def score_listing(l: Listing) -> ScoredListing:
    s = ScoredListing(l)
    specs = l.specs or {}
    cpu_k = specs.get("cpu")
    gpu_k = specs.get("gpu")
    s.cpu_score = _cpu_score(cpu_k)
    s.gpu_score = _gpu_score(gpu_k)
    s.cpu_tdp = _cpu_tdp(cpu_k)
    s.gpu_tdp = _gpu_tdp(gpu_k)
    s.vram_gb = specs.get("vram_gb") or _gpu_vram(gpu_k)
    s.cpu_year = _cpu_year(cpu_k)
    s.gpu_year = _gpu_year(gpu_k)
    s.bench_src = "curated"
    if l.raw.get("shop_bench"):
        try:
            s.bench_src = "shop"
        except Exception:
            pass
    price = l.effective_price or l.price
    if not price:
        return s
    if s.cpu_score:
        s.cpu_pts_per_man = s.cpu_score / price * 10000
    if s.gpu_score:
        s.gpu_pts_per_man = s.gpu_score / price * 10000
    # LLM-usable memory: dedicated VRAM, or unified RAM for Apple
    llm_mem = 0.0
    if s.vram_gb:
        llm_mem = s.vram_gb
    if is_unified(cpu_k) and specs.get("ram_gb"):
        llm_mem = max(llm_mem, specs["ram_gb"] * 0.75)
    if llm_mem:
        s.llm_gb_per_man = llm_mem / price * 10000
    if specs.get("ram_gb"):
        s.ram_gb_per_man = specs["ram_gb"] / price * 10000
    # perf per watt value: use GPU score/TDP when GPU present else CPU
    if s.gpu_score and s.gpu_tdp:
        s.perf_per_yen_w = (s.gpu_score / s.gpu_tdp) / price * 10000 * 1000
    elif s.cpu_score and s.cpu_tdp:
        s.perf_per_yen_w = (s.cpu_score / s.cpu_tdp) / price * 10000 * 1000
    return s


def _perf_of(s: ScoredListing, dim: str) -> float | None:
    if dim == "gpu":
        return s.gpu_score
    if dim == "cpu":
        return s.cpu_score
    if dim == "llm":
        v = s.vram_gb or 0
        if is_unified(s.listing.specs.get("cpu")) and s.listing.specs.get("ram_gb"):
            v = max(v, s.listing.specs["ram_gb"] * 0.75)
        return v or None
    return None


def detect_deals(scored: list[ScoredListing]) -> None:
    """Log-log regression price~perf per (category,condition,dim) group; residual -> deal score."""
    groups: dict[tuple, list[ScoredListing]] = defaultdict(list)
    for s in scored:
        l = s.listing
        if not (l.effective_price or l.price):
            continue
        if l.purchasable is False:
            continue
        if l.category == "peripheral":
            continue
        groups[(l.category, l.condition)].append(s)

    for (cat, cond), items in groups.items():
        for dim in ("gpu", "cpu"):
            pts = [(s, _perf_of(s, dim)) for s in items]
            pts = [(s, p) for s, p in pts if p and p > 0]
            if len(pts) < 8:
                continue
            xs = [math.log(p) for _, p in pts]
            ys = [math.log(s.listing.effective_price or s.listing.price) for s, p in pts]
            mx, my = statistics.fmean(xs), statistics.fmean(ys)
            denom = sum((x - mx) ** 2 for x in xs) or 1e-9
            b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
            a = my - b * mx
            res = [y - (a + b * x) for x, y in zip(xs, ys)]
            sd = statistics.pstdev(res) or 1e-9
            for (s, p), r in zip(pts, res):
                z = r / sd  # negative = cheaper than expected
                ds = -z
                if s.deal_score is None or ds > s.deal_score:
                    s.deal_score = ds
                    if dim == "gpu":
                        s.flags.append("gpu_dim")
                if ds >= 1.5:
                    s.flags.append("underpriced")
                elif ds <= -1.5:
                    s.flags.append("overpriced")


def apply_price_drops(scored: list[ScoredListing]) -> None:
    """Flag items whose current price is a fresh low vs their stored history."""
    try:
        from .store import load_history
        hist = load_history()
    except Exception:
        return
    if not hist:
        return
    latest_ts: dict[str, str] = {}
    for h in hist:
        k = h.get("id")
        if k and h.get("fetched_at", "") > latest_ts.get(k, ""):
            latest_ts[k] = h["fetched_at"]
    prev_min: dict[str, float] = {}
    for h in hist:
        p = h.get("effective_price") or h.get("price")
        k = h.get("id")
        if not p or not k:
            continue
        if h.get("fetched_at", "") >= latest_ts.get(k, ""):
            continue  # skip the latest snapshot — we compare against older prices
        prev_min[k] = min(prev_min.get(k, p), p)
    for s in scored:
        l = s.listing
        cur = l.effective_price or l.price
        if not cur:
            continue
        pm = prev_min.get(l.id)
        if pm and cur < pm * 0.95:
            s.price_drop = round((pm - cur) / pm * 100, 1)
            s.prev_price = pm
            s.flags.append("price_drop")


def summarize(scored: list[ScoredListing]) -> dict:
    items = [s for s in scored if (s.listing.effective_price or s.listing.price)]
    by_shop = defaultdict(int)
    by_cat = defaultdict(int)
    in_stock = 0
    for s in items:
        by_shop[s.listing.shop] += 1
        by_cat[s.listing.category] += 1
        if s.listing.in_stock:
            in_stock += 1
    return {
        "total": len(items), "in_stock": in_stock,
        "shops": dict(by_shop), "categories": dict(by_cat),
    }
