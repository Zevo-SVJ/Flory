# backtest.py
# does the desk's entry + exit have an edge, on tokens it never saw? replayed from the chain itself.
#   1. pick pump.fun graduations from a past window (pump.fun's migration account)
#   2. for each, read the PumpSwap pool's reserves along its first hours (the pool's own transactions):
#      price = SOL / tokens, liquidity = 2 x SOL, trades per hour, average swap
#   3. enter where the desk's pool rules would have (age, liquidity, fake cap, bot volume, dead volume),
#      exit with the desk's active exit profile (exits.py, same code as VIGIE), pay the real costs
#   4. report the return per trade after costs, its 95% interval, and how many entries a day
# what it cannot replay: the holder checks and the deep read (the chain doesn't keep yesterday's holder
# list cheaply), ECHO, and name factories. so it measures the pool rules + exits alone: a floor for
# the whole desk if the later checks help, the honest base rate either way.
# run:  python3 backtest.py 120        (with a Helius SOLANA_RPC in .env it is ~10x faster)
import json, os, random, statistics, sys, time
from config import DATA, FACTS, EXIT, PAPER_COSTS
import facts, exits

MIGRATION = "39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg"
WSOL = "So11111111111111111111111111111111111111112"
OUT = os.path.join(DATA, "backtest.json")
TICKET = 40.0                 # the desk's base ticket on a $1,000 balance (4%)
SAMPLE_S = 360                # one price point every 6 minutes
HORIZON_S = 7 * 3600          # entry window 3 h + exit window up to 6 h, capped at 7 h of history
MAX_PAGES = 100               # pools with more than 100,000 transactions since birth are skipped (noted)


def tx(sig: str) -> dict | None:
    for i in range(4):
        try:
            return facts._rpc("getTransaction", [sig, {"maxSupportedTransactionVersion": 1, "encoding": "jsonParsed"}])
        except Exception:
            time.sleep(1 + i)
    return None


def reserves(t: dict, pool: str, mint: str) -> tuple[float, float] | None:
    sol = tok = None
    for b in (t or {}).get("meta", {}).get("postTokenBalances") or []:
        if b.get("owner") == pool and b["mint"] == WSOL:
            sol = float(b["uiTokenAmount"]["uiAmount"] or 0)
        if b.get("owner") == pool and b["mint"] == mint:
            tok = float(b["uiTokenAmount"]["uiAmount"] or 0)
    return (sol, tok) if sol and tok else None


def graduates(h_from: float, h_to: float, n: int, seed: int = 11) -> list[dict]:
    """n random graduations between h_from and h_to hours ago: mint, pool, time."""
    now, sigs, before = time.time(), [], None
    while True:
        p = {"limit": 1000}
        if before:
            p["before"] = before
        page = facts._rpc("getSignaturesForAddress", [MIGRATION, p]) or []
        if not page:
            break
        sigs += page
        before = page[-1]["signature"]
        if page[-1]["blockTime"] < now - h_to * 3600:
            break
    window = [s for s in sigs if not s["err"] and now - h_to * 3600 <= s["blockTime"] <= now - h_from * 3600]
    random.Random(seed).shuffle(window)
    out, seen = [], set()
    for s in window:
        if len(out) >= n:
            break
        t = tx(s["signature"])
        if not t or not any("Migrate" in l for l in t["meta"].get("logMessages") or []):
            continue
        bals = [b for b in t["meta"].get("postTokenBalances") or [] if b["mint"] != WSOL]
        if not bals:
            continue
        big = max(bals, key=lambda b: float(b["uiTokenAmount"]["uiAmount"] or 0))   # the pool's token vault
        if big["mint"] in seen:
            continue
        seen.add(big["mint"])
        out.append({"mint": big["mint"], "pool": big["owner"], "t0": s["blockTime"]})
    return out


def pool_sigs(pool: str, t0: float) -> tuple[list[dict], bool]:
    """The pool's transactions from its creation to t0 + HORIZON_S, oldest first. False if too many."""
    sigs, before, pages = [], None, 0
    while pages < MAX_PAGES:
        p = {"limit": 1000}
        if before:
            p["before"] = before
        page = facts._rpc("getSignaturesForAddress", [pool, p]) or []
        pages += 1
        if not page:                      # reached the pool's first transaction
            return sorted(sigs, key=lambda s: s["blockTime"]), True
        sigs += [s for s in page if not s["err"] and s["blockTime"] and s["blockTime"] <= t0 + HORIZON_S]
        before = page[-1]["signature"]
        if page[-1]["blockTime"] <= t0:
            return sorted(sigs, key=lambda s: s["blockTime"]), True
    return [], False


