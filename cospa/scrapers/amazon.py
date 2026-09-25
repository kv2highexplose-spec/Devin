"""Amazon.co.jp — search pages render product cards via JS (bot-guarded, Playwright only)."""
from __future__ import annotations

import re
import time

from ..models import Listing, now_iso
from ..pwbrowser import browser, rendered_text
from ..specs import parse_specs
from .base import Scraper

BASE = "https://www.amazon.co.jp"
# (query, category_hint, condition)
QUERIES = [
    ("ゲーミングPC", "desktop", "new"),
    ("デスクトップPC", "desktop", "new"),
    ("ミニPC", "desktop", "new"),
    ("ゲーミングノートPC", "laptop", "new"),
    ("ノートパソコン", "laptop", "new"),
    ("中古 デスクトップパソコン", "desktop", "used"),
    ("中古 ノートパソコン", "laptop", "used"),
    ("CPU", "cpu", "new"),
    ("グラフィックボード", "gpu", "new"),
    ("メモリ DDR5", "ram", "new"),
    ("メモリ DDR4", "ram", "new"),
    ("SSD M.2", "ssd", "new"),
    ("中古 グラフィックボード", "gpu", "used"),
]
PAGES_PER_QUERY = 2


class AmazonScraper(Scraper):
    shop = "amazon"

    def run(self, limit_pages: int | None = None) -> list[Listing]:
        pages = limit_pages or PAGES_PER_QUERY
        out: list[Listing] = []
        with browser() as ctx:
            ctx.add_cookies([
                {"name": "i18n-prefs", "value": "JPY", "domain": ".amazon.co.jp", "path": "/"},
                {"name": "lc-acbjp", "value": "ja_JP", "domain": ".amazon.co.jp", "path": "/"},
            ])
            page = ctx.new_page()
            for q, cat, cond in QUERIES:
                for p in range(1, pages + 1):
                    url = f"{BASE}/s?k={self._q(q)}" + (f"&page={p}" if p > 1 else "")
                    try:
                        html = rendered_text(page, url, wait_ms=3000, scroll=2)
                    except Exception:
                        break
                    if not html or "Enter the characters" in html or "unusual traffic" in html:
                        time.sleep(6)
                        continue
                    items = self._parse(html, cat, cond)
                    if not items:
                        break
                    out.extend(items)
                    time.sleep(1.2)
        return out

    def _q(self, q: str) -> str:
        from urllib.parse import quote
        return quote(q)

    def _parse(self, html: str, cat: str, cond: str) -> list[Listing]:
        soup = self.soup(html)
        out = []
        for it in soup.select('div[data-component-type="s-search-result"]'):
            l = self._item(it, cat, cond)
            if l:
                out.append(l)
        return out

    def _item(self, it, cat: str, cond: str) -> Listing | None:
        asin = it.get("data-asin") or ""
        if not asin:
            return None
        title_el = it.select_one("h2 span, h2 a span")
        name = title_el.get_text(" ", strip=True) if title_el else ""
        if not name:
            return None
        sym = it.select_one(".a-price .a-price-symbol")
        if sym and re.search(r"USD|\$|US$|EUR|€|£", sym.get_text()):
            return None  # overseas listing — price is not JPY
        price = None
        whole = it.select_one(".a-price:not(.a-text-price) .a-price-whole")
        if whole:
            m = re.search(r"[\d,]+", whole.get_text())
            if m:
                price = int(m.group(0).replace(",", ""))
        if price is None:
            for off in it.select(".a-price .a-offscreen"):
                if off.find_parent(class_=re.compile(r"a-text-price|a-price-secondary")):
                    continue
                m = re.search(r"[\d,]{3,}", off.get_text())
                if m:
                    price = int(m.group(0).replace(",", ""))
                    if price >= 2000:
                        break
                    price = None
        if not price:
            return None  # no live price -> not purchasable
        url = BASE + f"/dp/{asin}"
        ship_el = it.find(string=re.compile(r"通常配送料無料|送料無料"))
        spec_text = " ".join(it.get_text(" ", strip=True).split())[:600]
        specs = parse_specs(name + " " + spec_text, cat if cat != "new" else "")
        real_cat = specs.get("category") or cat or "other"
        return Listing(
            shop=self.shop, name=name[:150], url=url, category=real_cat,
            price=price, price_kind="listed", effective_price=price,
            shipping=0 if ship_el else None,
            condition=cond, in_stock=True, purchasable=True,
            stock_note="Amazon掲載価格",
            specs=specs, fetched_at=now_iso(),
            raw={"asin": asin},
        )
