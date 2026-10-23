# market.py
# checks 10-13. the pool itself: depth, age, price, and whether anyone can actually sell.
import time
import requests
from config import FACTS, TICKET_USD, MOMENTUM
import chains

DS = "https://api.dexscreener.com/tokens/v1/solana"
DS_TOKENS = "https://api.dexscreener.com/tokens/v1"        # /{chainId}/{addr,addr,...}, 30 at most


def _best(pairs: list, mint: str) -> dict | None:
    chain, addr = chains.split(mint)
    same = (lambda a: a == addr) if chain == "solana" else (lambda a: (a or "").lower() == addr.lower())
    pairs = [p for p in pairs if same((p.get("baseToken") or {}).get("address"))
             and p.get("chainId", chain) == chain]
    if not pairs:
        return None
    p = max(pairs, key=lambda x: (x.get("liquidity") or {}).get("usd") or 0)
    h1 = (p.get("txns") or {}).get("h1") or {}
    m5 = (p.get("txns") or {}).get("m5") or {}
    born = p.get("pairCreatedAt")
    return {
        "symbol": (p.get("baseToken") or {}).get("symbol"),
        "chain": chain,
        "dex": p.get("dexId"),
        "pair": p.get("pairAddress"),
        "price": float(p.get("priceUsd") or 0),
        "price_native": float(p.get("priceNative") or 0),       # in SOL: priceUsd / priceNative = SOL's price
        "liq_usd": (p.get("liquidity") or {}).get("usd") or 0,
        "mcap": p.get("marketCap") or p.get("fdv") or 0,
        "age_min": round((time.time() * 1000 - born) / 60000) if born else None,
        "buys_1h": h1.get("buys", 0),
        "sells_1h": h1.get("sells", 0),
        "vol_1h": (p.get("volume") or {}).get("h1"),
        "vol_6h": (p.get("volume") or {}).get("h6") or 0,
        "vol_24h": (p.get("volume") or {}).get("h24") or 0,
        "chg_5m": (p.get("priceChange") or {}).get("m5") or 0,
        "chg_1h": (p.get("priceChange") or {}).get("h1") or 0,
        "chg_24h": (p.get("priceChange") or {}).get("h24") or 0,
        # the average trade: rug farms fake activity with hundreds of wallets buying $3-10 each. on Oct 19
        # the 18 "Gemini" and the FOMO farm traded $4-9 a swap; the graduates that really ran, $40-75
        "avg_trade_1h": ((p.get("volume") or {}).get("h1") or 0) / max(1, h1.get("buys", 0) + h1.get("sells", 0)),
        "liq_quote": (p.get("liquidity") or {}).get("quote"),     # SOL in the pool, as DexScreener last saw it
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
    """Up to 30 tokens per call and chain. The scanner uses this to drop thin pools before any real check.
    keys are Solana mints or "chain:0xaddr" (chains.py)."""
    out, by_chain = {}, {}
    for m in mints:
        by_chain.setdefault(chains.split(m)[0], []).append(m)
    for chain, keys in by_chain.items():
        if not chains.supported(chain):
            out.update({k: None for k in keys})
            continue
        for i in range(0, len(keys), 30):
            chunk = keys[i:i + 30]
            url = f"{DS}/{','.join(chunk)}" if chain == "solana" else \
                f"{DS_TOKENS}/{chain}/{','.join(chains.split(k)[1] for k in chunk)}"
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
            pairs = data if isinstance(data, list) else (data.get("pairs") or [])
            out.update({m: _best(pairs, m) for m in chunk})
    return out


def locate(addr: str) -> str | None:
    """A bare 0x address (pasted in the dashboard or sent to the bot) is on some EVM chain: the supported
    chain where its deepest pool sits. Returns the token key, or None."""
    if ":" in addr or not addr.lower().startswith("0x"):
        return addr
    try:
        r = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{addr}", timeout=15)
        r.raise_for_status()
        pairs = (r.json() or {}).get("pairs") or []
    except Exception:
        return None
    pairs = [p for p in pairs if chains.supported(p.get("chainId")) and p.get("chainId") != "solana"
             and ((p.get("baseToken") or {}).get("address") or "").lower() == addr.lower()]
    if not pairs:
        return None
    best = max(pairs, key=lambda p: (p.get("liquidity") or {}).get("usd") or 0)
    return chains.key(best["chainId"], addr)


def pool(mint: str) -> dict | None:
    return pools([mint])[mint]


def market_kill(m: dict | None) -> str | None:
    if not m:                                                    return "no_pool"
    if m["price"] <= 0:                                          return "no_price"
    if m["liq_usd"] < FACTS["min_liquidity_usd"]:                return "thin_pool"
    # gas paid twice on a small ticket: on Ethereum a $25 ticket loses 12% before the price moves
    if 2 * chains.CHAINS.get(m.get("chain") or "solana", chains.CHAINS["solana"])["tx_usd"] > \
            FACTS.get("max_fixed_cost_pct", 5) / 100 * TICKET_USD:   return "fees_eat_ticket"
    if TICKET_USD / m["liq_usd"] > FACTS["max_ticket_share"]:    return "ticket_too_big"
    cap_x = MOMENTUM["max_mcap_liq"] if lane(m) == "momentum" else FACTS["max_mcap_liq"]
    if (m.get("mcap") or 0) > cap_x * m["liq_usd"]:              return "fake_cap"
    if m["buys_1h"] + m["sells_1h"] >= 100 and m.get("avg_trade_1h", 1e9) < FACTS["min_avg_trade_usd"]:
        return "micro_trades"
    # a launch must trade 5% of its pool an hour; a deep survivor's pool can't turn that fast, its
    # volume is judged against its own recent hours instead (momentum_kill)
    if lane(m) == "early" and (m.get("vol_1h") or 0) < FACTS["min_turnover_1h"] * m["liq_usd"]:
        return "dead_volume"
    if m["age_min"] is None or m["age_min"] < FACTS["min_age_min"]:
        return "too_fresh"
    if m["buys_1h"] >= 20 and m["sells_1h"] == 0:                return "nobody_can_sell"
    if lane(m) == "momentum":
        return momentum_kill(m)
    return None


def lane(m: dict) -> str:
    """"early": a launch, up to max_age_hours old. "momentum": a survivor, judged on its move."""
    return "momentum" if (m.get("age_min") or 0) > FACTS["max_age_hours"] * 60 else "early"


def momentum_kill(m: dict) -> str | None:
    """A survivor is bought only while it moves: rising, on rising volume, buyers ahead, not vertical.
    "no_momentum" is not a verdict on the token: SCOUT sees it again when it trends again."""
    p = MOMENTUM
    if m["liq_usd"] < p["min_liq_usd"]:                          return "thin_pool"
    if m.get("vol_24h", 0) < p["min_vol_24h"]:                   return "dead_volume"
    if m.get("chg_1h", 0) > p["max_chg_1h"] or m.get("chg_24h", 0) > p["max_chg_24h"]:
        return "overextended"
    if m.get("chg_1h", 0) < p["min_chg_1h"] or m.get("chg_5m", 0) < p["min_chg_5m"]:
        return "no_momentum"
    if (m.get("vol_1h") or 0) < p["vol_accel"] * (m.get("vol_6h") or 0) / 6:
        return "no_momentum"
    if m["buys_1h"] < m["sells_1h"]:                              return "no_momentum"
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


def copycat(m: dict, mint: str) -> str | None:
    """Two kills from one search of the ticker (cached 10 min). None when clean or the search failed.
    - "serial_farm": 2+ other PumpSwap tokens under this ticker, launched in the 72 h BEFORE this one, dead
      (pool under $5k) after bot-made volume (average swap under $15). namesakes that died on the bonding
      curve don't count: every name gets those. a rug factory recycles names: 18 "Gemini" and 14 "FOMO" in a day on Oct 19, each
      pumped by bots for ~1 h then dumped in one block to the same -95.7%. the next one is the same script.
    - "copycat": another token under the ticker, launched this week, clearly bigger: copies get the leftovers."""
    sym = (m.get("symbol") or "").strip().lower()
    if not sym:
        return None
    ck = f"{m.get('chain') or 'solana'}:{sym}"
    hit = _tickers.get(ck)
    if not hit or time.time() - hit[0] > 600:
        try:
            r = requests.get("https://api.dexscreener.com/latest/dex/search", params={"q": sym}, timeout=15)
            r.raise_for_status()
            data = r.json()
            pairs = (data.get("pairs") if isinstance(data, dict) else None) or []
        except Exception:
            return None
        week_ago_ms = (time.time() - 7 * 86400) * 1000   # an old token reusing the name is not a rival narrative
        def avg24(p):
            t = (p.get("txns") or {}).get("h24") or {}
            return ((p.get("volume") or {}).get("h24") or 0) / max(1, (t.get("buys") or 0) + (t.get("sells") or 0))
        hit = (time.time(), [((p.get("baseToken") or {}).get("address"), (p.get("liquidity") or {}).get("usd") or 0,
                              p.get("pairCreatedAt") or 0, p.get("dexId"), avg24(p),
                              (p.get("volume") or {}).get("h24") or 0)
                             for p in pairs if p.get("chainId") == (m.get("chain") or "solana")
                             and (p.get("pairCreatedAt") or 0) >= week_ago_ms
                             and ((p.get("baseToken") or {}).get("symbol") or "").strip().lower() == sym])
        _tickers[ck] = hit
    # only the dead namesakes born BEFORE this token count: a real runner gets copied after it runs, and its
    # copies die (UHI, XBT, HOOT on Oct 19). a factory's previous batches are older than its next one
    recent_ms = (time.time() - 72 * 3600) * 1000
    me_ms = (time.time() - (m.get("age_min") or 0) * 60) * 1000
    me = chains.split(mint)[1].lower()
    dead = {addr for addr, liq, born, dex, avg, _ in hit[1]
            if (addr or "").lower() != me and dex == "pumpswap" and recent_ms <= born < me_ms - 10 * 60000
            and liq < 5000 and avg < FACTS["min_avg_trade_usd"]}
    if len(dead) >= 2:
        return "serial_farm"
    # a rival counts only if it really trades: the $1.2M "UHI" pools on Fluxbeam (Oct 19) moved 2% a day.
    # and only if it was there FIRST: a runner draws copies within the hour, and those copies can outgrow
    # it for a while. counting them killed the originals: DAC (1.25M$ traded in 24 h) and Tengu on Oct 19,
    # each "copying" namesakes launched after them. copycat was the desk's first kill reason that evening
    bigger = [liq for addr, liq, born, _, _, vol24 in hit[1]
              if (addr or "").lower() != me and born < me_ms - 10 * 60000
              and liq > 1.5 * (m.get("liq_usd") or 0) and vol24 >= 0.25 * liq]
    return "copycat" if bigger else None
