"""Sycom BTO (sycom.co.jp) — /custom/model?no= pages expose per-option prices/stock."""
from __future__ import annotations

import re

from ..models import Listing, now_iso
from ..specs import parse_specs
from .base import Scraper

BASE = "https://www.sycom.co.jp"
INDEX = [
    f"{BASE}/bto/game_pc/",
    f"{BASE}/bto/business_pc/",
    f"{BASE}/bto/creator_pc/",
    f"{BASE}/bto/mini_pc/",
]

# partsBox section id -> spec role
SEC_MAP = {
    "CPU": "cpu", "anc-004": "mem", "anc-005": "ssd", "anc-007": "gpu",
    "anc-003": "mb", "anc-010": "case", "anc-011": "psu",
}


class SycomScraper(Scraper):
    shop = "sycom"

    def run(self, limit_pages: int | None = None) -> list[Listing]:
        model_urls = []
        for idx in INDEX:
            try:
                html = self.f.text(idx)
            except Exception:
                continue
            for u in re.findall(r'href="(/custom/model\?no=\d+|https://www\.sycom\.co\.jp/custom/model\?no=\d+)"', html):
                if u not in model_urls:
                    model_urls.append(u)
        if limit_pages:
            model_urls = model_urls[:limit_pages]
        out = []
        for u in model_urls:
            url = u if u.startswith("http") else BASE + u
            try:
                out.extend(self._model(url))
            except Exception:
                continue
        return out

    def _model(self, url: str) -> list[Listing]:
        html = self.f.text(url)
        soup = self.soup(html)
        title = soup.title.get_text(strip=True) if soup.title else url
        title = re.sub(r"[｜|].*$", "", title).strip()
        # collect sections
        sections: dict[str, list[dict]] = {}
        for box in soup.select("div.partsBox01"):
            sid = box.get("id", "")
            role = SEC_MAP.get(sid)
            if not role:
                continue
            opts = []
            for li in box.select("ul.partsList li"):
                name_el = li.select_one('span[id$="_n"], span.name')
                price_el = li.select_one('span[id$="_p"], span.price')
                if not name_el:
                    continue
                name = name_el.get_text(" ", strip=True)
                name = re.sub(r"<a.*", "", name)
                price_txt = price_el.get_text(" ", strip=True) if price_el else ""
                checked = bool(li.select_one("input[checked]"))
                stopped = "stopOrder" in (li.get("class") or []) or "在庫切れ" in price_txt
                m = re.search(r"([+-]?[\d,]+)\s*円", price_txt)
                price = int(m.group(1).replace(",", "")) if m else None
                opts.append({"name": name, "price_txt": price_txt, "price": price,
                             "checked": checked, "stopped": stopped})
            sections[role] = opts
        cpu_opts = sections.get("cpu", [])
        if not cpu_opts:
            # fallback: single-config page — treat whole page
            specs = parse_specs(title)
            m = re.search(r"([\d,]{5,})\s*円", soup.get_text())
            if not m:
                return []
            price = int(m.group(1).replace(",", ""))
            return [self._listing(title, url, price, specs, True, title)]
        defaults = {}
        for role in ("gpu", "mem", "ssd"):
            opts = sections.get(role, [])
            checked = [o for o in opts if o["checked"]]
            defaults[role] = (checked or opts[:1] or [{"name": ""}])[0]["name"]
        out = []
        for o in cpu_opts:
            if o["price"] is None:
                continue
            spec_text = " ".join([o["name"], defaults["gpu"], defaults["mem"], defaults["ssd"]])
            specs = parse_specs(f"{title} {spec_text}")
            name = f"{title} {o['name'].split('[')[0].strip()}"[:120]
            out.append(self._listing(name, url, o["price"], specs,
                                     not o["stopped"], o["name"]))
        return out

    def _listing(self, name, url, price, specs, in_stock, stock_note) -> Listing:
        return Listing(
            shop=self.shop, name=name, url=url, category="desktop",
            price=price, price_kind="exact", effective_price=price,
            condition="new", in_stock=in_stock, purchasable=in_stock,
            stock_note="受注生産" if in_stock else "一部オプション在庫切れ",
            specs=specs, fetched_at=now_iso(),
        )
