"""Janpara (janpara.co.jp) — used PC shop; search results need JS render."""
from __future__ import annotations

import re
import time
from urllib.parse import quote

from bs4 import BeautifulSoup

from ..models import Listing, now_iso
from ..pwbrowser import browser
from ..specs import parse_specs
from .base import Scraper

BASE = "https://www.janpara.co.jp"
QUERIES = [
    ("ノートPC", "laptop"),
    ("デスクトップ", "desktop"),
    ("ThinkPad", "laptop"),
    ("Core i7", None),
    ("Ryzen", None),
    ("GeForce RTX", "gpu"),
    ("メモリ", "memory"),
    ("SSD", "ssd"),
]
PAGES_PER_QUERY = 6


class JanparaScraper(Scraper):
    shop = "janpara"

    def run(self, limit_pages: int | None = None) -> list[Listing]:
        pages = limit_pages or PAGES_PER_QUERY
        out = []
        with browser() as ctx:
            page = ctx.new_page()
            for q, cat in QUERIES:
                for p in range(1, pages + 1):
                    url = f"{BASE}/sale/search/result/?q={quote(q)}&LINE=24&ORDER=4&PAGE={p}"
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=45000)
                        page.wait_for_timeout(2200)
                        html = page.content()
                    except Exception:
                        break
                    items = self._parse(html)
                    if not items:
                        break
                    out.extend(items)
                    time.sleep(0.8)
        return out

    def _parse(self, html: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        out = []
        for div in soup.select("div.search_item_s"):
            a = div.select_one("a.search_itemlink")
            name_el = div.select_one(".search_itemname")
            price_el = div.select_one(".item_amount")
            cond_el = div.select_one(".search_itemcondition")
            if not (a and name_el and price_el):
                continue
            m = re.search(r"[\d,]+", price_el.get_text())
            if not m:
                continue
            price = int(m.group(0).replace(",", ""))
            name = " ".join(name_el.get_text(" ", strip=True).split())
            href = a.get("href", "")
            url = BASE + href if href.startswith("/") else href
            url = re.sub(r"&amp;?", "&", url)
            stock_txt = ""
            st = div.select_one(".search_itemprice div")
            if st:
                stock_txt = st.get_text(strip=True)
            stock_m = re.search(r"(\d+)\s*個の在庫", stock_txt)
            in_stock = bool(stock_m and int(stock_m.group(1)) > 0) or "在庫" in stock_txt
            cond = "used" if cond_el and "中古" in cond_el.get_text() else "new"
            specs = parse_specs(name)
            cat = specs.get("category") or ("laptop" if re.search(r"ノート|book|Pad$", name) else "desktop")
            out.append(Listing(
                shop=self.shop, name=name[:150], url=url, category=cat,
                price=price, price_kind="from", effective_price=price,
                condition=cond, in_stock=in_stock, purchasable=in_stock,
                stock_note=stock_txt[:60], specs=specs, fetched_at=now_iso(),
            ))
        return out
