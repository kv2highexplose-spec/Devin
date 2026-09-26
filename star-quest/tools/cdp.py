#!/usr/bin/env python3
"""Minimal Chrome DevTools Protocol driver for testing Star Quest."""
import json, time, sys
import urllib.request
import websockets.sync.client as ws

HTTP = "http://localhost:29229"


def find_page():
    with urllib.request.urlopen(HTTP + "/json") as r:
        tabs = json.load(r)
    for t in tabs:
        if t.get("type") == "page":
            return t["webSocketDebuggerUrl"]
    raise RuntimeError("no page tab")


class CDP:
    def __init__(self):
        self.ws = ws.connect(find_page(), max_size=50 * 1024 * 1024)
        self.mid = 0
        self.errors = []
        self.send("Runtime.enable")
        self.send("Page.enable")
        self.send("Log.enable")

    def send(self, method, **params):
        self.mid += 1
        self.ws.send(json.dumps({"id": self.mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.mid:
                return msg.get("result", msg)
            self._event(msg)

    def _event(self, msg):
        m = msg.get("method", "")
        if m == "Runtime.exceptionThrown":
            d = msg["params"]["exceptionDetails"]
            txt = d.get("exception", {}).get("description") or d.get("text", "")
            self.errors.append(txt)
            print("[JS-ERR]", txt[:400])
        elif m == "Runtime.consoleAPICalled" and msg["params"]["type"] in ("error",):
            args = " ".join(str(a.get("value", a.get("description", ""))) for a in msg["params"]["args"])
            self.errors.append(args)
            print("[CONSOLE-ERR]", args[:400])

    def drain(self, secs):
        end = time.time() + secs
        while time.time() < end:
            try:
                self.ws.recv(timeout=0.2)
            except TimeoutError:
                pass
            except Exception:
                break
            # process events
            # (recv timeout loop just clears buffer)

    def js(self, expr):
        r = self.send("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=False)
        if "exceptionDetails" in r:
            return ("ERR", r["exceptionDetails"].get("text", "") + " " +
                    str(r["exceptionDetails"].get("exception", {}).get("description", "")))
        res = r.get("result", {})
        return res.get("value", res.get("description"))

    DOMCODE = {"z": "KeyZ", "x": "KeyX", "Enter": "Enter", " ": "Space"}

    def key(self, key, ms=90):
        """Send a keypress using devtools key names."""
        code = {"up": "ArrowUp", "down": "ArrowDown", "left": "ArrowLeft",
                "right": "ArrowRight", "ok": "z", "cancel": "x",
                "enter": "Enter", "space": " "}.get(key, key)
        domcode = self.DOMCODE.get(code, code)
        self.send("Input.dispatchKeyEvent", type="keyDown", key=code, code=domcode)
        time.sleep(ms / 1000)
        self.send("Input.dispatchKeyEvent", type="keyUp", key=code, code=domcode)

    def hold(self, key, ms):
        code = {"up": "ArrowUp", "down": "ArrowDown", "left": "ArrowLeft",
                "right": "ArrowRight"}.get(key, key)
        self.send("Input.dispatchKeyEvent", type="keyDown", key=code, code=code)
        time.sleep(ms / 1000)
        self.send("Input.dispatchKeyEvent", type="keyUp", key=code, code=code)

    def shot(self, path):
        r = self.send("Page.captureScreenshot", format="png")
        import base64
        with open(path, "wb") as f:
            f.write(base64.b64decode(r["data"]))
        print("shot:", path)

    def nav(self, url):
        self.send("Page.navigate", url=url)
        time.sleep(1.5)
        # drain events
        self.drain(0.5)


if __name__ == "__main__":
    c = CDP()
    c.nav("http://localhost:8321/")
    time.sleep(1)
    print("scene:", c.js("SQ ? SQ.scene() : 'no SQ'"))
    c.shot("/tmp/sq_title.png")
    print("errors:", len(c.errors))
