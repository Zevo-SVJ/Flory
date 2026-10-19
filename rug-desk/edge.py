# edge.py
# the go-live gate. the one question that matters before real money: does the desk have an edge,
# AFTER costs, that is not luck? a few good days prove nothing; this answers with the paper trades.
#
#   - expectancy per trade with a 95% bootstrap confidence interval (2000 resamples)
#   - profit factor, win rate, worst drawdown of the realized curve
#   - verdict: real money only when there are enough trades, the whole interval is above zero,
#     and the drawdown was survivable. then a suggested size: a quarter of the Kelly fraction,
#     capped, because a full Kelly bet on an estimated edge is how accounts die.
import csv, os, random
from config import TRADES, TICKET_USD, PAPER_BANKROLL_USD

MIN_TRADES = 50
MAX_DRAWDOWN_SHARE = 0.30
MAX_TICKET_SHARE = 0.05     # never more than 5% of the bankroll on one memecoin, whatever Kelly says


def per_trade() -> list[float]:
    """Realized pnl of every fully closed position, in the order they closed."""
    if not os.path.exists(TRADES):
        return []
    with open(TRADES, newline="") as f:
        rows = list(csv.DictReader(f))
    pnl, out = {}, []
    for r in rows:
        if r["action"] == "open":
            pnl[r["mint"]] = 0.0
        elif r["mint"] in pnl:
            pnl[r["mint"]] += float(r["pnl"])
            if r["action"] == "close":
                out.append(pnl.pop(r["mint"]))
    return out


def stats(xs: list[float] | None = None, seed: int = 7) -> dict:
    xs = per_trade() if xs is None else xs
    n = len(xs)
    out = {"n": n, "min_trades": MIN_TRADES}
    if n == 0:
        return {**out, "verdict": "wait", "why": f"0/{MIN_TRADES} trades clôturés"}
    mean = sum(xs) / n
    rng = random.Random(seed)
    boots = sorted(sum(rng.choice(xs) for _ in range(n)) / n for _ in range(2000))
    lo, hi = boots[50], boots[1949]
    wins, losses = [x for x in xs if x > 0], [x for x in xs if x <= 0]
    pf = sum(wins) / -sum(losses) if losses and sum(losses) < 0 else None
    equity, peak, dd = 0.0, 0.0, 0.0
    for x in xs:
        equity += x
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    r = [x / TICKET_USD for x in xs]                        # return per dollar staked
    var = sum((v - mean / TICKET_USD) ** 2 for v in r) / max(1, n - 1)
    kelly = (mean / TICKET_USD) / var if var > 0 else 0
    out.update({"mean": round(mean, 3), "ci_low": round(lo, 3), "ci_high": round(hi, 3),
                "win_rate": round(len(wins) / n, 3), "profit_factor": round(pf, 2) if pf else None,
                "max_drawdown": round(dd, 2), "total": round(sum(xs), 2), "kelly": round(kelly, 3)})
    if n < MIN_TRADES:
        out.update(verdict="wait", why=f"{n}/{MIN_TRADES} trades clôturés : trop tôt pour conclure")
    elif lo <= 0:
        out.update(verdict="no", why=f"avantage non prouvé : la moyenne par trade peut être de {lo:+.2f} $ (IC 95 %)")
    elif dd > MAX_DRAWDOWN_SHARE * PAPER_BANKROLL_USD:
        out.update(verdict="no", why=f"drawdown de {dd:.0f} $ : plus de {MAX_DRAWDOWN_SHARE:.0%} de la banque")
    else:
        size = max(0.0, min(MAX_TICKET_SHARE, kelly / 4)) * PAPER_BANKROLL_USD
        out.update(verdict="yes", suggested_ticket=round(size, 2),
                   why=f"avantage prouvé : entre {lo:+.2f} $ et {hi:+.2f} $ par trade de {TICKET_USD} $ (IC 95 %)")
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(stats(), indent=2))
