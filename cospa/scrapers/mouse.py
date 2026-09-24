"""Mouse Computer (mouse-jp.co.jp) — brand -> model -> goods-list items."""
from __future__ import annotations

import re

from ..models import Listing, now_iso
from ..specs import parse_specs
from .base import Scraper

BASE = "https://www.mouse-jp.co.jp"
BRANDS = [
    "/store/brand/g-tune/",
    "/store/brand/nextgear/",
    "/store/brand/daiv/",
    "/store/brand/mouse/",
    "/store/brand/mousepro/",
    "/store/brand/iiyama/",
]


class MouseScraper(Scraper):
    shop = "mouse"

    def run(self, limit_pages: int | None = None) -> list[Listing]:
        model_urls: list[str] = []
        for b in BRANDS:
            try:
                html = self.f.text(BASE + b)
            except Exception:
                continue
            for u in re.findall(r'href="(/store/e/ea\d+/?)"', html):
                if u not in model_urls:
                    model_urls.append(u)
        if limit_pages:
            model_urls = model_urls[:limit_pages]
        out = []
        for u in model_urls:
            try:
                out.extend(self._model(BASE + u))
            except Exception:
                continue
        return out

    def _model(self, url: str) -> list[Listing]:
        html = self.f.text(url)
        soup = self.soup(html)
        out = []
        for item in soup.select("div[class*='block-goods-list-4CD--item'], li[class*='block-goods-list-4CD--item']"):
            l = self._parse_item(item, url, soup)
            if l:
                out.append(l)
        if not out:
            # single-config page fallback
            title = soup.title.get_text(strip=True) if soup.title else url
            price_el = soup.select_one(".goods-price-value, .price-value")
            if price_el:
                m = re.search(r"[\d,]+", price_el.get_text())
                if m:
                    specs = parse_specs(title)
                    out.append(self._listing(title, url, int(m.group(0).replace(",", "")), specs))
        return out

    def _parse_item(self, item, url, soup) -> Listing | None:
        price_el = item.select_one(".goods-price-value")
        if not price_el:
            return None
        m = re.search(r"[\d,]+", price_el.get_text())
        if not m:
            return None
        price = int(m.group(0).replace(",", ""))
        name_el = (item.select_one("[class*='item-name']") or item.select_one("[class*='item-title']")
                   or item.select_one("a"))
        name = name_el.get_text(" ", strip=True) if name_el else ""
        if not name:
            name = (soup.title.get_text(strip=True) if soup.title else url).split("|")[0]
        a = item.select_one("a[href]")
        item_url = a["href"] if a else url
        if item_url.startswith("/"):
            item_url = BASE + item_url
        specs_text = " ".join(s.get_text(" ", strip=True) for s in item.select("[class*='item-spec-item-text']"))
        icons = " ".join(i.get_text(" ", strip=True) for i in item.select("[class*='block-icon-item']"))
        specs = parse_specs(f"{name} {specs_text}")
        cat = "laptop" if re.search(r"ノート|note|laptop|book|モバイル", name) else "desktop"
        in_stock = "在庫切れ" not in item.get_text()
        return Listing(
            shop=self.shop, name=name[:150], url=item_url, category=cat,
            price=price, price_kind="base", effective_price=price,
            condition="new", in_stock=in_stock, purchasable=in_stock,
            stock_note=icons[:80], specs=specs, fetched_at=now_iso(),
        )

    def _listing(self, name, url, price, specs) -> Listing:
        cat = "laptop" if re.search(r"ノート|note|book|モバイル", name) else "desktop"
        return Listing(shop=self.shop, name=name, url=url, category=cat,
                       price=price, price_kind="base", effective_price=price,
                       condition="new", in_stock=True, purchasable=True,
                       stock_note="BTO", specs=specs, fetched_at=now_iso())
