# mbacktest.py
# the momentum lane, replayed. a survivor older than 72 h is bought on its move (market.momentum_kill);
# does that move carry on after costs, or is it where the late buyers pay the early ones?
#
# no survivorship bias: the universe is what SCOUT saw at the time (note(), every run), never "the tokens
# that are big today". a token that died after the sighting stays in the sample.
#   1. note(): every momentum-lane pool SCOUT sees with $100k+ liquidity, at most once per 6 h per token
#   2. run(): for each sighting at least 7 h old, read GeckoTerminal's 5-min candles around it (one free
#      call), look for the desk's entry rule in the hour after the sighting, exit with the active profile
#      over 6 h, pay the real costs. one row per sighting in data/mbacktest_rows.jsonl
# what it cannot replay: buys vs sells (candles have no side), the liquidity along the way (the sighting's
# is used), and moves inside a 5-min candle (VIGIE ticks every 20 s). the holder checks are not replayed.
import json, os, random, statistics, time
import requests
from config import DATA, EXIT, MOMENTUM, FACTS, PAPER_COSTS
import exits

SEEN = os.path.join(DATA, "momentum_seen.jsonl")
ROWS = os.path.join(DATA, "mbacktest_rows.jsonl")
OHLCV = "https://api.geckoterminal.com/api/v2/networks/solana/pools/{}/ohlcv/minute"
CANDLE_S = 300
ENTRY_WINDOW_S = 3600          # SCOUT sees a trending token every 3 min while it trends: one hour to fire
HOLD_S = 6 * 3600
LOOKBACK_S = 24 * 3600         # chg_24h and vol_24h need the day before
EVERY_S = 6 * 3600             # one sighting per token per 6 h
TICKET = 40.0
GAP_S = 3.0                    # between GeckoTerminal calls: the free API allows about 30 a minute


def _jsonl(path: str) -> list[dict]:
    try:
        with open(path) as f:
            return [json.loads(l) for l in f if l.strip()]
    except (OSError, ValueError):
        return []


_last_seen = {}


def note(live: dict):
    """Called by SCOUT with every pool it read this run. Never raises."""
    try:
        if not _last_seen:
            for s in _jsonl(SEEN):
                _last_seen[s["mint"]] = max(_last_seen.get(s["mint"], 0), s["t"])
        now, new = time.time(), []
        import market
        for mint, m in live.items():
            if not m or not m.get("pair") or market.lane(m) != "momentum":
                continue
            if (m.get("liq_usd") or 0) < MOMENTUM["min_liq_usd"] or now - _last_seen.get(mint, 0) < EVERY_S:
                continue
            _last_seen[mint] = now
            new.append({"mint": mint, "pair": m["pair"], "symbol": m.get("symbol"), "t": round(now),
                        "liq": round(m["liq_usd"]), "mcap": m.get("mcap"), "avg_trade": m.get("avg_trade_1h"),
                        "n1h": (m.get("buys_1h") or 0) + (m.get("sells_1h") or 0)})
        if new:
            os.makedirs(DATA, exist_ok=True)
            with open(SEEN, "a") as f:
                f.writelines(json.dumps(s) + "\n" for s in new)
    except Exception:
        pass


def n_sightings() -> int:
    return len(_jsonl(SEEN))


