from __future__ import annotations

import json
from pathlib import Path

from .models import Listing, now_iso

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LISTINGS = DATA_DIR / "listings.json"
SHOPS_DIR = DATA_DIR / "shops"
HISTORY = DATA_DIR / "history.jsonl"


def save_listings(items: list[Listing]) -> Path:
    """Persist per-shop snapshot files then merge into listings.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SHOPS_DIR.mkdir(parents=True, exist_ok=True)
    by_shop: dict[str, list[Listing]] = {}
    for i in items:
        by_shop.setdefault(i.shop, []).append(i)
    for shop, lst in by_shop.items():
        (SHOPS_DIR / f"{shop}.json").write_text(json.dumps(
            {"generated_at": now_iso(), "items": [i.to_dict() for i in lst]},
            ensure_ascii=False))
    all_items = load_all_items()
    snap = {"generated_at": now_iso(), "count": len(all_items), "items": all_items}
    LISTINGS.write_text(json.dumps(snap, ensure_ascii=False))
    with HISTORY.open("a") as f:
        for i in items:
            f.write(json.dumps({
                "id": i.id, "shop": i.shop, "name": i.name, "url": i.url,
                "price": i.price, "effective_price": i.effective_price,
                "in_stock": i.in_stock, "purchasable": i.purchasable,
                "fetched_at": i.fetched_at,
            }, ensure_ascii=False) + "\n")
    return LISTINGS


def load_all_items() -> list[dict]:
    items = []
    if SHOPS_DIR.exists():
        for p in sorted(SHOPS_DIR.glob("*.json")):
            try:
                items.extend(json.loads(p.read_text())["items"])
            except Exception:
                continue
    return items


def load_listings() -> list[dict]:
    if not LISTINGS.exists():
        return load_all_items()
    return json.loads(LISTINGS.read_text())["items"]


def load_history() -> list[dict]:
    if not HISTORY.exists():
        return []
    return [json.loads(l) for l in HISTORY.read_text().splitlines() if l.strip()]
