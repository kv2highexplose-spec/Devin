from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))


def now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


@dataclass
class Listing:
    """One purchasable product seen on a shop page."""
    shop: str                 # 'dospara' | 'iosys' | 'kakaku' | ...
    name: str
    url: str
    category: str             # desktop|laptop|minipc|cpu|gpu|ram|ssd|hdd|mb|psu|other
    price: int | None = None
    price_kind: str = "exact"          # exact|base|from   (BTO base-config price = base/from)
    shipping: int | None = None        # yen, None = unknown
    effective_price: int | None = None # price + shipping - auto discounts (best known total)
    condition: str = "new"             # new|used|outlet|junk|openbox
    condition_grade: str | None = None # e.g. '中古Bランク'
    in_stock: bool | None = None
    purchasable: bool | None = None    # buy button usable / orderable now
    stock_note: str | None = None      # '翌日出荷','残りわずか','受注生産'...
    specs: dict = field(default_factory=dict)  # cpu,gpu,ram_gb,storage_gb,storage_type,vram_gb,display,os
    raw: dict = field(default_factory=dict)    # extra source-specific fields
    verify: dict = field(default_factory=dict) # deep-verification results
    fetched_at: str = field(default_factory=now_iso)
    source_layer: str = "shop"         # shop|aggregator
    id: str = ""

    def __post_init__(self):
        if not self.id:
            base = f"{self.shop}|{self.url}|{self.name}"
            self.id = hashlib.sha1(base.encode()).hexdigest()[:16]
        if self.effective_price is None and self.price is not None:
            self.effective_price = self.price + (self.shipping or 0)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Listing":
        return cls(**d)


@dataclass
class ScoredListing:
    """Listing + analysis metrics, ready for the dashboard."""
    listing: Listing
    cpu_score: float | None = None
    gpu_score: float | None = None
    bench_src: str | None = None         # shop-provided bench (e.g. dospara) if any
    cpu_tdp: float | None = None
    gpu_tdp: float | None = None
    vram_gb: float | None = None
    cpu_year: int | None = None
    gpu_year: int | None = None
    cpu_pts_per_man: float | None = None   # bench points per 10k JPY
    gpu_pts_per_man: float | None = None
    llm_gb_per_man: float | None = None    # usable VRAM(unified incl.) per 10k JPY
    ram_gb_per_man: float | None = None
    perf_per_yen_w: float | None = None    # (score/tdp) per 10k JPY
    deal_score: float | None = None        # -residual z vs price/perf curve (higher=cheaper)
    price_drop: float | None = None        # % below previous minimum observed price
    prev_price: float | None = None        # previous minimum observed price
    flags: list = field(default_factory=list)  # ['underpriced','sale','unverifiable',...]

    def to_dict(self) -> dict:
        d = self.listing.to_dict()
        for k in ("cpu_score", "gpu_score", "bench_src", "cpu_tdp", "gpu_tdp",
                  "vram_gb", "cpu_year", "gpu_year", "cpu_pts_per_man",
                  "gpu_pts_per_man", "llm_gb_per_man", "ram_gb_per_man",
                  "perf_per_yen_w", "deal_score", "price_drop", "prev_price", "flags"):
            d[k] = getattr(self, k)
        return d
