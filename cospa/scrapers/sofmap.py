"""Sofmap (sofmap.com) — product_list_parts.aspx is server-rendered (Shift_JIS)."""
from __future__ import annotations

import re

from ..models import Listing, now_iso
from ..specs import parse_specs
from .base import Scraper

BASE = "https://www.sofmap.com"
GIDS = [
    ("001010110", "laptop"),    # ノートPC
    ("001010150", "desktop"),   # デスクトップ
    ("001010160", "laptop"),    # Macノート
    ("001010170", "desktop"),   # Macデスクトップ
    ("001010120", "laptop"),    # Surface
    ("001020011", "laptop"),    # ゲーミングノート
    ("001020012", "desktop"),   # ゲーミングデスクトップ
    ("001030010", "cpu"),
    ("001030020", "motherboard"),
    ("001030030", "memory"),
    ("001030040", "ssd"),
    ("001030060", "gpu"),
    ("001030070", "psu"),
]
PAGES_PER_GID = 8


class SofmapScraper(Scraper):
    shop = "sofmap"

    def __init__(self, fetcher=None):
        super().__init__(fetcher)
        self.f.encoding = "shift_jis"

    def run(self, limit_pages: int | None = None) -> list[Listing]:
        pages = limit_pages or PAGES_PER_GID
        out = []
        for gid, cat in GIDS:
            for p in range(1, pages + 1):
                url = (f"{BASE}/product_list_parts.aspx?gid={gid}&is_page=serch_result"
                       f"&pno={p}&styp=p_srt&stk_flg=1&product_type=ALL&dispcnt=100&order_by=DEFAULT")
                try:
                    html = self.f.text(url)
                except Exception:
                    break
                if not html:
                    break
                items = self._parse(html, cat)
                if not items:
                    break
                out.extend(items)
        return out

    def _parse(self, html: str, cat: str) -> list[Listing]:
        soup = self.soup(html)
        out = []
        for li in soup.select("#change_style_list > li, ul.product_list > li"):
            l = self._item(li, cat)
            if l:
                out.append(l)
        return out

    def _item(self, li, cat: str) -> Listing | None:
        a = li.select_one("a.product_name")
        price_el = li.select_one("span.price strong, span.price")
        if not (a and price_el):
            return None
        m = re.search(r"[\d,]{3,}", price_el.get_text())
        if not m:
            return None
        price = int(m.group(0).replace(",", ""))
        name = " ".join(a.get_text(" ", strip=True).split())
        url = a.get("href", "")
        if url.startswith("/"):
            url = BASE + url
        stock_el = li.select_one("span.stock, span.ic.stock")
        stock_txt = stock_el.get_text(strip=True) if stock_el else ""
        in_stock = "在庫切れ" not in stock_txt and "完売" not in stock_txt
        date_el = li.select_one("span.date")
        date_txt = date_el.get_text(strip=True) if date_el else ""
        cond_el = li.select_one(".item_label, .used_box a")
        cond_txt = cond_el.get_text(strip=True) if cond_el else ""
        cond = "used" if ("中古" in name or "中古" in cond_txt or "USED" in cond_txt) else "new"
        specs = parse_specs(name)
        real_cat = cat if cat else specs.get("category") or "other"
        if cat in ("laptop", "desktop") and specs.get("category") not in ("laptop", "desktop"):
            pass  # keep gid-based category for PCs
        specs.setdefault("category", real_cat)
        return Listing(
            shop=self.shop, name=name[:150], url=url, category=real_cat,
            price=price, price_kind="listed", effective_price=price,
            condition=cond, in_stock=in_stock, purchasable=in_stock,
            stock_note=(stock_txt + " " + date_txt)[:80],
            specs=specs, fetched_at=now_iso(),
        )
