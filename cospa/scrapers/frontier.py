"""Frontier BTO direct (frontier-direct.jp) — single server-rendered catalog page."""
from __future__ import annotations

import re

from ..models import Listing, now_iso
from ..specs import parse_specs
from .base import Scraper

URL = "https://www.frontier-direct.jp/direct/goods/search.aspx?min_price=0&seq=nd&search=F&ismodesmartphone=P&sort=1"


class FrontierScraper(Scraper):
    shop = "frontier"

    def run(self, limit_pages: int | None = None) -> list[Listing]:
        html = self.f.text(URL)
        out = []
        for card in self.soup(html).select("div.iw-goods"):
            l = self._parse_card(card)
            if l:
                out.append(l)
        return out

    def _parse_card(self, card) -> Listing | None:
        name_el = card.select_one("h3.uk-card-title")
        a = card.select_one("a.iw-goods-img")
        price_el = card.select_one(".iw-price-default .iw-number")
        if not (name_el and price_el):
            return None
        name = name_el.get_text(strip=True)
        catch = card.select_one(".iw-catch-copy")
        title = f"{name} {catch.get_text(strip=True)}" if catch else name
        price = int(re.sub(r"[^\d]", "", price_el.get_text()))
        url = "https://www.frontier-direct.jp" + a["href"] if a else URL
        stock_attr = (card.get("iw-stock") or "").strip()
        stock_txt = ""
        st = card.select_one(".iw-stock")
        if st:
            stock_txt = st.get_text(strip=True)
        stock = stock_txt or stock_attr
        sold_out = stock.startswith("×") or "完売" in stock or "売り切れ" in stock
        in_stock = not sold_out
        specs_text = " ".join(li.get_text(" ", strip=True) for li in card.select(".iw-goods-comment-1 li"))
        specs = parse_specs(f"{title} {specs_text}", "desktop")
        cart_ok = bool(card.select_one("a.iw-button-cart")) and in_stock
        return Listing(
            shop=self.shop, name=title, url=url, category="desktop",
            price=price, price_kind="exact", effective_price=price,
            condition="new", in_stock=in_stock, purchasable=cart_ok,
            stock_note=stock, specs=specs,
            raw={"series": (a or {}).get("data-category") if a else None},
            fetched_at=now_iso(),
        )
