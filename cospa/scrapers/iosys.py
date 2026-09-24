from __future__ import annotations

import re
from urllib.parse import urljoin

from ..models import Listing
from ..specs import parse_specs
from .base import Scraper

BASE = "https://iosys.co.jp"

CATS = {
    "/items/pc/deskpc/desktop": "desktop",
    "/items/pc/notepc": "laptop",
    "/items/gaming": "desktop",
    "/items/pc/tabletpc": "laptop",
}


class IosysScraper(Scraper):
    shop = "iosys"

    def run(self, limit_pages: int | None = None) -> list[Listing]:
        out: list[Listing] = []
        for path, cat in CATS.items():
            out.extend(self._crawl(path, cat, limit_pages))
        return out

    def _crawl(self, path: str, cat: str, limit_pages: int | None):
        out = []
        page = 1
        while True:
            url = f"{BASE}{path}?page={page}" if page > 1 else BASE + path
            html = self.f.text(url)
            if not html:
                break
            batch = self._parse(html, cat)
            out.extend(batch)
            if not batch or (limit_pages and page >= limit_pages) or page > 40:
                break
            if f"page={page + 1}" not in html:
                break
            page += 1
        return out

    def _parse(self, html: str, cat: str):
        soup = self.soup(html)
        out = []
        for li in soup.select("li.item"):
            form = li.select_one("form")
            a = li.find("a", href=True)
            if not form or not a:
                continue

            def val(n):
                el = form.select_one(f'input[name="{n}"]')
                return el.get("value", "") if el else ""

            name = val("name")
            spec = val("spec")
            rank = val("rank")
            price_el = li.select_one(".price p")
            price = None
            if price_el:
                m = re.search(r"[\d,]+", price_el.text)
                if m:
                    price = int(m.group(0).replace(",", ""))
            stock_el = li.select_one(".stock")
            stock = None
            if stock_el:
                m = re.search(r"(\d+)", stock_el.text)
                stock = int(m.group(1)) if m else None
            if not price or not name:
                continue
            sp = parse_specs(f"{name} {spec}", cat)
            in_stock = (stock or 0) > 0
            out.append(Listing(
                shop=self.shop, name=name, url=urljoin(BASE, a["href"]),
                category=cat, price=price, condition="used",
                condition_grade=rank or None,
                in_stock=in_stock, purchasable=in_stock,
                stock_note=f"在庫数:{stock}" if stock is not None else None,
                specs=sp, raw={"spec": spec},
            ))
        return out
