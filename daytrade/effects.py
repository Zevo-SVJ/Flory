# effects.py
# batch 3: market effects documented by independent research, replayed with fixed rules, 1x the account.
#   python3 effects.py                      (SPY)
#   DAYTRADE_SYMBOL=QQQ python3 effects.py
#
# LAST30   Gao, Han, Li, Zhou (JFE 2018): the first half hour (yesterday's close -> 10:00) predicts the last
#          half hour. at 15:30 go with its sign, out at the close.
# HEDGE30  Baltussen, Da, Lammers, Martens (JFE 2021): option and leveraged-ETF hedgers trade with the day's
#          move into the close. at 15:30 go with the sign of yesterday's close -> 15:30, out at the close.
# NIGHT    Lou, Polk, Skouras (JFE 2019) and others: index returns come mostly overnight. hold close -> open.
# TOM      Lakonishok and Smidt (1988), Etula et al. (RFS 2020): returns cluster at the turn of the month.
#          hold from the close of the 2nd-to-last trading day to the close of the 3rd trading day.
# the gate is the one used for ICT: discovery 2016-2021 t >= 2, holdout 2022+ positive with t >= 1,
# on SPY AND on QQQ. returns are net of the same costs as everywhere else.
import json, math, sys
from config import ICT, COSTS, SYMBOL
import data
import strategy

AUM = 100_000.0


def cost(price: float, c: dict = COSTS) -> float:
    """One round trip of the whole account, as a fraction of it."""
    return 2 * strategy.fee(int(AUM / price), c) / AUM


def summarize(days) -> list[dict]:
    """Per day: open, 10:00 price, 15:30 price, close (None when the session has no such minute)."""
    out = []
    for day, bars in days:
        if not bars:
            continue
        at = {b["m"]: b["c"] for b in bars}
        out.append({"date": day, "o": bars[0]["o"], "p10": at.get(29), "p1530": at.get(359),
                    "c": bars[-1]["c"], "full": bars[-1]["m"] >= 389})
    return out


def last30(s: list[dict]) -> list[tuple[str, float]]:
    out = []
    for y, d in zip(s, s[1:]):
        if d["full"] and d["p10"] and d["p1530"]:
            side = 1 if d["p10"] > y["c"] else -1 if d["p10"] < y["c"] else 0
            if side:
                out.append((d["date"], side * (d["c"] / d["p1530"] - 1) - cost(d["p1530"])))
                continue
        out.append((d["date"], 0.0))
    return out


def hedge30(s: list[dict]) -> list[tuple[str, float]]:
    out = []
    for y, d in zip(s, s[1:]):
        if d["full"] and d["p1530"]:
            side = 1 if d["p1530"] > y["c"] else -1 if d["p1530"] < y["c"] else 0
            if side:
                out.append((d["date"], side * (d["c"] / d["p1530"] - 1) - cost(d["p1530"])))
                continue
        out.append((d["date"], 0.0))
    return out


def night(s: list[dict]) -> list[tuple[str, float]]:
    return [(d["date"], d["o"] / y["c"] - 1 - cost(y["c"])) for y, d in zip(s, s[1:])]


def tom(s: list[dict]) -> list[tuple[str, float]]:
    """In the market on the last trading day of a month and the first three of the next (returns close to
    close), entering at the close of the 2nd-to-last day; one round trip per month."""
    months = {}
    for i, d in enumerate(s):
        months.setdefault(d["date"][:7], []).append(i)
    held = set()
    for ix in months.values():
        held.update(ix[-1:])
        held.update(ix[:3])
    out = []
    for i in range(1, len(s)):
        r = 0.0
        if i in held:
            r = s[i]["c"] / s[i - 1]["c"] - 1
            if i - 1 not in held:
                r -= cost(s[i - 1]["c"])                 # entry, and the exit three days later
        out.append((s[i]["date"], r))
    return out


EFFECTS = {"last30": last30, "hedge30": hedge30, "night": night, "tom": tom}


def stats(rets: list[float]) -> dict:
    n = len(rets)
    if n < 2:
        return {"days": n}
    mu = sum(rets) / n
    sd = math.sqrt(sum((r - mu) ** 2 for r in rets) / (n - 1))
    eq, peak, dd = 1.0, 1.0, 0.0
    for r in rets:
        eq *= 1 + r
        peak = max(peak, eq)
        dd = min(dd, eq / peak - 1)
    return {"days": n, "active": sum(r != 0 for r in rets), "cagr_pct": round((eq ** (252 / n) - 1) * 100, 2),
            "sharpe": round(mu / sd * math.sqrt(252), 2) if sd else 0.0,
            "t_stat": round(mu / (sd / math.sqrt(n)), 2) if sd else 0.0, "max_dd_pct": round(dd * 100, 1)}


def verdict(rows: list[tuple[str, float]], p: dict = ICT) -> dict:
    (a, b), (c, d), g = p["discovery"], p["holdout"], p["gate"]
    disc = stats([r for day, r in rows if a <= day <= b])
    hold = stats([r for day, r in rows if c <= day <= d])
    ok = disc.get("t_stat", 0) >= g["min_t"] and hold.get("t_stat", 0) >= g["holdout_min_t"]
    return {"discovery": disc, "holdout": hold, "pass": ok}


def main():
    days = data.days()
    if not days:
        print(f"no {SYMBOL} data")
        return 1
    s = summarize(days)
    out = {name: verdict(f(s)) for name, f in EFFECTS.items()}
    if "--short" not in sys.argv:
        print(json.dumps(out, indent=1))
    for name, v in out.items():
        d, h = v["discovery"], v["holdout"]
        print(f"{SYMBOL} {name}: 2016-21 {d.get('cagr_pct')}%/y sharpe={d.get('sharpe')} t={d.get('t_stat')} | "
              f"2022+ {h.get('cagr_pct')}%/y sharpe={h.get('sharpe')} t={h.get('t_stat')} | "
              f"{'PASS' if v['pass'] else 'FAIL'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
