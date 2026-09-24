"""Be-Stock (be-stock.com) — Magento, used PCs with spec blocks and stock flags."""
from __future__ import annotations

import re

from ..models import Listing, now_iso
from ..specs import parse_specs
from .base import Scraper

BASE = "https://www.be-stock.com/shop/"

# series listing paths discovered from the shop nav
SERIES = [
    "desktop/desktop.html",
    "desktop/centre.html",
    "note/t.html", "note/x.html", "note/l.html", "note/e.html",
    "note/p.html", "note/r.html", "note/v.html", "note/edge.html",
    "note/v14-gen4.html",
    "macbook/macbook.html", "macbook/air.html", "macbook/pro.html",
    "feature-list/imperfect-product.html",
    "feature-list/windows11.html",
]


class BeStockScraper(Scraper):
    shop = "be-stock"

    def run(self, limit_pages: int | None = None) -> list[Listing]:
        # Magento session gate: list URLs 404 until a cookie is issued — prime with top page
        self.f.text(BASE + "/")
        out = []
        for s in SERIES:
            out.extend(self._series(s, limit_pages))
        return out

    def _series(self, path: str, limit_pages: int | None) -> list[Listing]:
        out = []
        for p in range(1, (limit_pages or 6) + 1):
            url = f"{BASE}{path}?product_list_limit=100" + (f"&p={p}" if p > 1 else "")
            try:
                html = self.f.text(url)
            except Exception:
                break
            if not html:
                break
            items = self.soup(html).select("li.item.product, li.product-item")
            if not items:
                break
            for it in items:
                l = self._parse(it)
                if l:
                    out.append(l)
            if not re.search(rf'[?&]p={p + 1}\b', html):
                break
        return out

    def _parse(self, it) -> Listing | None:
        a = it.select_one("a.product-item-link")
        if not a:
            return None
        name = " ".join(a.get_text(" ", strip=True).split())
        url = a.get("href", "")
        stock_el = it.select_one("span.stock")
        stock_txt = stock_el.get_text(" ", strip=True) if stock_el else ""
        out_of_stock = bool(it.select_one(".stock.qty-0")) or "在庫切れ" in stock_txt
        in_stock = not out_of_stock and bool(stock_el)
        price_el = it.select_one(".price-box .price, span.price")
        price = None
        if price_el:
            m = re.search(r"[\d,]+", price_el.get_text())
            if m:
                price = int(m.group(0).replace(",", ""))
        spec_parts = []
        for s in it.select("div.product-info-spec-set"):
            t = s.select_one(".type")
            v = s.select_one(".value")
            if t and v:
                spec_parts.append(f"{t.get_text(strip=True)} {v.get_text(strip=True)}")
        cond_el = it.select_one(".itemList .label")
        grade = cond_el.get_text(strip=True) if cond_el else None
        spec_text = " ".join(spec_parts)
        cat = "laptop" if re.search(r"note|thinkpad|macbook|book|ノート|タブレット", (url + name).lower()) else "desktop"
        specs = parse_specs(f"{name} {spec_text}", cat)
        return Listing(
            shop=self.shop, name=name, url=url, category=cat,
            price=price, price_kind="exact", effective_price=price,
            condition="used", condition_grade=grade,
            in_stock=in_stock, purchasable=in_stock,
            stock_note=stock_txt, specs=specs,
            raw={"spec_kv": spec_parts},
            fetched_at=now_iso(),
        )
