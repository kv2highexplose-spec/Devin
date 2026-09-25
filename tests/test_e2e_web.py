"""Minimal browser E2E for the MIDI Pocket web app.

Serves site/ over localhost, drives headless Chrome via CDP, and verifies the
app boots, lists the catalog, and actually starts playback.

Requires google-chrome (or chromium) on PATH plus `websocket-client`.
Run: python -m pytest tests/test_e2e_web.py
"""
import json
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parent.parent / "site"
CHROME = next(
    (c for c in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser") if shutil.which(c)),
    None,
)

pytestmark = pytest.mark.skipif(CHROME is None, reason="no Chrome/Chromium binary on PATH")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class CDP:
    def __init__(self, ws_url: str):
        import websocket

        self.ws = websocket.create_connection(ws_url, timeout=30, suppress_origin=True)
        self.i = 0

    def send(self, method: str, params: dict | None = None):
        self.i += 1
        self.ws.send(json.dumps({"id": self.i, "method": method, "params": params or {}}))
        while True:
            r = json.loads(self.ws.recv())
            if r.get("id") == self.i:
                if "error" in r:
                    raise RuntimeError(f"{method}: {r['error']}")
                return r.get("result", {})

    def ev(self, expr: str):
        r = self.send(
            "Runtime.evaluate",
            {"expression": expr, "awaitPromise": True, "returnByValue": True},
        )
        if "exceptionDetails" in r:
            desc = r["exceptionDetails"].get("exception", {}).get(
                "description", r["exceptionDetails"].get("text")
            )
            raise AssertionError(f"page exception: {desc}")
        return r["result"].get("value")


@pytest.fixture(scope="module")
def app():
    http_port, cdp_port = _free_port(), _free_port()
    http = subprocess.Popen(
        ["python3", "-m", "http.server", str(http_port), "--bind", "127.0.0.1"],
        cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    chrome = subprocess.Popen(
        [
            CHROME, "--headless=new", f"--remote-debugging-port={cdp_port}",
            "--no-first-run", "--no-default-browser-check",
            "--autoplay-policy=no-user-gesture-required",
            "--user-data-dir=/tmp/mp_e2e_profile", "about:blank",
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        page_ws = None
        for _ in range(60):
            try:
                import urllib.request

                tabs = json.loads(urllib.request.urlopen(
                    f"http://127.0.0.1:{cdp_port}/json/list", timeout=2
                ).read())
                page_ws = next(t["webSocketDebuggerUrl"] for t in tabs if t["type"] == "page")
                break
            except Exception:
                time.sleep(0.5)
        if not page_ws:
            pytest.fail("chrome CDP endpoint did not come up")
        cdp = CDP(page_ws)
        cdp.send("Page.enable")
        cdp.send("Page.navigate", {"url": f"http://127.0.0.1:{http_port}/"})
        for _ in range(60):
            try:
                if cdp.ev("typeof window.MP === 'object' && MP.state.tracks.length"):
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            pytest.fail("app did not boot (window.MP / catalog missing)")
        yield cdp
    finally:
        chrome.terminate()
        http.terminate()


def test_catalog_loaded(app):
    n = app.ev("MP.state.tracks.length")
    assert n >= 1000, f"expected >=1000 tracks, got {n}"
    assert app.ev("document.querySelectorAll('.track').length") > 0


def test_soundfonts_registered(app):
    fonts = app.ev("MP.state.fonts.map(f=>f.id)")
    for f in ("generaluser", "fluid", "timgm", "chippocket"):
        assert f in fonts, f"missing bundled font {f}"


def test_playback_starts_and_advances(app):
    # synthetic click is a real user gesture for autoplay policy + our handlers
    app.ev("document.querySelector('.track').click()")
    for _ in range(80):
        if app.ev("MP.player.seq && !MP.player.seq.paused && MP.player.seq.currentTime > 0"):
            break
        time.sleep(0.5)
    else:
        pytest.fail("playback never started")
    assert app.ev("MP.player.synth.soundBankManager.soundBankList.length") == 1
    assert app.ev("MP.player.synth._voiceCount") > 0
    t0 = app.ev("MP.player.seq.currentTime")
    time.sleep(2)
    t1 = app.ev("MP.player.seq.currentTime")
    assert t1 - t0 > 1.0, f"playback not advancing ({t0} -> {t1})"
    assert app.ev("MP.player.ctx.state") == "running"


def test_font_switch_mid_play(app):
    app.ev("MP.player.setFont('chippocket')")
    assert app.ev("MP.state.fontId") == "chippocket"
    assert app.ev("MP.player.synth.soundBankManager.soundBankList.length") == 1
    assert app.ev("MP.player.seq && !MP.player.seq.paused")


def test_search_filters(app):
    n_all = app.ev("MP.state.filtered.length")
    app.ev("""(() => {
        const s = document.getElementById('searchBox');
        s.value = 'ランダムでは絶対にヒットしない語xyz';
        s.dispatchEvent(new Event('input', {bubbles: true}));
        return 0;
    })()""")
    assert app.ev("MP.state.filtered.length") == 0
    app.ev("""(() => {
        const s = document.getElementById('searchBox');
        s.value = ''; s.dispatchEvent(new Event('input', {bubbles: true}));
    })()""")
    assert app.ev("MP.state.filtered.length") == n_all
