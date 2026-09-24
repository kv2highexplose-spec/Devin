"""Re-verify purchasability on actual product pages: price + stock + cart button."""
from __future__ import annotations

import re
import time

from bs4 import BeautifulSoup

from .http import Fetcher

OUT_STOCK = ("在庫なし", "在庫切れ", "完売", "品切れ", "売り切れ", "取扱終了", "販売終了",
             "お取り寄せ不可", "売り尽くし", "SOLD OUT", "soldout", "現在取り扱っておりません")
IN_STOCK = ("在庫あり", "在庫有り", "残りわずか", "在庫僅少", "お取り寄せ", "取り寄せ",
            "受注生産", "メーカー直送", "通常販売", "即納")
CART_PAT = re.compile(r"(カートに入れ|カートへ|購入する|今すぐ購入|購入|買い物カゴ|買い物かご|注文する|カスタマイズ・購入|add.?to.?cart)", re.I)
NO_STOCK_PAT = re.compile(r"(在庫なし|在庫切れ|完売|品切|販売終了|取扱終了|お取り寄せ不可)")


SHOP_PRICE = {
    "iosys": ["div.price.row p", "p.price"],
    "dospara": [".p0", ".sales_price", ".product-price", ".price"],
    "tsukumo": [".price .price-normal", ".price", ".product-price"],
    "frontier": [".price-box .price", ".product-price", ".price"],
    "sycom": ["#price", ".price"],
    "sofmap": [".price strong", ".price", ".products_price"],
    "mouse": [".goods-price-value", ".price"],
    "be-stock": [".product-info-price .price", ".price-box .price", ".price"],
    "nttx": [".block-detail--price", ".price", ".goods-price"],
    "janpara": [".item_amount", ".price"],
    "pc-koubou": [".price--num", ".price"],
    "kakaku": [".priceLowest .price", ".price"],
}


def _jsonld_price(html: str) -> int | None:
    for m in re.finditer(r'"(?:lowPrice|price|low_price|highPrice)"\s*:\s*"?([\d.]+)"?', html):
        try:
            v = int(float(m.group(1)))
            if v > 300:
                return v
        except ValueError:
            continue
    return None


def _first_price(soup, pats) -> int | None:
    for sel in pats:
        el = soup.select_one(sel)
        if el:
            m = re.search(r"[\d,]{3,}", el.get_text(" ", strip=True))
            if m:
                return int(m.group(0).replace(",", ""))
    return None


def _cart_button_state(soup) -> tuple[bool | None, str]:
    """(enabled|None, note). Heuristic: a cart/buy control exists and isn't disabled/CS."""
    btns = []
    for sel in ("button", "a", "input[type=button]", "input[type=submit]", "input[type=image]"):
        for el in soup.select(sel):
            t = (el.get_text(" ", strip=True) or el.get("value", "") or el.get("alt", "") or el.get("title", ""))
            if CART_PAT.search(t):
                btns.append(el)
    if not btns:
        return None, "no-cart-btn"
    for el in btns:
        cls = " ".join(el.get("class") or [])
        dis = el.get("disabled") is not None or "disabled" in cls.lower() or "soldout" in cls.lower()
        if not dis:
            return True, "cart-enabled"
    return False, "cart-disabled"


def verify_generic(html: str, url: str, shop: str = "") -> dict:
    soup = BeautifulSoup(html, "html.parser")
    body = soup.get_text(" ", strip=True)
    in_stock = None
    stock_kw = None
    for kw in OUT_STOCK:
        if kw in body:
            in_stock = False
            stock_kw = kw
            break
    if in_stock is None:
        for kw in IN_STOCK:
            if kw in body:
                in_stock = True
                stock_kw = kw
                break
    cart_ok, cart_note = _cart_button_state(soup)
    price = _jsonld_price(html) or _first_price(soup, SHOP_PRICE.get(shop, []) + [
        ".price", ".sales_price", ".sale-price", ".item_price", ".products_price",
        ".special_price", ".current-price", ".p-price", "#js-p-detail-price",
        ".product-info-price .price", ".price-wrapper", ".price-box .price",
        ".unit-price", ".productPrice", ".p0", ".itemInfo--price", ".goods-price-value",
    ])
    return {"in_stock": in_stock, "stock_kw": stock_kw, "cart_enabled": cart_ok, "cart_note": cart_note, "price": price}


DOSPARA_BAD_STOCK = ("在庫なし", "売り切れ", "販売終了", "お取り寄せ不可")


def _dospara(html: str) -> dict | None:
    m = re.search(r'productJson\s*=\s*(\{.*?\});', html, re.S)
    if not m:
        return None
    import json as _j
    try:
        j = _j.JSONDecoder().raw_decode(m.group(1))[0]
    except Exception:
        return None
    stk = j.get("stkname") or ""
    price = j.get("amttax") or j.get("price")
    return {
        "in_stock": bool(stk) and stk not in DOSPARA_BAD_STOCK,
        "stock_kw": stk or None,
        "cart_enabled": bool(stk) and stk not in DOSPARA_BAD_STOCK,
        "cart_note": "dospara-stkname",
        "price": int(price) if price else None,
        "detail_specs": {k: j.get(k) for k in ("cpu2", "video2", "memory2", "ssd2") if j.get(k)},
    }


def verify_listing(f: Fetcher, listing: dict) -> dict:
    url = listing["url"]
    shop = listing.get("shop", "")
    out = {"verified": False, "shop": shop}
    try:
        html = f.text(url)
    except Exception as e:
        out["error"] = f"fetch: {type(e).__name__}"
        return out
    if shop in ("janpara", "pc-koubou", "be-stock", "nttx") and (not html or len(html) < 20000):
        try:
            from .pwbrowser import browser
            with browser() as page:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(2600)
                html = page.content()
        except Exception as e:
            out["error"] = f"pw: {type(e).__name__}"
    if not html:
        out["error"] = "empty"
        return out
    if "<title>404" in html or "ページが見つかりません" in html[:8000]:
        out["error"] = "404"
        out["verified"] = True
        out["in_stock"] = False
        out["purchasable_now"] = False
        return out
    if shop == "dospara":
        r = _dospara(html) or verify_generic(html, url, shop)
    else:
        r = verify_generic(html, url, shop)
    out.update(r)
    out["verified"] = True
    in_stock = r["in_stock"]
    cart = r["cart_enabled"]
    if shop in ("sycom", "mouse", "frontier"):
        # BTO shops: page chrome mentions 在庫 keywords spuriously; cart link is the signal
        out["purchasable_now"] = cart is True and (in_stock is not False or True)
    else:
        out["purchasable_now"] = (in_stock is not False) and (cart is not False) and (
            in_stock is True or cart is True)
    if r["price"]:
        out["verified_price"] = r["price"]
        lp = listing.get("effective_price") or listing.get("price")
        if lp:
            out["price_match"] = abs(r["price"] - lp) / lp < 0.02
    return out


def verify_many(listings: list[dict], limit: int = 40, delay: float = 1.0) -> list[dict]:
    f = Fetcher()
    out = []
    for l in listings[:limit]:
        v = verify_listing(f, l)
        v["url"] = l["url"]
        v["name"] = l.get("name", "")[:80]
        v["list_price"] = l.get("effective_price") or l.get("price")
        out.append(v)
        time.sleep(delay)
    return out