def candles(pair: str, end: float) -> list[tuple]:
    """5-min candles (t, open, high, low, close, volume $) ending at `end`, oldest first."""
    n = int((LOOKBACK_S + ENTRY_WINDOW_S + HOLD_S) / CANDLE_S) + 4
    for attempt in range(3):
        r = requests.get(OHLCV.format(pair), params={"aggregate": 5, "limit": min(1000, n),
                                                      "before_timestamp": int(end), "currency": "usd"},
                         headers={"accept": "application/json"}, timeout=20)
        if r.status_code == 404:          # GeckoTerminal does not index this pool
            return []
        if r.status_code == 429:
            time.sleep(30 * (attempt + 1))
            continue
        r.raise_for_status()
        rows = ((r.json().get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
        return sorted(tuple(float(x) for x in c) for c in rows)
    raise RuntimeError("GeckoTerminal 429 three times")


def _at(cs: list[tuple], t: float) -> float | None:
    """Close of the last candle that ended at or before t."""
    best = None
    for c in cs:
        if c[0] + CANDLE_S > t:
            break
        best = c[4]
    return best


def _vol(cs: list[tuple], t0: float, t1: float) -> float:
    return sum(c[5] for c in cs if t0 < c[0] + CANDLE_S <= t1)


def signal(cs: list[tuple], t: float) -> dict | None:
    """The momentum lane's numbers at time t, from candles only."""
    p, p5, p1h, p24 = _at(cs, t), _at(cs, t - 300), _at(cs, t - 3600), _at(cs, t - 86400)
    if not p or not p5 or not p1h:
        return None
    return {"price": p, "chg_5m": (p / p5 - 1) * 100, "chg_1h": (p / p1h - 1) * 100,
            "chg_24h": (p / p24 - 1) * 100 if p24 else 0.0,
            "vol_1h": _vol(cs, t - 3600, t), "vol_6h": _vol(cs, t - 6 * 3600, t), "vol_24h": _vol(cs, t - 86400, t)}


def enters(s: dict, sight: dict) -> bool:
    """market.momentum_kill on candle numbers (no buy/sell split), plus the pool checks from the sighting."""
    p = MOMENTUM
    if sight.get("mcap") and sight["mcap"] > p["max_mcap_liq"] * sight["liq"]:
        return False
    if (sight.get("n1h") or 0) >= 100 and (sight.get("avg_trade") or 1e9) < FACTS["min_avg_trade_usd"]:
        return False
    return (s["vol_24h"] >= p["min_vol_24h"] and s["chg_1h"] <= p["max_chg_1h"] and s["chg_24h"] <= p["max_chg_24h"]
            and s["chg_1h"] >= p["min_chg_1h"] and s["chg_5m"] >= p["min_chg_5m"]
            and s["vol_1h"] >= p["vol_accel"] * s["vol_6h"] / 6)


def replay(sight: dict, cs: list[tuple] | None = None) -> dict:
    t0 = sight["t"]
    cs = cs if cs is not None else candles(sight["pair"], t0 + ENTRY_WINDOW_S + HOLD_S + CANDLE_S)
    if len(cs) < 20:
        return {**sight, "skip": "no_candles"}
    grid = [c[0] + CANDLE_S for c in cs if t0 <= c[0] + CANDLE_S <= t0 + ENTRY_WINDOW_S]
    entry = next((t for t in grid if (s := signal(cs, t)) and enters(s, sight)), None)
    if entry is None:
        return {**sight, "skip": "no_signal"}
    path = [{"t": c[0] + CANDLE_S, "price": c[4], "liq": sight["liq"], "b5": None, "s5": None, "v5": c[5]}
            for c in cs if entry <= c[0] + CANDLE_S <= entry + HOLD_S]
    if len(path) < 2:
        return {**sight, "skip": "no_path"}
    import exitlab
    gross = exitlab.simulate(exits.features(path), EXIT)
    if gross is None:
        return {**sight, "skip": "no_path"}
    impact = 100 * TICKET / (sight["liq"] / 2)
    cost = 2 * (PAPER_COSTS["fee_pct"] + PAPER_COSTS.get("mev_pct", 0) + impact) / 100 + 2 * PAPER_COSTS["tx_usd"] / TICKET
    net = (gross / exitlab.TICKET_USD - cost) * 100
    return {**sight, "entered": True, "entry_t": entry, "wait_min": round((entry - t0) / 60),
            "net_pct": round(net, 1), "peak_pct": round((max(p["price"] for p in path) / path[0]["price"] - 1) * 100, 1)}


def _bootstrap():
    """First run on a desk that already traded the momentum lane: SCOUT's dossiers hold the momentum
    tokens it handed to GARDE, with the time it saw them. their pool is looked up once."""
    if os.path.exists(SEEN):
        return
    import dossier, market
    found = []
    try:
        names = os.listdir(dossier.DIR)
    except OSError:
        names = []
    for name in names:
        if not name.endswith(".json"):
            continue
        d = dossier.load(name[:-5])
        for e in d.get("entries", []):
            if e.get("agent") == "SCOUT" and e.get("lane") == "momentum" and e.get("liq_usd"):
                found.append({"mint": d["mint"], "t": round(e["t"]), "liq": e["liq_usd"],
                              "avg_trade": e.get("avg_trade"), "symbol": None})
                break
    if not found:
        return
    pools = market.pools([f["mint"] for f in found])
    rows = []
    for f in found:
        m = pools.get(f["mint"]) or {}
        if m.get("pair"):
            rows.append({**f, "pair": m["pair"], "symbol": m.get("symbol"), "n1h": 0, "boot": True})
    os.makedirs(DATA, exist_ok=True)
    with open(SEEN, "w") as fh:
        fh.writelines(json.dumps(r) + "\n" for r in rows)


def run(max_n: int = 40) -> int:
    """Replay the sightings old enough to have their 7 h, not replayed yet. Returns how many were added."""
    _bootstrap()
    done = {(r["mint"], r["t"]) for r in _jsonl(ROWS)}
    ready = [s for s in _jsonl(SEEN) if s["t"] + ENTRY_WINDOW_S + HOLD_S + CANDLE_S < time.time()
             and (s["mint"], s["t"]) not in done]
    added = 0
    for s in ready[:max_n]:
        try:
            r = replay(s)
        except Exception as e:
            r = {**s, "skip": f"error {str(e)[:60]}"}
        # a failed read is retried next run, unless the sighting is 3 days old: then it is kept as failed
        if not str(r.get("skip", "")).startswith("error") or time.time() - s["t"] > 3 * 86400:
            with open(ROWS, "a") as f:
                f.write(json.dumps(r) + "\n")
            added += 1
        time.sleep(GAP_S)
    return added


def scorecard(rows: list[dict] | None = None) -> dict | None:
    """n, mean net % per trade, 95% interval, both halves (by sighting time)."""
    rows = _jsonl(ROWS) if rows is None else rows
    ent = sorted((r for r in rows if r.get("entered")), key=lambda r: r["t"])
    if not ent:
        return None
    xs = [r["net_pct"] for r in ent]
    half = len(xs) // 2
    rng = random.Random(5)
    boots = sorted(statistics.mean(rng.choice(xs) for _ in xs) for _ in range(1000))
    return {"entry": "momentum", "exit": "actif", "n": len(xs), "mean": round(statistics.mean(xs), 1),
            "ci95": [round(boots[25], 1), round(boots[974], 1)], "win": round(sum(x > 0 for x in xs) / len(xs), 2),
            "half1": round(statistics.mean(xs[:half]), 1) if half else None,
            "half2": round(statistics.mean(xs[half:]), 1) if xs[half:] else None,
            "sightings": len(rows)}


if __name__ == "__main__":
    print(run(), "sighting(s) replayed")
    print(json.dumps(scorecard(), indent=1))
