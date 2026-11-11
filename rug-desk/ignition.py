# ignition.py
# the moment a Solana memecoin ignites, measured. Skide's examples (FLOAT, mihao, PUSSY...) all show the same
# shape: a quiet token, then a burst of buyers and volume, a run, then a fall. the desk does not buy Solana:
# every entry tried there lost (passes -20%, the 15 min graduates -45% each). this lab tells, without buying
# anything, whether entering on the ignition and selling fast near the peak pays:
#   - at every SCOUT run, every Solana pool SCOUT priced is checked for an ignition (IGNITE below)
#   - the token is logged once (not again for 6 h) and priced every 20 s for 3 h like any ghost
#   - python3 ignition.py: from the first price after the signal, what fast exits would have made, net of the
#     costs of a $25 round trip, by the token's age at the signal
# nothing is bought, no pause, no balance, no rule of the desk changes: a lab apart (the lesson of sol15).
import csv, os, statistics, time
from config import DATA

FILE = os.path.join(DATA, "ignition.csv")
FIELDS = ["t", "mint", "symbol", "age_min", "mcap", "liq", "chg_5m", "chg_1h", "buys_5m", "sells_5m", "price"]
IGNITE = {"chg_5m": 8.0, "chg_1h": 20.0, "buy_ratio": 1.5, "min_liq": 15000, "max_mcap": 30e6, "vol_share": 0.2}
REPEAT_S = 6 * 3600
WATCH_H = 3
EXITS = {"retournement -10 %": 10, "retournement -20 %": 20}
FIXED = (5, 15, 30, 60)


def ignites(m: dict) -> bool:
    """A burst: +8% in 5 min and +20% in 1 h, buyers 1.5x the sellers over 5 min, a fifth of the hour's volume
    in the last 5 min, a real pool, not already a big cap."""
    if not m or (m.get("chain") or "solana") != "solana" or (m.get("price") or 0) <= 0:
        return False
    b, s = m.get("buys_5m") or 0, m.get("sells_5m") or 0
    return ((m.get("chg_5m") or 0) >= IGNITE["chg_5m"] and (m.get("chg_1h") or 0) >= IGNITE["chg_1h"]
            and b >= IGNITE["buy_ratio"] * max(1, s) and (m.get("liq_usd") or 0) >= IGNITE["min_liq"]
            and 0 < (m.get("mcap") or 0) <= IGNITE["max_mcap"]
            and (m.get("vol_5m") or 0) >= IGNITE["vol_share"] * max(1.0, m.get("vol_1h") or 0))


def _rows() -> list[dict]:
    try:
        with open(FILE, newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def note(live: dict, now: float | None = None) -> int:
    """Called by SCOUT with the pools it priced. Returns how many ignitions were logged."""
    import paths
    now = now or time.time()
    last = {}
    for r in _rows():
        last[r["mint"]] = max(last.get(r["mint"], 0.0), float(r["t"]))
    n = 0
    for mint, m in live.items():
        if not ignites(m) or now - last.get(mint, -1e18) < REPEAT_S:
            continue
        os.makedirs(DATA, exist_ok=True)
        new = not os.path.exists(FILE)
        with open(FILE, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if new:
                w.writeheader()
            w.writerow({"t": round(now), "mint": mint, "symbol": m.get("symbol"), "age_min": m.get("age_min"),
                        "mcap": round(m.get("mcap") or 0), "liq": round(m.get("liq_usd") or 0),
                        "chg_5m": m.get("chg_5m"), "chg_1h": m.get("chg_1h"), "buys_5m": m.get("buys_5m"),
                        "sells_5m": m.get("sells_5m"), "price": m.get("price")})
        paths.haunt(mint, WATCH_H)
        n += 1
    return n


def _net(pts: list[dict], p0: float, exit_at: float, cost: float) -> float:
    return 100 * (exit_at / p0 - 1) - cost


def report() -> list[str]:
    import paths, chains
    rows = _rows()
    if not rows:
        return ["ignition : aucun départ repéré pour l'instant (SCOUT les note à chaque passage)"]
    res = {}
    for r in rows:
        t = float(r["t"])
        pts = [p for p in paths.load(r["mint"], since=t, until=t + WATCH_H * 3600) if p["price"] > 0]
        if len(pts) < 10 or pts[-1]["t"] < t + 3600:
            continue
        p0 = pts[0]["price"]
        c = chains.costs(r["mint"])
        liq = float(r["liq"] or 0) or 1e9
        cost = 2 * (c["fee_pct"] + c.get("mev_pct", 0) + 100 * 25 / (liq / 2)) + 2 * c["tx_usd"] / 25 * 100
        age = float(r["age_min"] or 0)
        band = "moins d'1 h" if age < 60 else "1 à 24 h" if age < 1440 else "plus de 24 h"
        out = {}
        for name, k in EXITS.items():            # out on the turn: k% under the high since the signal, 3 h at most
            peak, sold = p0, pts[-1]["price"]
            for p in pts[1:]:
                peak = max(peak, p["price"])
                if p["price"] <= peak * (1 - k / 100):
                    sold = p["price"]
                    break
            out[name] = _net(pts, p0, sold, cost)
        half, peak, rest = None, p0, None         # half at x2, the rest on a 15% turn
        for p in pts[1:]:
            peak = max(peak, p["price"])
            if half is None and p["price"] >= 2 * p0:
                half = p["price"]
            if p["price"] <= peak * 0.85:
                rest = p["price"]
                break
        rest = rest or pts[-1]["price"]
        out["moitié à x2, reste -15 %"] = _net(pts, p0, ((half or rest) + rest) / 2, cost)
        for h in FIXED:
            later = [p for p in pts if p["t"] >= pts[0]["t"] + h * 60]
            if later:
                out[f"revendu à {h} min"] = _net(pts, p0, later[0]["price"], cost)
        out["sommet atteint (impossible à viser)"] = 100 * (max(p["price"] for p in pts) / p0 - 1)
        for k, v in out.items():
            res.setdefault((k, "tous"), []).append(v)
            res.setdefault((k, band), []).append(v)
    if not res:
        return [f"ignition : {len(rows)} départ(s) repéré(s), suivis 1 h au moins avant d'être jugés"]
    lines = [f"ignition : {len(rows)} départ(s) repéré(s) sur Solana · jugés sur {len(res[('revendu à 5 min', 'tous')]) if ('revendu à 5 min', 'tous') in res else 0}"]
    for (k, band), xs in sorted(res.items(), key=lambda kv: (kv[0][1] != "tous", kv[0][1], kv[0][0])):
        if len(xs) < 3:
            continue
        h = len(xs) // 2
        lines.append(f"  {band:12s} · {k:36s} n {len(xs):>4} · moyenne {statistics.mean(xs):+7.1f} % · médiane "
                     f"{statistics.median(xs):+7.1f} % · gagnants {100 * sum(x > 0 for x in xs) / len(xs):3.0f} % · "
                     f"moitiés {statistics.mean(xs[:h]):+.1f} / {statistics.mean(xs[h:]):+.1f}")
    return lines


if __name__ == "__main__":
    print("\n".join(report()))
