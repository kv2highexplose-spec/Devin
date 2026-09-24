#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from cospa import scrapers
from cospa.metrics import detect_deals, score_listing, summarize
from cospa.models import Listing, now_iso
from cospa.store import save_listings, DATA_DIR


def scrape(only=None, limit_pages=None):
    items = []
    for name, cls in scrapers.discover().items():
        if only and name not in only:
            continue
        try:
            s = cls()
            got = s.run(**({} if limit_pages is None else {}))
            print(f"[{name}] {len(got)} items", flush=True)
            items.extend(got)
        except Exception as e:
            print(f"[{name}] FAILED: {e}", flush=True)
    save_listings(items)
    print(f"total {len(items)} -> {DATA_DIR/'listings.json'}")
    return items


def reparse():
    """Re-run the (improved) spec parser on stored listings' name+raw text."""
    import cospa.store as store
    from cospa.specs import parse_specs
    items = [Listing.from_dict(d) for d in store.load_listings()]
    n = 0
    for l in items:
        spec_keys = {"spec", "spec_kv", "spec_table", "series"}
        extra = " ".join(str(v) for k, v in (l.raw or {}).items() if k in spec_keys and isinstance(v, (str, int, float)))
        text = f"{l.name} {extra}"
        sp = parse_specs(text, category_hint="")
        if not sp.get("category"):
            sp["category"] = {"memory": "ram", "mb": "motherboard", "mobo": "motherboard"}.get(l.category, l.category)
        # keep scraper-provided fields
        for k in ("cpu_score_src", "gpu_score_src"):
            if (l.specs or {}).get(k):
                sp[k] = l.specs[k]
        if sp != l.specs:
            n += 1
        l.specs = sp
        if sp.get("category"):
            l.category = sp["category"]
    store.save_listings(items)
    print(f"reparsed {n}/{len(items)} listings")


def analyze(items: list[Listing] | None = None):
    if items is None:
        items = [Listing.from_dict(d) for d in __import__("cospa.store", fromlist=["load_listings"]).load_listings()]
    scored = [score_listing(l) for l in items]
    detect_deals(scored)
    from cospa.metrics import apply_price_drops
    apply_price_drops(scored)
    out = {
        "generated_at": now_iso(),
        "summary": summarize(scored),
        "items": [s.to_dict() for s in scored],
    }
    (DATA_DIR / "analysis.json").write_text(json.dumps(out, ensure_ascii=False))
    print(f"analyzed {len(items)} -> {DATA_DIR/'analysis.json'}")
    return out


def verify(limit: int = 60):
    """Re-check top deals on their real product pages (price/stock/cart button)."""
    from cospa.verify import verify_listing
    from cospa.http import Fetcher

    raw = (DATA_DIR / "analysis.json")
    if not raw.exists():
        print("run analyze first")
        return
    d = json.loads(raw.read_text())
    deals = [i for i in d["items"] if i.get("purchasable") and i.get("deal_score")]
    deals.sort(key=lambda x: -x.get("deal_score", 0))
    # spread across shops: top-N per shop to avoid one shop hogging
    picked, per = [], {}
    for i in deals:
        s = i["shop"]
        if s == "kakaku":
            continue  # aggregator, not a checkout page
        if per.get(s, 0) >= max(4, limit // 8):
            continue
        per[s] = per.get(s, 0) + 1
        picked.append(i)
        if len(picked) >= limit:
            break
    f = Fetcher()
    results = []
    for idx, l in enumerate(picked):
        v = verify_listing(f, l)
        v.update({"url": l["url"], "name": l.get("name", "")[:90],
                  "list_price": l.get("effective_price") or l.get("price")})
        results.append(v)
        print(f"[{idx+1}/{len(picked)}] {v['shop']:<10} stock={v.get('in_stock')} cart={v.get('cart_enabled')} "
              f"price={v.get('verified_price')} match={v.get('price_match')} | {v.get('name','')[:40]}", flush=True)
    (DATA_DIR / "verify.json").write_text(json.dumps({
        "generated_at": now_iso(), "results": results}, ensure_ascii=False, indent=1))
    ok = sum(1 for r in results if r.get("purchasable_now") and r.get("price_match") is not False)
    print(f"verified {len(results)}: {ok} confirmed purchasable at listed price")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    only = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    if cmd == "scrape":
        scrape(only)
    elif cmd == "reparse":
        reparse()
        analyze()
    elif cmd == "analyze":
        analyze()
    elif cmd == "verify":
        verify(int(only[0]) if only else 60)
    elif cmd == "serve":
        from cospa.dashboard.server import serve
        serve()
    elif cmd == "all":
        analyze(scrape(only))
    else:
        print("usage: run.py [scrape|analyze|verify|serve|all] [shop,shop|limit]")


if __name__ == "__main__":
    main()
