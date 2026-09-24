"""NTT-X Store / OCN shop (nttxstore.jp) — Unitcom engine, JS-rendered list."""
from __future__ import annotations

import re
import time
from urllib.parse import quote

from bs4 import BeautifulSoup

from ..models import Listing, now_iso
from ..pwbrowser import browser
from ..specs import parse_specs
from .base import Scraper

BASE = "https://nttxstore.jp"
QUERIES = [
    ("RTX", "gpu"), ("Radeon", "gpu"), ("Core i7", None), ("Ryzen", None),
    ("ノートPC", "laptop"), ("デスクトップ", "desktop"), ("ミニPC", "desktop"),
    ("メモリ", "memory"), ("SSD", "ssd"), ("マザーボード", "motherboard"),
    ("電源", "psu"),
]
PAGES_PER_QUERY = 5


class NttxScraper(Scraper):
    shop = "nttx"

    def run(self, limit_pages: int | None = None) -> list[Listing]:
        pages = limit_pages or PAGES_PER_QUERY
        out = []
        with browser() as ctx:
            page = ctx.new_page()
            for q, cat in QUERIES:
                for p in range(1, pages + 1):
                    url = f"{BASE}/shop/goods/search.aspx?search=x&ct=&keyword={quote(q)}&p={p}&ps=20&stock_flg=1"
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=45000)
                        page.wait_for_timeout(2200)
                        html = page.content()
                    except Exception:
                        break
                    items = self._parse(html, cat)
                    if not items:
                        break
                    out.extend(items)
                    time.sleep(0.8)
        return out

    def _parse(self, html: str, cat: str | None) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        out = []
        for li in soup.select("li.block-thumbnail-t--item"):
            a = li.select_one("a[href*='/shop/g/']")
            name_el = li.select_one(".block-thumbnail-t--goods-name")
            price_el = li.select_one(".block-thumbnail-t--price")
            model_el = li.select_one(".block-thumbnail-t--goods-model-number")
            if not (a and name_el and price_el):
                continue
            m = re.search(r"[\d,]{3,}", price_el.get_text())
            if not m:
                continue
            price = int(m.group(0).replace(",", ""))
            name = " ".join(name_el.get_text(" ", strip=True).split())
            model = model_el.get_text(" ", strip=True) if model_el else ""
            url = a.get("href", "")
            if url.startswith("/"):
                url = BASE + url
            specs = parse_specs(f"{name} {model}")
            real_cat = cat or specs.get("category") or "other"
            specs.setdefault("category", real_cat)
            stock_el = li.select_one(".block-thumbnail-t--stock")
            stock_txt = stock_el.get_text(strip=True) if stock_el else ""
            in_stock = "在庫切れ" not in stock_txt and "売り切れ" not in stock_txt
            out.append(Listing(
                shop=self.shop, name=name[:150], url=url, category=real_cat,
                price=price, price_kind="listed", effective_price=price,
                condition="used" if "中古" in name else "new",
                in_stock=in_stock, purchasable=in_stock,
                stock_note=stock_txt[:60] or "list",
                specs=specs, fetched_at=now_iso(),
            ))
        return out
