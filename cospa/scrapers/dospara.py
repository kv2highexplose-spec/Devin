from __future__ import annotations

import re
from urllib.parse import urljoin

from ..models import Listing
from ..specs import parse_specs
from .base import Scraper

BASE = "https://www.dospara.co.jp"
AJAX = BASE + "/on/demandware.store/Sites-dospara-Site/ja_JP/Search-ShowAjax"

# cgid -> (normalized category, condition)
CGIDS = {
    "gamepc": ("desktop", "new"),
    "desktop": ("desktop", "new"),
    "note": ("laptop", "new"),
    "minipc": ("minipc", "new"),
    "SBR1391": ("desktop", "used"),
    "SBR1392": ("laptop", "used"),
    "SBR1514": ("desktop", "used"),
    "SBR1795": ("laptop", "used"),
    "SBR1902": ("desktop", "junk"),
    "SBR1903": ("laptop", "junk"),
    "SBR1517": ("cpu", "used"),
    "SBR1518": ("ram", "used"),
    "SBR1522": ("gpu", "used"),
    "SBR1523": ("other", "used"),
    "SBR1960": ("other", "used"),
    "SBR247": ("other", "outlet"),
    "SBR1961": ("laptop", "used"),
}


class DosparaScraper(Scraper):
    shop = "dospara"

    def run(self, limit_pages: int | None = None) -> list[Listing]:
        items: list[Listing] = []
        for cgid, (cat, cond) in CGIDS.items():
            got = self._crawl(cgid, cat, cond, limit_pages)
            items.extend(got)
        return items

    def _crawl(self, cgid: str, cat: str, cond: str, limit_pages: int | None):
        out: list[Listing] = []
        start, sz = 0, 96
        while True:
            url = f"{AJAX}?cgid={cgid}&start={start}&sz={sz}"
            html = self.f.text(url)
            if not html:
                break
            batch, total = self._parse(html, cat, cond)
            out.extend(batch)
            start += sz
            if not batch or start >= total or (limit_pages and start // sz >= limit_pages):
                break
            if start > 2000:
                break
        return out

    def _parse(self, html: str, cat: str, cond: str):
        soup = self.soup(html)
        mt = soup.select_one(".p-products-all-item-search__number")
        total = int(mt.text.replace(",", "").strip()) if mt else 0
        items = []
        for it in soup.select(".p-products-all-item__item"):
            try:
                pid = it.select_one("input.productId")
                name_el = it.select_one("input.productName")
                name = name_el.get("value", "").strip() if name_el else ""
                link = it.select_one('a[href$=".html"]')
                url = urljoin(BASE, link["href"]) if link and link.get("href") else ""
                price_el = it.select_one(".p-products-all-item-product__number")
                price = None
                if price_el:
                    m = re.search(r"[\d,]+", price_el.text)
                    if m:
                        price = int(m.group(0).replace(",", ""))
                box = it.select_one(".p-products-all-item-product__price--box")
                is_from = bool(box and "～" in box.text)
                ship_el = it.select_one('[class*="shipment"]')
                ship_note = ship_el.text.strip() if ship_el else None
                spec = {}
                for tr in it.select(".p-products-all-item-product__spec table tr"):
                    th, td = tr.find("th"), tr.find("td")
                    if th and td:
                        spec[th.text.strip()] = td.text.strip()
                spec_text = " ".join(f"{k} {v}" for k, v in spec.items())
                sp = parse_specs(f"{name} {spec_text}", cat)
                bench = spec.get("ベンチマーク")
                in_stock = bool(ship_note and "出荷" in ship_note)
                purchasable = in_stock
                actual_cat = cat
                if cat == "desktop" and sp.get("display"):
                    actual_cat = "laptop"
                items.append(Listing(
                    shop=self.shop, name=name, url=url,
                    category=actual_cat, price=price,
                    price_kind="base" if is_from else "exact",
                    condition=cond,
                    in_stock=in_stock if ship_note else None,
                    purchasable=purchasable if ship_note else None,
                    stock_note=ship_note,
                    specs=sp,
                    raw={"pid": pid["value"] if pid else None,
                         "shop_bench": bench, "spec_table": spec},
                ))
            except Exception:
                continue
        return items, total
