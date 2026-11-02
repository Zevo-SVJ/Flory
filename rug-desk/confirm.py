# confirm.py
# buy on confirmation instead of at the verdict. Nov 2 (diag.py --entree, every Robinhood token killed only for
# an unlocked LP, replayed with the desk's exits and costs): buying at the verdict made +13.0% a trade over 216
# (+9.4% without the top 3, 41% winners); waiting up to 2 h for +10% over the verdict price with more buys than
# sells in the last 5 min made +21.3% over the 139 that confirmed (+17.2% without the top 3, 54% winners).
# a token that never confirms is never bought: those were the losers that never went anywhere.
# used for the lp_open tier while shadow.confirm_ok() says the shadow book still shows it; VIGIE checks the
# queue every 20 s from the prices it already records for every shadowed token (paths.py).
import json, os, time
from config import DATA
import atomic, book, paths

FILE = os.path.join(DATA, "confirm.json")
RISE = 1.10                 # +10% over the verdict price...
WAIT_S = 2 * 3600           # ...within 2 h, else dropped


def load() -> dict:
    try:
        with open(FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(q: dict):
    os.makedirs(DATA, exist_ok=True)
    tmp = atomic.tmp(FILE)
    with open(tmp, "w") as f:
        json.dump(q, f)
    os.replace(tmp, FILE)


def add(mint: str, v: dict):
    q = load()
    q[mint] = {"t": time.time(), "price": v["price"], "symbol": v.get("symbol") or mint[:6], "liq": v.get("liq_usd"),
               "ticket": v.get("ticket"), "tier": v.get("tier"), "vaults": v.get("vaults"), "sol0": v.get("sol0")}
    _save(q)


def tick(now: float | None = None) -> list[dict]:
    """Buys what confirmed, drops what waited too long. Returns events for the log."""
    now = now or time.time()
    q, out, changed = load(), [], False
    for mint, c in list(q.items()):
        if now > c["t"] + WAIT_S:
            q.pop(mint); changed = True
            out.append({"kind": "kill", "symbol": c["symbol"], "mint": mint,
                        "text": f"${c['symbol']} not bought: no confirmation in 2 h (+10% with buyers)"})
            continue
        pts = paths.load(mint, since=now - 90)
        s = pts[-1] if pts else None
        if not s or s["price"] < RISE * c["price"] or (s.get("b5") or 0) <= (s.get("s5") or 0):
            continue
        q.pop(mint); changed = True
        if (g := book.guard(mint)):
            out.append({"kind": "kill", "symbol": c["symbol"], "mint": mint,
                        "text": f"${c['symbol']} confirmed but skipped (limits): {g}"})
            continue
        usd = c.get("ticket") or None
        book.open_position(mint, c["symbol"], s["price"], s.get("liq") or c["liq"], **({"usd": usd} if usd else {}),
                           vaults=c.get("vaults"), sol0=c.get("sol0"))
        out.append({"kind": "buy", "symbol": c["symbol"], "mint": mint, "price": s["price"],
                    "text": f"BUY ${usd or 0:.0f} ({c.get('tier')}, confirmed +{(s['price'] / c['price'] - 1) * 100:.0f}% "
                            f"with buyers) ${c['symbol']} @ {s['price']:.8g}"})
    if changed:
        _save(q)
    return out
