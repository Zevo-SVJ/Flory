# market.py
# checks 10-13. the pool itself: depth, age, price, and whether anyone can actually sell.
import time
import requests
from config import FACTS, TICKET_USD

DS = "https://api.dexscreener.com/tokens/v1/solana"


def _best(pairs: list, mint: str) -> dict | None:
    pairs = [p for p in pairs if (p.get("baseToken") or {}).get("address") == mint]
    if not pairs:
        return None
    p = max(pairs, key=lambda x: (x.get("liquidity") or {}).get("usd") or 0)
    h1 = (p.get("txns") or {}).get("h1") or {}
    m5 = (p.get("txns") or {}).get("m5") or {}
    born = p.get("pairCreatedAt")
    return {
        "symbol": (p.get("baseToken") or {}).get("symbol"),
        "dex": p.get("dexId"),
        "pair": p.get("pairAddress"),
        "price": float(p.get("priceUsd") or 0),
        "liq_usd": (p.get("liquidity") or {}).get("usd") or 0,
        "age_min": round((time.time() * 1000 - born) / 60000) if born else None,
        "buys_1h": h1.get("buys", 0),
        "sells_1h": h1.get("sells", 0),
        "vol_1h": (p.get("volume") or {}).get("h1"),
        "buys_5m": m5.get("buys", 0),
        "sells_5m": m5.get("sells", 0),
        "vol_5m": (p.get("volume") or {}).get("m5") or 0,
        "url": p.get("url"),
        # what the team published: X, Telegram, website. a launch with a Telegram is among the strongest
        # graduation predictors in a survival study of 832,941 pump.fun launches (arXiv 2607.02823)
        "socials": sorted({(x.get("type") or "").lower() for x in ((p.get("info") or {}).get("socials") or [])}
                          | ({"website"} if (p.get("info") or {}).get("websites") else set())),
    }


def pools(mints: list[str]) -> dict[str, dict | None]:
    """Up to 30 tokens per call. The scanner uses this to drop thin pools before any real check."""
    out = {}
    for i in range(0, len(mints), 30):
        chunk = mints[i:i + 30]
        r = requests.get(f"{DS}/{','.join(chunk)}", timeout=15)
        r.raise_for_status()
        data = r.json()
        pairs = data if isinstance(data, list) else (data.get("pairs") or [])
        out.update({m: _best(pairs, m) for m in chunk})
    return out


def pool(mint: str) -> dict | None:
    return pools([mint])[mint]


def market_kill(m: dict | None) -> str | None:
    if not m:                                                    return "no_pool"
    if m["price"] <= 0:                                          return "no_price"
    if m["liq_usd"] < FACTS["min_liquidity_usd"]:                return "thin_pool"
    if TICKET_USD / m["liq_usd"] > FACTS["max_ticket_share"]:    return "ticket_too_big"
    if m["age_min"] is None or m["age_min"] < FACTS["min_age_min"]:
        return "too_fresh"
    if m["age_min"] > FACTS["max_age_hours"] * 60:               return "too_old"
    if m["buys_1h"] >= 20 and m["sells_1h"] == 0:                return "nobody_can_sell"
    return None


SOL = "So11111111111111111111111111111111111111112"
_regime = {"t": 0, "value": None}


def sol_regime() -> dict | None:
    """SOL's own trend (deepest SOL pool on DexScreener), cached 5 minutes. Solana memecoins move with
    SOL, so every verdict records it and AUDIT can tell whether passes do worse in a falling market."""
    if time.time() - _regime["t"] < 300:
        return _regime["value"]
    try:
        r = requests.get(f"{DS}/{SOL}", timeout=15)
        r.raise_for_status()
        pairs = [p for p in r.json() if (p.get("baseToken") or {}).get("address") == SOL]
        ch = max(pairs, key=lambda x: (x.get("liquidity") or {}).get("usd") or 0).get("priceChange") or {}
        value = {"sol_1h": ch.get("h1"), "sol_24h": ch.get("h24")}
    except Exception:
        value = None                      # unknown stays unknown: the verdict is logged without it
    _regime.update(t=time.time(), value=value)
    return value


_tickers = {}


def copycat(m: dict, mint: str) -> bool | None:
    """Is another Solana token under the same ticker, launched this week, clearly bigger? Then this one
    is a copy riding someone else's narrative: copies get the leftovers. Search cached 10 min per ticker.
    None when the search failed: an unknown is not a kill here, the other checks still run."""
    sym = (m.get("symbol") or "").strip().lower()
    if not sym:
        return None
    hit = _tickers.get(sym)
    if not hit or time.time() - hit[0] > 600:
        try:
            r = requests.get("https://api.dexscreener.com/latest/dex/search", params={"q": sym}, timeout=15)
            r.raise_for_status()
            data = r.json()
            pairs = (data.get("pairs") if isinstance(data, dict) else None) or []
        except Exception:
            return None
        week_ago_ms = (time.time() - 7 * 86400) * 1000   # an old token reusing the name is not a rival narrative
        hit = (time.time(), [((p.get("baseToken") or {}).get("address"), (p.get("liquidity") or {}).get("usd") or 0)
                             for p in pairs if p.get("chainId") == "solana"
                             and (p.get("pairCreatedAt") or 0) >= week_ago_ms
                             and ((p.get("baseToken") or {}).get("symbol") or "").strip().lower() == sym])
        _tickers[sym] = hit
    bigger = [liq for addr, liq in hit[1] if addr != mint and liq > 1.5 * (m.get("liq_usd") or 0)]
    return bool(bigger)
