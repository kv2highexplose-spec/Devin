---
name: testing-cospa-dashboard
description: How to run and end-to-end test the cospa-pc Japanese PC-price dashboard (scrapers + analyzer + zero-dep web UI)
---

# Testing the cospa-pc dashboard

## App under test
- Working checkout with real scraped data lives at `/home/ubuntu/repos/cospa-pc/` (the `data/` dir ~80MB is gitignored). `~/repos/Devin` is the code-only PR copy — code is identical but has no data; always serve from the cospa-pc checkout.
- Serve: `python3 run.py serve` (cwd = repo root) → http://localhost:8000. `index.html` and `data/*.json` are re-read per request, but `server.py`/`run.py` code is loaded at process start — restart the server if those files changed (`pkill -f "run.py serve"` then relaunch).

## APIs
- `GET /api/data` — `{generated_at, summary, items[] , verify_generated_at}`; merges `data/verify.json` results into items as `i.verify` keyed by url.
- `GET /api/status` → `{running, log}`; `GET /api/history` → last 500 history.jsonl entries.
- `POST /api/refresh` — **destructive in test env**: launches a full 13-shop re-scrape (requests+Playwright, real external sites, minutes) and `save_listings` rewrites `data/listings.json` + appends `history.jsonl`. Do NOT click the データ更新 button during testing.

## Pipeline commands (safe)
- `python3 run.py analyze` — recomputes `data/analysis.json` from `data/listings.json` only. Safe and useful: it fixes stale analysis (e.g. missing urls) without touching listings/history.
- `run.py scrape` / `run.py verify` hit real shops — avoid during UI testing.

## Useful test tricks
- The dashboard's `<a href="">` on empty-url items opens a duplicate dashboard tab (target=_blank) — a dead link is visually demonstrable.
- Badge rows: verified items to search via the 検索 box — `FRGKB550` (購入確認済), `MH354J` (価格相違). Out-of-stock: filter shop=pc-koubou, uncheck 在庫のみ AND スコアありのみ (OOS items are often unscored) → 在庫なし + dimmed rows.
- `data/verify.json` `results[].url` may be `""` — server merges it onto every empty-url item (`vmap[""]`), and Listing.verify `{}` serializes truthy → 確認不可 on every row. Check badge truthiness carefully.
- Chrome-for-Testing may hold multiple windows on :8000 from earlier sessions — close extras or `browser_console`/read_dom hit the wrong page.

## Devin secrets needed
- None — dashboard and all APIs are unauthenticated on localhost.
