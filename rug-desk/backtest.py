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
MAX_PAGES = 250               # pools with more than 250,000 transactions since birth are skipped (noted)


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

    # the whole first 7 h, one point every 6 min, kept in the output: entry and exit variants can be
    # replayed offline (variants()) without reading the chain again
    full = []
    for k in range(int(HORIZON_S // SAMPLE_S) + 1):
        s = at(g["t0"] + k * SAMPLE_S)
        if not s:
            break
        full.append(s)
    trade = {}
    for mins in (15, 30, 60, 120):          # average swap size at four ages, for the bot-volume rule
        s = next((p for p in full if p["t"] >= g["t0"] + mins * 60), None)
        if s:
            trade[mins] = avg_trade(s["i"])
    g = {**g, "path": [[round(p["t"] - g["t0"]), p["price"], round(p["liq"]), p["n1h"]] for p in full],
         "avg_trade": {k: (round(v, 1) if v else None) for k, v in trade.items()}}
    entry = None
    start = -(-int(FACTS["min_age_min"] * 60) // SAMPLE_S)        # ceil: never before min_age_min
    for k in range(start, int(3 * 3600 // SAMPLE_S) + 1):
        s = full[k] if k < len(full) else None
        if not s:
            break
        if s["liq"] < FACTS["min_liquidity_usd"] or s["price"] * 1e9 > FACTS["max_mcap_liq"] * s["liq"]:
            continue
        age = k * SAMPLE_S / 60
        a = next((v for m, v in sorted(trade.items(), reverse=True) if m <= age and v), None)
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
    path = [dict(p) for p in full if entry["t"] <= p["t"] <= entry["t"] + 6 * 3600]
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
            "entry_avg_trade": round(entry["avg_trade"], 1), "gross_pct": round(gross_r * 100, 1),
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


def sol_price() -> float:
    import market
    return (market.pools([WSOL]).get(WSOL) or {}).get("price") or 190.0


def replay_all(gs: list[dict], sol_usd: float, workers: int, on_row=None) -> list[dict]:
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
            if on_row:
                on_row(r, rows)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(one, gs))
    return rows


# ---------- the cumulative backtest: AUDIT adds a batch of fresh graduations every few hours ----------
HERE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(HERE, "seeds", "backtest_oct19.jsonl")
ROWS = os.path.join(DATA, "backtest_rows.jsonl")          # every graduation replayed so far, one a line
HISTORY = os.path.join(DATA, "backtest_history.jsonl")    # the scorecard after each run: the interval narrowing
STATE = os.path.join(DATA, "backtest_state.json")


def _jsonl(path: str) -> list[dict]:
    try:
        with open(path) as f:
            return [json.loads(l) for l in f if l.strip()]
    except (OSError, ValueError):
        return []


def rows_all() -> list[dict]:
    """The seed plus every row the desk added, one per mint (the latest wins)."""
    return list({r["mint"]: r for r in _jsonl(SEED) + _jsonl(ROWS)}.values())


def accumulate(n: int, h_from: float = 7.5, h_to: float = 14, workers: int = 2) -> int:
    """Replay n graduations the sample does not have yet and append them. Returns how many were added.
    a row that failed on a rate limit is not kept: its window passes, another graduation takes its place."""
    known = {r["mint"] for r in rows_all()}
    gs = [g for g in graduates(h_from, h_to, n * 2) if g["mint"] not in known][:n]
    if not gs:
        return 0
    os.makedirs(DATA, exist_ok=True)
    added = []        # keep() runs under replay_all's lock

    def keep(r, _rows):
        if str(r.get("skip", "")).startswith("error"):
            return
        with open(ROWS, "a") as f:
            f.write(json.dumps(r, separators=(",", ":")) + "\n")
        added.append(r["mint"])

    replay_all(gs, sol_price(), workers, keep)
    return len(added)


SCORECARD = {      # the rules the panel follows over time
    "early: old desk (15 min)": "old desk (15 min, rules)",
    "early: desk now (60 min + graduation)": "desk now (60 min + above graduation)",
}


def scorecard(rows: list[dict] | None = None) -> dict:
    """Per followed rule, with the active exit: n, mean net % per trade, 95% interval, both halves.
    plus the momentum lane (mbacktest.py) and the verdict each one earns (edge.judge)."""
    import edge, mbacktest
    rows = rows_all() if rows is None else rows
    by = {v["entry"]: v for v in variants(rows, exits_only=("actif",))}
    out = {"graduates": len(rows), "rules": {}}
    for label, rule in SCORECARD.items():
        v = by.get(rule)
        if v:
            out["rules"][label] = {**v, **edge.judge(v["n"], v["mean"], v["ci95"][0])}
    m = mbacktest.scorecard()
    if m:
        out["rules"]["momentum: desk rule"] = {**m, **edge.judge(m["n"], m["mean"], m["ci95"][0])}
    out["sightings"] = mbacktest.n_sightings()
    return out


def record_history(card: dict):
    with open(HISTORY, "a") as f:
        f.write(json.dumps({"t": time.time(), "graduates": card["graduates"],
                            "rules": {k: {x: v[x] for x in ("n", "mean", "ci95")} for k, v in card["rules"].items()}}) + "\n")


def history(last: int = 30) -> list[dict]:
    return _jsonl(HISTORY)[-last:]


def run_batch() -> dict:
    """One automatic run (agents.py starts it in a child process every SCHEDULE['backtest_every_h']):
    momentum first (GeckoTerminal, no key), then fresh graduations if the RPC is Helius (the public RPC
    rate-limits a replay and would slow the desk's own reads). writes the scorecard and its history."""
    from config import SCHEDULE
    import mbacktest
    st = {"started": time.time()}
    try:
        st["momentum_added"] = mbacktest.run(SCHEDULE.get("backtest_momentum_n", 40))
    except Exception as e:
        st["momentum_error"] = str(e)[:160]
    if "helius" in facts.RPC_URL:
        try:
            st["early_added"] = accumulate(SCHEDULE.get("backtest_n", 40))
        except Exception as e:
            st["early_error"] = str(e)[:160]
    else:
        st["early_error"] = "SOLANA_RPC n'est pas Helius : graduations non rejouées (le RPC public limite)"
    card = scorecard()
    record_history(card)
    st.update(finished=time.time(), card=card)
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f)
    os.replace(tmp, STATE)
    return st


if __name__ == "__main__":
    if sys.argv[1:] == ["--accumulate"]:
        try:
            os.nice(10)                  # the desk's own reads come first
        except OSError:
            pass
        print(json.dumps(run_batch()["card"], indent=1))
        sys.exit(0)
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    sol_usd = sol_price()
    h_from, h_to = (float(x) for x in os.environ.get("BT_WINDOW", "7.5,14").split(","))
    gs = graduates(h_from, h_to, n)

    def show(r, rows):
        os.makedirs(DATA, exist_ok=True)
        with open(OUT, "w") as f:
            json.dump({"sol_usd": sol_usd, "rows": rows, "summary": summary(rows)}, f, indent=1)
        print(json.dumps(r), flush=True)

    rows = replay_all(gs, sol_usd, int(os.environ.get("BT_WORKERS", "3")), show)
    print(json.dumps(summary(rows), indent=2))


# ---------- offline variants: replay other entry and exit rules on the recorded paths ----------
ENTRY_RULES = {
    "old desk (15 min, rules)": {"min_age": 15},
    "wait 30 min": {"min_age": 30},
    "wait 60 min": {"min_age": 60},
    "above graduation price": {"above_t0": 1.0},
    "rising 30 min (+10%)": {"rise_30m": 0.10},
    "pool $30k+": {"min_liq": 30000},
    "desk now (60 min + above graduation)": {"min_age": 60, "above_t0": 1.0},
}


def _entry(row: dict, rule: dict) -> int | None:
    path = row.get("path") or []
    if not path:
        return None
    p0 = path[0][1]
    at = row.get("avg_trade")
    trade = {int(k): v for k, v in at.items()} if isinstance(at, dict) else {0: at}
    for k, (t, price, liq, n1h) in enumerate(path):
        age = t / 60
        if age < rule.get("min_age", FACTS["min_age_min"]) or age > 180:
            continue
        if liq < rule.get("min_liq", FACTS["min_liquidity_usd"]) or price * 1e9 > FACTS["max_mcap_liq"] * liq:
            continue
        a = next((v for m, v in sorted(trade.items(), reverse=True) if m <= age and v), None)
        if a is None or (n1h >= 100 and a < FACTS["min_avg_trade_usd"]) or n1h * a < FACTS["min_turnover_1h"] * liq:
            continue
        if price < rule.get("above_t0", 0) * p0:
            continue
        if "rise_30m" in rule:
            back = next((q for q in reversed(path[:k]) if q[0] <= t - 1800), None)
            if not back or price < back[1] * (1 + rule["rise_30m"]):
                continue
        return k
    return None


def _net(row: dict, k: int, params: dict) -> float | None:
    import exitlab
    t_in = row["path"][k][0]
    pts = [{"t": t, "price": price, "liq": liq, "b5": None, "s5": None, "v5": None}
           for t, price, liq, _ in row["path"][k:] if t <= t_in + 6 * 3600]
    gross = exitlab.simulate(exits.features(pts), params)
    if gross is None:
        return None
    impact = 100 * TICKET / (pts[0]["liq"] / 2)
    cost = 2 * (PAPER_COSTS["fee_pct"] + PAPER_COSTS.get("mev_pct", 0) + impact) / 100 + 2 * PAPER_COSTS["tx_usd"] / TICKET
    return (gross / exitlab.TICKET_USD - cost) * 100


def variants(rows: list[dict], exits_only: tuple = ()) -> list[dict]:
    """Every entry rule x every exit profile, with the two halves (by graduation time) kept apart:
    a rule that only wins on one half is luck, not an edge."""
    import exitlab
    live = sorted((r for r in rows if r.get("path")), key=lambda r: r["t0"])
    half = len(live) // 2
    profiles = {"actif": EXIT, **{n: {**EXIT, **p} for n, p in exitlab.PROFILES.items()}}
    out = []
    if exits_only:
        profiles = {k: v for k, v in profiles.items() if k in exits_only}
    for en, rule in ENTRY_RULES.items():
        for pn, params in profiles.items():
            res = []
            for i, r in enumerate(live):
                k = _entry(r, rule)
                if k is None:
                    continue
                x = _net(r, k, params)
                if x is not None:
                    res.append((i < half, x))
            if not res:
                continue
            xs = [x for _, x in res]
            a = [x for h, x in res if h]
            b = [x for h, x in res if not h]
            rng = random.Random(5)
            boots = sorted(statistics.mean(rng.choice(xs) for _ in xs) for _ in range(1000))
            out.append({"entry": en, "exit": pn, "n": len(xs), "mean": round(statistics.mean(xs), 1),
                        "ci95": [round(boots[25], 1), round(boots[974], 1)],
                        "win": round(sum(x > 0 for x in xs) / len(xs), 2),
                        "half1": round(statistics.mean(a), 1) if a else None,
                        "half2": round(statistics.mean(b), 1) if b else None})
    return sorted(out, key=lambda v: -v["mean"])
