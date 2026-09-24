from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path


def discover() -> dict[str, type]:
    """Return {shop_name: ScraperClass} for every scraper module here."""
    out = {}
    pkg = Path(__file__).parent
    for mod in pkgutil.iter_modules([str(pkg)]):
        if mod.name in ("base", "__init__"):
            continue
        m = importlib.import_module(f"cospa.scrapers.{mod.name}")
        for attr in dir(m):
            cls = getattr(m, attr)
            if isinstance(cls, type) and getattr(cls, "shop", None) and cls.__name__.endswith("Scraper"):
                out[cls.shop] = cls
    return out


def run_all(only: list[str] | None = None) -> list:
    from ..models import Listing
    items: list[Listing] = []
    for name, cls in discover().items():
        if only and name not in only:
            continue
        try:
            got = cls().run()
            print(f"[{name}] {len(got)} items")
            items.extend(got)
        except Exception as e:
            print(f"[{name}] FAILED: {e}")
    return items
