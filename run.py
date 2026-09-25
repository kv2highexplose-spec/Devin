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


def export_csv(path: Path | None = None, pc_only: bool = False):
    """Flatten analysis.json into an Excel-friendly CSV (utf-8-sig).
    pc_only: drop non-PC rows (peripherals, unclassified, no-price) for cospa comparison."""
    import csv
    ap = DATA_DIR / "analysis.json"
    if not ap.exists():
        print("run analyze first")
        return
    d = json.loads(ap.read_text())
    vmap = {}
    vp = DATA_DIR / "verify.json"
    if vp.exists():
        for r in json.loads(vp.read_text()).get("results", []):
            if r.get("url"):
                vmap[r["url"]] = r
    out = path or (DATA_DIR / ("export_pc.csv" if pc_only else "export.csv"))
    cols = [
        "製品名", "ショップ", "カテゴリ", "新品・中古", "実売価格", "送料", "実質価格",
        "在庫", "購入可能", "検証済み購入可否", "検証価格", "価格一致",
        "CPU", "CPUスコア", "CPU TDP(W)", "CPU発売年",
        "GPU", "GPUスコア", "GPU TDP(W)", "GPU発売年",
        "RAM(GB)", "ストレージ(GB)", "ストレージ種別", "VRAM(GB)", "画面(型)",
        "CPU点/万円", "GPU点/万円", "VRAM・RAM GB/万円", "RAM GB/万円", "電力効率/万円",
        "割安スコア", "値下げ%", "前回最安値", "フラグ", "OS", "在庫メモ", "価格種別", "URL", "取得日時",
    ]
    def row(i):
        sp = i.get("specs") or {}
        v = vmap.get(i.get("url"), {})
        cond = {"new": "新品", "used": "中古", "outlet": "アウトレット", "junk": "ジャンク"}.get(i.get("condition"), i.get("condition") or "")
        ins = {True: "在庫あり", False: "在庫なし"}.get(i.get("in_stock"), "")
        pur = {True: "可", False: "不可"}.get(i.get("purchasable"), "")
        pnv = {True: "可", False: "不可"}.get(v.get("purchasable_now"), "")
        pm = {True: "一致", False: "不一致"}.get(v.get("price_match"), "")
        return [
            i.get("name"), i.get("shop"), i.get("category"), cond,
            i.get("price"), i.get("shipping"), i.get("effective_price"),
            ins, pur, pnv, v.get("verified_price"), pm,
            sp.get("cpu"), i.get("cpu_score"), i.get("cpu_tdp"), i.get("cpu_year"),
            sp.get("gpu"), i.get("gpu_score"), i.get("gpu_tdp"), i.get("gpu_year"),
            sp.get("ram_gb"), sp.get("storage_gb"), sp.get("storage_type"),
            i.get("vram_gb") or sp.get("vram_gb"), sp.get("display"),
            i.get("cpu_pts_per_man"), i.get("gpu_pts_per_man"), i.get("llm_gb_per_man"),
            i.get("ram_gb_per_man"), i.get("perf_per_yen_w"),
            i.get("deal_score"), i.get("price_drop"), i.get("prev_price"),
            ",".join(i.get("flags") or []), sp.get("os"), i.get("stock_note"),
            i.get("price_kind"), i.get("url"), i.get("fetched_at"),
        ]
    items = d["items"]
    if pc_only:
        items = [i for i in items
                 if i.get("category") not in ("peripheral", "other", "")
                 and (i.get("effective_price") or i.get("price") or 0) >= 1000
                 and i.get("name")]
        items.sort(key=lambda i: (i.get("category") or "", -(i.get("deal_score") or 0),
                                  i.get("effective_price") or i.get("price") or 0))
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for i in items:
            w.writerow(row(i))
    print(f"{len(items)} rows -> {out}")


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
    elif cmd == "csv":
        export_csv(Path(only[0]) if only else None)
    elif cmd in ("csv-pc", "csv_pc"):
        export_csv(Path(only[0]) if only else None, pc_only=True)
    elif cmd == "serve":
        from cospa.dashboard.server import serve
        serve()
    elif cmd == "all":
        analyze(scrape(only))
    else:
        print("usage: run.py [scrape|analyze|verify|serve|all] [shop,shop|limit]")


if __name__ == "__main__":
    main()
