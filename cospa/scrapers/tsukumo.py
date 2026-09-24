"""Tsukumo e-shop (shop.tsukumo.co.jp) — server-rendered search + rich stock flags."""
from __future__ import annotations

import re
from urllib.parse import quote

from ..models import Listing, now_iso
from ..specs import parse_specs
from .base import Scraper

BASE = "https://shop.tsukumo.co.jp"

QUERIES = [
    ("デスクトップPC", "desktop", 8),
    ("ゲーミングPC", "desktop", 10),
    ("ノートPC", "laptop", 8),
    ("グラフィックボード", "gpu", 10),
    ("CPU", "cpu", 8),
    ("マザーボード", "motherboard", 6),
    ("PCメモリ", "memory", 6),
    ("SSD", "ssd", 6),
    ("PC電源", "psu", 4),
    ("中古", None, 8),
]

STOCK_OUT = ("在庫なし", "入荷待ち", "販売終了", "取扱終了", "予約受付終了")


class TsukumoScraper(Scraper):
    shop = "tsukumo"

    def run(self, limit_pages: int | None = None) -> list[Listing]:
        out, seen = [], set()
        for kw, cat_hint, pages in QUERIES:
            if limit_pages:
                pages = min(pages, limit_pages)
            for n in self._search(kw, pages):
                if n.url in seen:
                    continue
                if cat_hint and n.category == "other":
                    n.category = cat_hint
                seen.add(n.url)
                out.append(n)
        return out

    def _search(self, keyword: str, pages: int) -> list[Listing]:
        out = []
        for p in range(1, pages + 1):
            if p == 1:
                url = f"{BASE}/search/?keyword={quote(keyword)}&end_of_sales=1&sort=publish_date+desc"
            else:
                url = f"{BASE}/search/p{p}/?keyword={quote(keyword)}&end_of_sales=1&sort=publish_date+desc"
            try:
                html = self.f.text(url)
            except Exception:
                break
            items = self.soup(html).select("div.search-box__product")
            if not items:
                break
            for it in items:
                l = self._parse(it, keyword)
                if l:
                    out.append(l)
        return out

    def _parse(self, it, keyword: str) -> Listing | None:
        a = it.select_one("a.product-link")
        price_el = it.select_one(".sli_grid_price")
        if not (a and price_el):
            return None
        href = a.get("href", "")
        url = href if href.startswith("http") else BASE + href
        name = (a.get("title") or a.get_text(strip=True)).strip()
        if not name:
            h2 = it.select_one("h2.product-name") or it.select_one(".product-name")
            name = h2.get_text(strip=True) if h2 else ""
        meta = it.select_one('meta[itemprop="name"]')
        if not name and meta:
            name = meta.get("content", "")
        m = re.search(r"[¥￥]([\d,]+)", price_el.get_text())
        if not m:
            return None
        price = int(m.group(1).replace(",", ""))
        stock_el = it.select_one(".search_stock_title")
        stock = stock_el.get_text(strip=True) if stock_el else ""
        deliv = it.select_one(".tommorow_deliv")
        if deliv and deliv.get_text(strip=True):
            stock = f"{stock} / {deliv.get_text(' ', strip=True)}".strip(" /")
        in_stock = not any(s in stock for s in STOCK_OUT) and bool(stock)
        cat = classify(name, keyword)
        specs = parse_specs(name, cat)
        return Listing(
            shop=self.shop, name=name, url=url, category=cat,
            price=price, price_kind="exact", effective_price=price,
            condition="used" if "中古" in name or "中古" in keyword else "new",
            in_stock=in_stock, purchasable=in_stock,
            stock_note=stock, specs=specs, fetched_at=now_iso(),
        )


_LAPTOP = ("ノート", "note pc", "laptop", "book", "thinkpad", "elitebook",
           "dynabook", "letsnote", "surface pro", "surface laptop", "x1 ",
           "probook", "vostro", "inspiron", "ideapad", "macbook", "chromebook",
           "タブレット", "ally", "rog xbox", "claw", "steam deck")
_MB = ("マザーボード", "motherboard")


def classify(name: str, keyword: str) -> str:
    n = name.lower()
    used = "中古" in keyword or "中古" in n
    # name-driven first
    if re.search(r"\b(b\d{3,4}m?[se]?|z\d{3,4}|x\d{3,4}[se]?|h\d{3,4}|a\d{3,3}m?)\s*(v\d+|pro|plus|wifi)?\s*(マザー|motherboard|\bv\d{2})?\b", n) or any(k in n for k in _MB):
        if not used:
            return "motherboard"
    if any(k in n for k in _LAPTOP):
        return "laptop"
    if re.search(r"rtx|gtx|radeon|geforce|\barc\b|ビデオカード|グラフィックボード|グラフィックカード", n):
        return "gpu"
    if re.search(r"ssd|nvme|hdd", n):
        return "ssd"
    if re.search(r"ddr[345]|メモリ|memory", n):
        return "memory"
    if re.search(r"電源|psu|80plus|w\s*atx", n):
        return "psu"
    if re.search(r"ryzen|core i|core\s*ultra|xeon|celeron|pentium|プロセッサ|\bcpu\b", n):
        if used:
            return "desktop" if "pc" not in n else "desktop"
        return "cpu" if "cpu" in keyword.lower() else "desktop"
    # keyword fallback
    if "ノート" in keyword:
        return "laptop"
    if "グラフィック" in keyword:
        return "gpu"
    if "cpu" in keyword.lower():
        return "cpu"
    if "メモリ" in keyword:
        return "memory"
    if "ssd" in keyword.lower():
        return "ssd"
    if "マザー" in keyword:
        return "motherboard"
    if "電源" in keyword:
        return "psu"
    if used:
        return "desktop"
    if "デスクトップ" in keyword or "ゲーミング" in keyword:
        return "desktop"
    return "other"
