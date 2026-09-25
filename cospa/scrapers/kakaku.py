from __future__ import annotations

import re

from ..models import Listing
from ..specs import parse_specs
from .base import Scraper

BASE = "https://kakaku.com"

CATS = {
    "/pc/cpu/": ("cpu", 14),
    "/pc/videocard/": ("gpu", 15),
    "/pc/pc-memory/": ("ram", 6),
    "/pc/ssd/": ("ssd", 6),
    "/pc/hdd-35inch/": ("hdd", 4),
    "/pc/motherboard/": ("mb", 5),
    "/pc/power-supply/": ("psu", 3),
    "/pc/desktop-pc/": ("desktop", 10),
    "/pc/notebook-pc/": ("laptop", 15),
}


class KakakuScraper(Scraper):
    shop = "kakaku"

    def __init__(self, fetcher=None):
        super().__init__(fetcher)
        self.f.encoding = "cp932"

    def run(self, limit_pages: int | None = None) -> list[Listing]:
        out: list[Listing] = []
        for path, (cat, maxpg) in CATS.items():
            out.extend(self._crawl(path, cat, limit_pages or maxpg))
        return out

    def _crawl(self, path: str, cat: str, maxpg: int):
        out = []
        for pg in range(1, maxpg + 1):
            url = f"{BASE}{path}itemlist.aspx" + (f"?pdf_pg={pg}" if pg > 1 else "")
            html = self.f.text(url)
            if not html:
                break
            batch = self._parse(html, cat)
            out.extend(batch)
            if not batch or len(batch) < 40:
                break
        return out

    def _parse(self, html: str, cat: str):
        soup = self.soup(html)
        out = []
        for a in soup.select("a.ckitanker"):
            row = a.find_parent("tr", class_="tr-border")
            if not row:
                continue
            nxt = row.find_next_sibling("tr", class_="tr-border")
            if not nxt:
                continue
            name = a.get_text(" ", strip=True)
            name = re.sub(r"^\S+　", "", name).strip()  # drop maker prefix cell text
            url = a.get("href", "")
            price_el = nxt.select_one("li.pryen a")
            price = None
            if price_el:
                m = re.search(r"[\d,]+", price_el.text)
                if m:
                    price = int(m.group(0).replace(",", ""))
            shop_el = nxt.select_one("li.prshop")
            shop_note = shop_el.get_text(" ", strip=True) if shop_el else None
            if not name or not url:
                continue
            spec_text = name + " " + nxt.get_text(" ", strip=True)[:300]
            sp = parse_specs(spec_text, cat)
            out.append(Listing(
                shop=self.shop, name=name, url=url,
                category=cat, price=price,
                condition="new",
                in_stock=None, purchasable=None,
                stock_note=f"最安ショップ:{shop_note}" if shop_note else None,
                specs=sp,
                source_layer="aggregator",
                raw={"kakaku_shop": shop_note},
            ))
        return out
