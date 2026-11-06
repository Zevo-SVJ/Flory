# backtest.py
# replays the strategy on every cached day and checks it against the paper.
#   python3 backtest.py                -> prints the summary, writes data/backtest.json
#   python3 backtest.py 2016-01-01 2024-02-29
# the GATE (config.py) is the go / no-go: if our reproduction on the paper's own period is far below what
# the paper reports, the strategy (or our code) is wrong and nothing goes to paper trading.
# the period after March 2024 never fed the paper: it is the honest out-of-sample test.
from __future__ import annotations   # python 3.9 (the Mac's own python3) reads the type hints
import json, math, os, sys
from collections import deque
from config import DATA, STRATEGY, COSTS, GATE
import data
import strategy

START_AUM = 100_000.0
POST_PUB = "2024-03-01"


def run(days: list[tuple[str, list[dict]]], p: dict = STRATEGY, c: dict = COSTS, aum: float = START_AUM) -> list[dict]:
    """One row per traded day: date, net return on the morning's equity, SPY's own return, details."""
    hist, rets, rows, prev = deque(maxlen=p["lookback_days"]), deque(maxlen=p["vol_lookback_days"]), [], None
    for day, bars in days:
        if not bars:
            continue
        close = bars[-1]["c"]
        if prev is not None and len(hist) == p["lookback_days"] and len(rets) == p["vol_lookback_days"]:
            lev = strategy.leverage(strategy.daily_vol(list(rets)), p)
            r = strategy.run_day(bars, strategy.sigma(list(hist)), prev, aum, lev, p, c)
            ret = r["pnl"] / aum
            aum += r["pnl"]
            rows.append({"date": day, "ret": ret, "spy": close / prev - 1, "lev": round(lev, 3),
                         "trades": r["trades"], "fees": round(r["fees"], 2), "aum": round(aum, 2)})
        if prev is not None:
            rets.append(close / prev - 1)
        hist.append(strategy.moves(bars))
        prev = close
    return rows


def stats(rets: list[float]) -> dict:
    if len(rets) < 2:
        return {"days": len(rets)}
    eq, peak, dd = 1.0, 1.0, 0.0
    for r in rets:
        eq *= 1 + r
        peak = max(peak, eq)
        dd = min(dd, eq / peak - 1)
    mu = sum(rets) / len(rets)
    sd = math.sqrt(sum((r - mu) ** 2 for r in rets) / (len(rets) - 1))
    years = len(rets) / 252
    return {"days": len(rets), "total_pct": round((eq - 1) * 100, 1),
            "cagr_pct": round((eq ** (1 / years) - 1) * 100, 2) if eq > 0 else -100.0,
            "vol_pct": round(sd * math.sqrt(252) * 100, 2),
            "sharpe": round(mu / sd * math.sqrt(252), 2) if sd else 0.0,
            "max_dd_pct": round(dd * 100, 1),
            "hit_pct": round(100 * sum(r > 0 for r in rets) / max(1, sum(r != 0 for r in rets)), 1)}


def between(rows: list[dict], start: str | None, end: str | None) -> list[dict]:
    return [r for r in rows if (not start or r["date"] >= start) and (not end or r["date"] <= end)]


def report(rows: list[dict]) -> dict:
    a, b = GATE["paper_period"]
    paper = between(rows, a, b)
    half = len(paper) // 2
    first, second = paper[:half], paper[half:]
    s_paper = stats([r["ret"] for r in paper])
    s1, s2 = stats([r["ret"] for r in first]), stats([r["ret"] for r in second])
    ok_sharpe = s_paper.get("sharpe", 0) >= GATE["min_sharpe"]
    ok_halves = (not GATE["both_halves_positive"]) or (s1.get("total_pct", 0) > 0 and s2.get("total_pct", 0) > 0)
    years = {}
    for r in rows:
        years.setdefault(r["date"][:4], []).append(r)
    return {
        "range": [rows[0]["date"], rows[-1]["date"]] if rows else None,
        "all": stats([r["ret"] for r in rows]),
        "spy_buy_hold": stats([r["spy"] for r in rows]),
        "paper_period": {"range": [a, b], **s_paper,
                         "first_half": {"range": [first[0]["date"], first[-1]["date"]] if first else None, **s1},
                         "second_half": {"range": [second[0]["date"], second[-1]["date"]] if second else None, **s2}},
        "post_publication": {"from": POST_PUB, **stats([r["ret"] for r in between(rows, POST_PUB, None)])},
        "by_year": {y: {"ret_pct": round((math.prod(1 + r["ret"] for r in rs) - 1) * 100, 1),
                        "spy_pct": round((math.prod(1 + r["spy"] for r in rs) - 1) * 100, 1),
                        "trades": sum(r["trades"] for r in rs)} for y, rs in sorted(years.items())},
        "avg_trades_per_day": round(sum(r["trades"] for r in rows) / max(1, len(rows)), 2),
        "fees_pct_of_start": round(100 * sum(r["fees"] for r in rows) / START_AUM, 1),
        "gate": {"sharpe_ok": ok_sharpe, "halves_ok": ok_halves, "pass": bool(paper) and ok_sharpe and ok_halves,
                 "rule": f"Sharpe >= {GATE['min_sharpe']} on {a}..{b}, both halves positive"},
        "settings": {"strategy": STRATEGY, "costs": COSTS},
    }


def main(start: str | None = None, end: str | None = None):
    days = data.days(start, end)
    if not days:
        print("no data: run  python3 data.py fetch 2016-01-01 <today>  first")
        return 1
    rows = run(days)
    rep = report(rows)
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "backtest.json"), "w") as f:
        json.dump(rep, f, indent=1)
    with open(os.path.join(DATA, "backtest_days.csv"), "w") as f:
        f.write("date,ret,spy,lev,trades,fees,aum\n")
        for r in rows:
            f.write(f"{r['date']},{r['ret']:.6f},{r['spy']:.6f},{r['lev']},{r['trades']},{r['fees']},{r['aum']}\n")
    print(json.dumps({k: rep[k] for k in ("range", "all", "spy_buy_hold", "paper_period", "post_publication",
                                          "avg_trades_per_day", "fees_pct_of_start", "gate")}, indent=1))
    print("by year:", json.dumps(rep["by_year"]))
    print("GATE:", "PASS" if rep["gate"]["pass"] else "FAIL", "-", rep["gate"]["rule"])
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
