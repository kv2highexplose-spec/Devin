from __future__ import annotations

from bs4 import BeautifulSoup

from ..http import Fetcher
from ..specs import parse_specs


class Scraper:
    shop = "base"
    category_map: dict[str, str] = {}  # source category slug -> normalized category

    def __init__(self, fetcher: Fetcher | None = None):
        self.f = fetcher or Fetcher()

    def run(self):
        raise NotImplementedError

    def soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    def specs_for(self, *texts: str, hint: str = "") -> dict:
        return parse_specs(" ".join(t for t in texts if t), hint)

    @staticmethod
    def classify_from_specs(specs: dict, default: str = "desktop") -> str:
        if specs.get("display"):
            return "laptop"
        return default
