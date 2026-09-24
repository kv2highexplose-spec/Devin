from __future__ import annotations

import time
import random
import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


class Fetcher:
    def __init__(self, min_interval: float = 0.8, timeout: int = 25,
                 encoding: str | None = None):
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.5",
        })
        self.min_interval = min_interval
        self.timeout = timeout
        self.encoding = encoding
        self._last = 0.0

    def get(self, url: str, retries: int = 3, **kw) -> requests.Response | None:
        for i in range(retries):
            gap = self.min_interval + random.uniform(0, 0.4)
            dt = time.time() - self._last
            if dt < gap:
                time.sleep(gap - dt)
            try:
                r = self.s.get(url, timeout=self.timeout, **kw)
                self._last = time.time()
                if r.status_code == 200:
                    if self.encoding:
                        r.encoding = self.encoding
                    return r
                if r.status_code in (403, 429, 503):
                    time.sleep(2 + i * 3)
                    continue
                return r
            except requests.RequestException:
                time.sleep(2 + i * 2)
        return None

    def text(self, url: str, **kw) -> str | None:
        r = self.get(url, **kw)
        return r.text if r is not None else None
