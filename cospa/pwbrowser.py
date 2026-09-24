"""Headless Chrome via Playwright for JS-rendered shops and button checks."""
from __future__ import annotations

import contextlib
import time

from playwright.sync_api import sync_playwright

CHROME = "/home/ubuntu/.local/bin/google-chrome"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


@contextlib.contextmanager
def browser():
    pw = sync_playwright().start()
    try:
        br = pw.chromium.launch(
            executable_path=CHROME,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"],
        )
        ctx = br.new_context(user_agent=UA, locale="ja-JP", viewport={"width": 1366, "height": 900})
        try:
            yield ctx
        finally:
            ctx.close()
            br.close()
    finally:
        pw.stop()


def rendered_text(page, url: str, wait_ms: int = 2500, scroll: int = 0) -> str:
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(wait_ms)
    for _ in range(scroll):
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(600)
    return page.content()


def check_buy_button(page, url: str, selectors: list[str],
                     wait_ms: int = 2000) -> dict:
    """Visit a product page and report whether a cart/buy button exists and is enabled.

    Returns {"found": bool, "enabled": bool, "label": str, "selector": str}.
    Never clicks the button — enabled state is read from the DOM only.
    """
    out = {"found": False, "enabled": False, "label": "", "selector": ""}
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(wait_ms)
    except Exception as e:
        out["error"] = f"goto: {type(e).__name__}"
        return out
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el is None:
                continue
            out["found"] = True
            out["selector"] = sel
            try:
                out["enabled"] = bool(el.is_enabled()) and el.is_visible()
            except Exception:
                out["enabled"] = False
            try:
                out["label"] = (el.inner_text() or "").strip()[:60]
            except Exception:
                pass
            return out
        except Exception:
            continue
    return out


@contextlib.contextmanager
def throttle(seconds: float = 1.2):
    start = time.time()
    yield
    dt = time.time() - start
    if dt < seconds:
        time.sleep(seconds - dt)
