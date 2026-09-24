"""PC Koubou (pc-koubou.jp) — search.php renders items via JS (Playwright)."""
from __future__ import annotations

import re
import time
from urllib.parse import quote

from bs4 import BeautifulSoup

from ..models import Listing, now_iso
from ..pwbrowser import browser
from ..specs import parse_specs
from .base import Scraper

BASE = "https://www.pc-koubou.jp"
# (query, category, used_filter)
QUERIES = [
    ("LEVEL", "desktop", "0"),
    ("ゲーミング", "desktop", "0"),
    ("ノートパソコン", "laptop", "0"),
    ("クリエイターパソコン", "desktop", "0"),
    ("ビジネスPC", "desktop", "0"),
    ("RTX", "gpu", "0"),
    ("Radeon", "gpu", "0"),
    ("Core i", "cpu", "0"),
    ("Ryzen", "cpu", "0"),
    ("メモリ", "memory", "0"),
    ("SSD", "ssd", "0"),
    ("ThinkPad", "laptop", "1"),
    ("ノートパソコン", "laptop", "1"),
    ("デスクトップパソコン", "desktop", "1"),
    ("パソコン", None, "1"),
]
PAGES_PER_QUERY = 4


class PcKoubouScraper(Scraper):
    shop = "pc-koubou"

    def run(self, limit_pages: int | None = None) -> list[Listing]:
        pages = limit_pages or PAGES_PER_QUERY
        out = []
        with browser() as ctx:
            page = ctx.new_page()
            for q, cat, used in QUERIES:
                for p in range(1, pages + 1):
                    url = (f"{BASE}/user_data/search.php?q={quote(q)}&s5[]={used}"
                           f"&limit=60&sort=number33&p={p}")
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=45000)
                        page.wait_for_timeout(2400)
                        html = page.content()
                    except Exception:
                        break
                    items = self._parse(html, cat, used)
                    if not items:
                        break
                    out.extend(items)
                    time.sleep(0.8)
        return out

    def _parse(self, html: str, cat: str | None, used: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        out = []
        for div in soup.select("div.search-result"):
            l = self._item(div, cat, used)
            if l:
                out.append(l)
        return out

    def _item(self, div, cat, used) -> Listing | None:
        a = div.select_one("a[href*='detail.php?product_id=']")
        name_el = div.select_one("p.name")
        price_el = div.select_one(".price--notax .price--num, .price--num")
        if not (a and name_el and price_el):
            return None
        m = re.search(r"[\d,]{3,}", price_el.get_text())
        if not m:
            return None
        price = int(m.group(0).replace(",", ""))
        name = " ".join(name_el.get_text(" ", strip=True).split())
        href = a.get("href", "")
        url = BASE + href if href.startswith("/") else href
        spec_text = " ".join(s.get_text(" ", strip=True) for s in div.select(".spec, .spec-opt, .spec-area"))
        specs = parse_specs(f"{name} {spec_text}")
        cpu_score = div.select_one(".score-cpu dd")
        gpu_score = div.select_one(".score-gpu dd")
        extra = {}
        if cpu_score and re.search(r"\d+", cpu_score.get_text()):
            extra["cpu_score_src"] = int(re.search(r"\d[\d,]*", cpu_score.get_text()).group(0).replace(",", ""))
        if gpu_score and re.search(r"\d+", gpu_score.get_text()):
            extra["gpu_score_src"] = int(re.search(r"\d[\d,]*", gpu_score.get_text()).group(0).replace(",", ""))
        specs.update(extra)
        stock_el = div.select_one("p.stock")
        stock_txt = stock_el.get_text(strip=True) if stock_el else ""
        soldout = "soldout" in (stock_el.get("class") or []) if stock_el else False
        in_stock = not soldout and "在庫切れ" not in stock_txt
        cond = "used" if used == "1" or "中古" in name else "new"
        real_cat = cat or specs.get("category") or "other"
        if real_cat in ("laptop", "desktop"):
            specs.setdefault("category", real_cat)
        return Listing(
            shop=self.shop, name=name[:150], url=url, category=real_cat,
            price=price, price_kind="notax", effective_price=price,
            condition=cond, in_stock=in_stock, purchasable=in_stock,
            stock_note=stock_txt[:60] or "list",
            specs=specs, fetched_at=now_iso(),
        )
