"""Zero-dependency dashboard server: /api/data, /api/refresh, static UI."""
from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from ..store import DATA_DIR

DASH_DIR = Path(__file__).parent
_refresh_state = {"running": False, "log": []}


def _do_refresh(only=None):
    if _refresh_state["running"]:
        return
    _refresh_state["running"] = True
    _refresh_state["log"] = ["started"]
    try:
        import run as _run  # run.py at repo root
        items = _run.scrape(only)
        _run.analyze(items)
        _refresh_state["log"].append(f"done: {len(items)} items")
    except Exception as e:  # noqa
        _refresh_state["log"].append(f"error: {e}")
    finally:
        _refresh_state["running"] = False


class Handler(SimpleHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path):
        if not path.exists() or path.is_dir():
            path = DASH_DIR / "index.html"
        body = path.read_bytes()
        ctype = "text/html; charset=utf-8"
        if path.suffix == ".js":
            ctype = "application/javascript"
        elif path.suffix == ".css":
            ctype = "text/css"
        elif path.suffix == ".json":
            ctype = "application/json; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/data":
            ap = DATA_DIR / "analysis.json"
            if not ap.exists():
                self._json({"items": [], "summary": {}, "generated_at": None})
            else:
                d = json.loads(ap.read_text(encoding="utf-8"))
                vp = DATA_DIR / "verify.json"
                if vp.exists():
                    vmap = {}
                    for r in json.loads(vp.read_text(encoding="utf-8")).get("results", []):
                        vmap[r["url"]] = r
                    for i in d.get("items", []):
                        r = vmap.get(i.get("url"))
                        if r:
                            i["verify"] = {
                                "purchasable_now": r.get("purchasable_now"),
                                "in_stock": r.get("in_stock"),
                                "cart_enabled": r.get("cart_enabled"),
                                "verified_price": r.get("verified_price"),
                                "price_match": r.get("price_match"),
                                "stock_kw": r.get("stock_kw"),
                            }
                    d["verify_generated_at"] = json.loads(vp.read_text(encoding="utf-8")).get("generated_at")
                self._json(d)
        elif path == "/api/refresh":
            only = None
            if "?" in self.path:
                from urllib.parse import parse_qs, urlparse
                q = parse_qs(urlparse(self.path).query).get("only")
                only = q[0].split(",") if q else None
            threading.Thread(target=_do_refresh, args=(only,), daemon=True).start()
            self._json({"started": True})
        elif path == "/api/status":
            self._json(_refresh_state)
        elif path == "/api/history":
            p = DATA_DIR / "history.jsonl"
            lines = p.read_text(encoding="utf-8").strip().split("\n")[-500:] if p.exists() else []
            self._json({"history": [json.loads(l) for l in lines if l]})
        elif path == "/" or path.startswith("/index"):
            self._file(DASH_DIR / "index.html")
        elif path.startswith("/static/"):
            self._file(DASH_DIR / path[len("/static/"):])
        else:
            self.send_error(404)

    def log_message(self, *a):
        pass


def serve(host="0.0.0.0", port=8000):
    srv = ThreadingHTTPServer((host, port), Handler)
    print(f"dashboard: http://localhost:{port}")
    srv.serve_forever()
