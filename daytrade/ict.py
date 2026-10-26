# ict.py
# the ICT setups traders post about, turned into fixed rules and replayed on every day since 2016.
#   python3 ict.py                         (SPY, a proxy for ES)
#   DAYTRADE_SYMBOL=QQQ python3 ict.py     (QQQ, a proxy for NQ)
#
# vocabulary, as coded here (5-minute candles, regular session only):
#   bullish FVG at candle k : low[k] > high[k-2]   the gap (high[k-2], low[k]) was skipped by a fast move up
#   bearish FVG at candle k : high[k] < low[k-2]
#   liquidity               : the previous day's high / low, and the high / low of the first 30 minutes;
#                             stops rest just beyond them
#   sweep                   : price trades beyond one of those levels (takes the stops), then turns
#   IFVG (inverse FVG)      : an FVG that price closes straight through; it flips sides, and the close
#                             through it is the entry
#
# SILVER BULLET (long; short is the mirror): between 10:00 and 11:00, after a sweep of a low, a bullish FVG
#   forms; buy the retrace to the top of the gap. stop just below the swept low. target 2R.
# IFVG REVERSAL (long): a bearish FVG forms on the way down, a low is swept, then a candle closes above the
#   FVG before 12:00; buy that close. stop just below the swept low. target 2R.
# both: one trade per setup per day, out at the close at the latest. if stop and target are hit in the same
# minute, the stop counts. a limit fills only if price trades a cent through it.
import json, math, sys
from config import ICT, COSTS, SYMBOL
import data
import strategy

TICK = 0.01


def candles(bars: list[dict], size: int) -> list[dict]:
    """1-minute bars -> size-minute candles {s, e, o, h, l, c}: s / e = first minute, minute after the last."""
    out = {}
    for b in bars:
        g = b["m"] // size
        c = out.get(g)
        if c is None:
            out[g] = {"s": g * size, "e": (g + 1) * size, "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"]}
        else:
            c["h"], c["l"], c["c"] = max(c["h"], b["h"]), min(c["l"], b["l"]), b["c"]
    return [out[g] for g in sorted(out)]


def mirror(bars: list[dict]) -> list[dict]:
    """Prices negated: a short setup becomes a long one, so each rule is written once."""
    return [{**b, "o": -b["o"], "h": -b["l"], "l": -b["h"], "c": -b["c"]} for b in bars]


def levels(prev: dict | None, bars: list[dict]) -> list[tuple[int, float]]:
    """(minute from which the level exists, price) for the lows liquidity rests under."""
    out = []
    if prev:
        out.append((0, prev["l"]))
    first = [b for b in bars if b["m"] < 30]
    if first:
        out.append((30, min(b["l"] for b in first)))
    return out


def sweeps(bars: list[dict], lv: list[tuple[int, float]]) -> dict[int, float]:
    """minute -> lowest low since the first sweep, for every minute at or after that sweep."""
    out, low, swept = {}, None, False
    for b in bars:
        if not swept and any(b["m"] >= since and b["l"] < px for since, px in lv):
            swept = True
        if swept:
            low = b["l"] if low is None else min(low, b["l"])
            out[b["m"]] = low
    return out


def manage(bars: list[dict], start_m: int, entry: float, stop: float, target: float) -> tuple[float, int]:
    """Exit price and minute, walking 1-minute bars from the fill minute. stop first when both are touched."""
    for b in bars:
        if b["m"] < start_m:
            continue
        if b["l"] <= stop:
            return stop, b["m"]
        if b["h"] >= target:
            return target, b["m"]
    return bars[-1]["c"], bars[-1]["m"]


def _trade(bars, fill_m, entry, stop, p):
    if entry - stop < p["min_risk_pct"] / 100 * abs(entry):
        return None
    target = entry + p["target_r"] * (entry - stop)
    px, m = manage(bars, fill_m, entry, stop, target)
    return {"m": fill_m, "entry": entry, "stop": stop, "exit": px, "exit_m": m, "r": (px - entry) / (entry - stop)}


def silver_bullet(bars: list[dict], prev: dict | None, p: dict = ICT) -> dict | None:
    lo, hi = p["sb_window"]
    sw = sweeps(bars, levels(prev, bars))
    cs = candles(bars, p["bar_min"])
    for k in range(2, len(cs)):
        c, a = cs[k], cs[k - 2]
        if not (lo < c["e"] <= hi):
            continue
        gap = c["l"] - a["h"]
        if gap < p["min_gap_pct"] / 100 * abs(c["c"]) or (c["e"] - 1) not in sw:
            continue
        entry, stop = c["l"], sw[c["e"] - 1] - TICK     # stop below the swept low, as known when the gap formed
        for b in bars:                                   # the retrace into the gap, before 11:00
            if b["m"] < c["e"] or b["m"] >= hi:
                continue
            if b["l"] <= entry - TICK:
                return _trade(bars, b["m"], entry, stop, p)
        # not filled: the next FVG of the window may still give a trade
    return None