def replay(g: dict, sol_usd: float) -> dict:
    sigs, complete = pool_sigs(g["pool"], g["t0"])
    if not complete:
        return {**g, "skip": "too_busy"}
    import bisect
    times = [s["blockTime"] for s in sigs]
    lo = bisect.bisect_left(times, g["t0"] + FACTS["min_age_min"] * 60)
    hi = bisect.bisect_left(times, g["t0"] + 3 * 3600)
    if hi - lo < 150:          # under 150 swaps in its whole entry window: no pool rule could pass
        return {**g, "skip": "dead_at_birth", "swaps": hi - lo}

    def at(t: float) -> dict | None:
        i = bisect.bisect_left(times, t)
        if i >= len(sigs):
            return None
        r = reserves(tx(sigs[i]["signature"]), g["pool"], g["mint"])
        if not r:
            return None
        sol, tok = r
        n1h = i - bisect.bisect_left(times, t - 3600)
        return {"t": t, "price": sol / tok * sol_usd, "liq": 2 * sol * sol_usd, "n1h": n1h, "i": i}

    def avg_trade(i: int) -> float | None:
        """Mean SOL moved per swap over 6 consecutive swaps, in dollars."""
        pts = [reserves(tx(s["signature"]), g["pool"], g["mint"]) for s in sigs[i:i + 7]]
        sols = [p[0] for p in pts if p]
        if len(sols) < 3:
            return None
        return statistics.mean(abs(a - b) for a, b in zip(sols, sols[1:])) * sol_usd

    entry = None
    for k in range(int(FACTS["min_age_min"] * 60 // SAMPLE_S), int(3 * 3600 // SAMPLE_S) + 1):
        s = at(g["t0"] + k * SAMPLE_S)
        if not s:
            break
        if s["liq"] < FACTS["min_liquidity_usd"] or s["price"] * 1e9 > FACTS["max_mcap_liq"] * s["liq"]:
            continue
        a = avg_trade(s["i"])
        if a is None:
            continue
        if s["n1h"] >= 100 and a < FACTS["min_avg_trade_usd"]:
            return {**g, "skip": "micro_trades", "age_min": k * SAMPLE_S / 60}
        if s["n1h"] * a < FACTS["min_turnover_1h"] * s["liq"]:
            continue
        entry = {**s, "avg_trade": a, "age_min": k * SAMPLE_S / 60}
        break
    if not entry:
        return {**g, "skip": "never_entered"}
    path = [entry]
    t = entry["t"]
    while t < min(entry["t"] + 6 * 3600, g["t0"] + HORIZON_S):
        t += SAMPLE_S
        s = at(t)
        if not s:                      # no swap after t: the pool is dead, last price stands
            break
        path.append(s)
    for p in path:
        p.update(b5=None, s5=None, v5=None)
    import exitlab
    gross = exitlab.simulate(exits.features(path), EXIT)
    if gross is None:
        return {**g, "skip": "no_path"}
    gross_r = gross / exitlab.TICKET_USD
    impact = 100 * TICKET / (entry["liq"] / 2)
    cost_r = (2 * (PAPER_COSTS["fee_pct"] + PAPER_COSTS.get("mev_pct", 0) + impact) / 100
              + 2 * PAPER_COSTS["tx_usd"] / TICKET)
    peak = max(p["price"] for p in path) / entry["price"] - 1
    return {**g, "entered": True, "age_min": entry["age_min"], "liq": round(entry["liq"]),
            "avg_trade": round(entry["avg_trade"], 1), "gross_pct": round(gross_r * 100, 1),
            "net_pct": round((gross_r - cost_r) * 100, 1), "peak_pct": round(peak * 100, 1),
            "hours": round((path[-1]["t"] - entry["t"]) / 3600, 1)}


def summary(rows: list[dict]) -> dict:
    ent = [r for r in rows if r.get("entered")]
    skips = {}
    for r in rows:
        if r.get("skip"):
            skips[r["skip"]] = skips.get(r["skip"], 0) + 1
    out = {"graduates": len(rows), "entries": len(ent), "skips": skips}
    if ent:
        net = [r["net_pct"] for r in ent]
        rng = random.Random(3)
        boots = sorted(statistics.mean(rng.choice(net) for _ in net) for _ in range(2000))
        out.update(mean_net_pct=round(statistics.mean(net), 2), median_net_pct=round(statistics.median(net), 2),
                   ci95=[round(boots[50], 2), round(boots[1949], 2)], win_rate=round(sum(x > 0 for x in net) / len(net), 2),
                   best=max(net), worst=min(net))
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    import market
    sol = market.pools([WSOL]).get(WSOL) or {}
    sol_usd = sol.get("price") or 190.0
    gs = graduates(7.5, 14, n)
    rows = []
    from concurrent.futures import ThreadPoolExecutor
    import threading
    lock = threading.Lock()

    def one(g):
        try:
            r = replay(g, sol_usd)
        except Exception as e:
            r = {**g, "skip": f"error {str(e)[:60]}"}
        with lock:
            rows.append(r)
            os.makedirs(DATA, exist_ok=True)
            with open(OUT, "w") as f:
                json.dump({"sol_usd": sol_usd, "rows": rows, "summary": summary(rows)}, f, indent=1)
            print(json.dumps(r), flush=True)

    with ThreadPoolExecutor(max_workers=int(os.environ.get("BT_WORKERS", "3"))) as ex:
        list(ex.map(one, gs))
    print(json.dumps(summary(rows), indent=2))
