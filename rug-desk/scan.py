# scan.py
# SCOUT's lead sources, all free DexScreener reads:
#   - tokens that paid for a profile or a boost (paying is not a quality signal, the dev spent money)
#   - the DexScreener search, a rotating set of words, kept to PumpSwap pools in the age window.
#     it finds survivors the paid lists miss (6 vs 3 on the first live test)
# the filter decides the rest.
import csv, json, os, time
import requests
from config import LOG, SCHEDULE, FACTS
import check, market, grads
from market import market_kill

SOURCES = ["token-profiles/latest/v1", "token-boosts/latest/v1", "token-boosts/top/v1",
           "token-profiles/recent-updates/v1", "community-takeovers/latest/v1", "ads/latest/v1"]
SEARCH = "https://api.dexscreener.com/latest/dex/search"
WORDS = ["pump", "sol", "cat", "dog", "ai", "meme", "pepe", "inu", "moon", "coin", "frog", "baby",
         "gm", "based", "wif", "bonk", "agent", "cto", "degen", "sigma", "trump", "elon", "chill",
         "king", "god", "super", "core", "luke", "gato", "gold", "the", "one", "x", "bull", "bear"]
WORDS_PER_RUN = 12          # DexScreener allows 300 searches a minute; this is 12 every 10 minutes
_turn = 0
grad_error = None           # the on-chain graduation feed's last failure, shown by SCOUT
# kills that can change with time: a pool grows up, a source comes back. retried after this long
RETRY_AFTER_MIN = 30
RETRYABLE = ("too_fresh", "thin_pool", "no_pool", "no_price", "no_holders")


def _done() -> set[str]:
    """Mints we never need to look at again: a final verdict, or a retryable kill that's still recent."""
    if not os.path.exists(LOG):
        return set()
    last = {}
    with open(LOG, newline="") as f:
        for r in csv.DictReader(f):
            last[r["mint"]] = r
    cutoff = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - RETRY_AFTER_MIN * 60))
    done = set()
    for mint, r in last.items():
        reason = r["reason"] or ""
        retry = reason in RETRYABLE or " failed" in reason or r["stage"] == "limits"
        if not retry or r["time"] > cutoff:
            done.add(mint)
    return done


NARRATIVES = os.path.join(os.path.dirname(LOG), "narratives.txt")   # written by ECHO from X, 1 word a line


def narratives() -> list[str]:
    """ECHO's narrative scan: what X is about to turn into memecoins. Fresh words only (6 h)."""
    if not os.path.exists(NARRATIVES) or time.time() - os.path.getmtime(NARRATIVES) > 6 * 3600:
        return []
    with open(NARRATIVES) as f:
        return [w.strip().lstrip("$").lower() for w in f if w.strip() and not w.startswith("#")][:10]


def searched(trending: list[str] = ()) -> list[str]:
    """PumpSwap pools from the DexScreener search: today's trending tickers (narratives breed
    look-alikes) plus a rotating set of generic WORDS, run after run."""
    global _turn
    words = list(dict.fromkeys([w for w in narratives() if len(w) >= 3]
                               + [w.lower() for w in trending if w and len(w) >= 3]))[:WORDS_PER_RUN * 2 // 3]
    words += [WORDS[(_turn + i) % len(WORDS)] for i in range(WORDS_PER_RUN - len(words))]
    _turn = (_turn + WORDS_PER_RUN) % len(WORDS)
    now_ms, out = time.time() * 1000, []
    for w in words:
        try:
            r = requests.get(SEARCH, params={"q": w}, timeout=15)
            r.raise_for_status()
        except Exception:
            continue                          # one failed word is not an outage; the next run retries
        data = r.json()
        for p in (data.get("pairs") if isinstance(data, dict) else None) or []:
            age_h = (now_ms - (p.get("pairCreatedAt") or 0)) / 3.6e6
            a = (p.get("baseToken") or {}).get("address")
            if (p.get("chainId") == "solana" and p.get("dexId") == "pumpswap" and a and a not in out
                    and FACTS["min_age_min"] / 60 <= age_h <= FACTS["max_age_hours"]
                    and ((p.get("liquidity") or {}).get("usd") or 0) >= FACTS["min_liquidity_usd"]):
                out.append(a)
    return out


def leads() -> list[str]:
    done, out, errors = _done(), [], []
    for src in SOURCES:
        try:
            r = requests.get(f"https://api.dexscreener.com/{src}", timeout=15)
            r.raise_for_status()
        except Exception as e:
            errors.append(f"{src}: {e}")
            continue
        for t in r.json():
            a = t.get("tokenAddress")
            if t.get("chainId") == "solana" and a and a not in done and a not in out:
                out.append(a)
    live = market.pools(out)
    trending = [(live[m] or {}).get("symbol") for m in out if live.get(m) and not market_kill(live[m])]
    found = searched(trending)
    if len(errors) == len(SOURCES) and not found:
        raise RuntimeError("; ".join(errors))
    out += [a for a in found if a not in done and a not in out]
    # every pump.fun graduation, read on chain: the one source that sees each new PumpSwap pool
    global grad_error
    try:
        grads.fetch()
        grad_error = None
    except Exception as e:
        grad_error = f"pump.fun graduations unreadable: {e}"[:200]
    graduates = [a for a in grads.recent() if a not in done and a not in out]
    out += graduates
    # one batched pool read for every lead: most are bonding-curve tokens with no real pool yet.
    # they are not logged, they just come back next run, so the slots go to tokens that can pass
    live.update(market.pools([m for m in out if m not in live]))
    # a graduate whose pool stayed under $10k two hours after graduating is dead: stop pricing it
    born = grads.load()["mints"]
    grads.forget([m for m in graduates if time.time() - born.get(m, time.time()) > 7200
                  and ((live.get(m) or {}).get("liq_usd") or 0) < 10000])
    ok = [m for m in out if not market_kill(live[m])]
    # best pools first, so the per-run cap keeps the tradeable ones
    ok.sort(key=lambda m: -(live[m].get("vol_1h") or 0))
    return ok[:SCHEDULE["scan_per_run"]]


def scan() -> list[dict]:
    return [{"mint": m, **check.run(m)} for m in leads()]


if __name__ == "__main__":
    for v in scan():
        print(json.dumps(v))