def ifvg(bars: list[dict], prev: dict | None, p: dict = ICT) -> dict | None:
    lo, hi = p["ifvg_window"]
    sw = sweeps(bars, levels(prev, bars))
    cs = candles(bars, p["bar_min"])
    gaps = []                                            # tops of the bearish FVGs still open
    for k in range(2, len(cs)):
        c, a = cs[k], cs[k - 2]
        if lo < c["e"] <= hi and (c["e"] - 1) in sw:
            for top in gaps:
                if c["c"] > top:
                    nxt = [b for b in bars if b["m"] >= c["e"]]
                    if not nxt:
                        return None
                    entry = nxt[0]["o"]                  # bought at the next minute's open
                    return _trade(bars, nxt[0]["m"], entry, sw[c["e"] - 1] - TICK, p)
        gaps = [top for top in gaps if c["c"] <= top]    # closed through before any sweep: spent
        if a["l"] - c["h"] >= p["min_gap_pct"] / 100 * abs(c["c"]):
            gaps.append(a["l"])
    return None


SETUPS = {"silver_bullet": silver_bullet, "ifvg": ifvg}


def day_trades(bars: list[dict], prev: dict | None, setup) -> list[dict]:
    """The long and the short version of a setup on one day; if both trigger, the earlier one only."""
    out = []
    t = setup(bars, prev)
    if t:
        out.append({**t, "side": 1})
    mp = {"h": -prev["l"], "l": -prev["h"]} if prev else None
    t = setup(mirror(bars), mp)
    if t:
        out.append({**t, "side": -1, "entry": -t["entry"], "stop": -t["stop"], "exit": -t["exit"]})
    out.sort(key=lambda x: x["m"])
    return out[:1]


def run(days, setup, p: dict = ICT, c: dict = COSTS, aum: float = 100_000.0) -> list[dict]:
    rows, prev = [], None
    for day, bars in days:
        if not bars:
            continue
        for t in day_trades(bars, prev, setup):
            risk = abs(t["entry"] - t["stop"])
            shares = min(int(aum * p["risk_pct"] / 100 / risk), int(aum * p["max_leverage"] / t["entry"]))
            if shares <= 0:
                continue
            gross = t["side"] * (t["exit"] - t["entry"]) * shares
            cost = 2 * strategy.fee(shares, c)
            r_net = (gross - cost) / (risk * shares)
            rows.append({"date": day, "side": t["side"], "m": t["m"], "r": round(t["r"], 3),
                         "r_net": round(r_net, 3), "ret": (gross - cost) / aum})
            aum += gross - cost
        prev = {"h": max(b["h"] for b in bars), "l": min(b["l"] for b in bars)}
    return rows


def summary(rows: list[dict]) -> dict:
    n = len(rows)
    if n < 2:
        return {"trades": n}
    rs = [r["r_net"] for r in rows]
    mu = sum(rs) / n
    sd = math.sqrt(sum((x - mu) ** 2 for x in rs) / (n - 1))
    eq, peak, dd = 1.0, 1.0, 0.0
    for r in rows:
        eq *= 1 + r["ret"]
        peak = max(peak, eq)
        dd = min(dd, eq / peak - 1)
    return {"trades": n, "win_pct": round(100 * sum(x > 0 for x in rs) / n, 1),
            "avg_r_gross": round(sum(r["r"] for r in rows) / n, 3), "avg_r_net": round(mu, 3),
            "t_stat": round(mu / (sd / math.sqrt(n)), 2) if sd else 0.0,
            "total_pct": round((eq - 1) * 100, 1), "max_dd_pct": round(dd * 100, 1)}


def report(rows: list[dict], p: dict = ICT) -> dict:
    (a, b), (c, d), g = p["discovery"], p["holdout"], p["gate"]
    disc = summary([r for r in rows if a <= r["date"] <= b])
    hold = summary([r for r in rows if c <= r["date"] <= d])
    ok = (disc.get("trades", 0) >= g["min_trades"] and disc.get("avg_r_net", -1) >= g["min_avg_r"]
          and disc.get("t_stat", 0) >= g["min_t"] and hold.get("avg_r_net", -1) > g["holdout_min_avg_r"]
          and hold.get("t_stat", 0) >= g["holdout_min_t"])
    years = {}
    for r in rows:
        years.setdefault(r["date"][:4], []).append(r["r_net"])
    return {"discovery": disc, "holdout": hold,
            "by_year_avg_r": {y: [len(v), round(sum(v) / len(v), 3)] for y, v in sorted(years.items())},
            "pass": ok}


def main():
    days = data.days()
    if not days:
        print(f"no {SYMBOL} data: run  DAYTRADE_SYMBOL={SYMBOL} python3 data.py fetch 2016-01-01 <today>")
        return 1
    out = {"symbol": SYMBOL, "range": [days[0][0], days[-1][0]]}
    for name, f in SETUPS.items():
        out[name] = report(run(days, f))
    print(json.dumps(out, indent=1))
    for name in SETUPS:
        print(f"{SYMBOL} {name}: {'PASS' if out[name]['pass'] else 'FAIL'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
