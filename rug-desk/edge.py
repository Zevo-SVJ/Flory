# edge.py
# the go-live gate. the one question that matters before real money: does the desk have an edge,
# AFTER costs, that is not luck? a few good days prove nothing; this answers with the paper trades.
#
#   - expectancy per trade with a 95% bootstrap confidence interval (2000 resamples)
#   - profit factor, win rate, worst drawdown of the realized curve
#   - verdict: real money only when there are enough trades, the whole interval is above zero,
#     and the drawdown was survivable. then a suggested size: a quarter of the Kelly fraction,
#     capped, because a full Kelly bet on an estimated edge is how accounts die.
import csv, os, random, statistics, time
from config import TRADES, TICKET_USD, PAPER_BANKROLL_USD, LOG, FACTS

MIN_TRADES = 200           # Oct 19: with ~72% swing per trade, fewer trades cannot tell +5% from 0
MAX_DRAWDOWN_SHARE = 0.30
MAX_TICKET_SHARE = 0.05     # never more than 5% of the bankroll on one memecoin, whatever Kelly says


def closed() -> list[dict]:
    """Every fully closed position, in the order they closed: {mint, usd staked, pnl, opened, closed}."""
    if not os.path.exists(TRADES):
        return []
    with open(TRADES, newline="") as f:
        rows = list(csv.DictReader(f))
    live, out = {}, []
    for r in rows:
        if r["action"] == "open":
            live[r["mint"]] = {"mint": r["mint"], "usd": float(r["usd"] or TICKET_USD), "pnl": 0.0, "opened": r["time"]}
        elif r["mint"] in live:
            live[r["mint"]]["pnl"] += float(r["pnl"])
            if r["action"] == "close":
                out.append({**live.pop(r["mint"]), "closed": r["time"]})
    return out


def per_trade() -> list[float]:
    """Realized pnl ($) of every fully closed position."""
    return [t["pnl"] for t in closed()]


def stats(xs: list[float] | None = None, seed: int = 7, stakes: list[float] | None = None) -> dict:
    """xs: pnl per trade ($). stakes: what each trade put in ($); the edge is judged on the return per
    dollar staked, since tickets vary with the setup (size.py). without stakes, the flat TICKET_USD."""
    if xs is None:
        t = closed()
        xs, stakes = [x["pnl"] for x in t], [x["usd"] for x in t]
    stakes = stakes or [TICKET_USD] * len(xs)
    n = len(xs)
    out = {"n": n, "min_trades": MIN_TRADES}
    if n == 0:
        return {**out, "verdict": "wait", "why": f"0/{MIN_TRADES} trades clôturés"}
    rets = [x / max(st, 1e-9) for x, st in zip(xs, stakes)]       # -1.0 = the whole ticket lost
    mean_r = sum(rets) / n
    rng = random.Random(seed)
    boots = sorted(sum(rng.choice(rets) for _ in range(n)) / n for _ in range(2000))
    lo_r, hi_r = boots[50], boots[1949]
    unit = TICKET_USD                     # shown in dollars on a flat reference ticket, judged in %
    mean, lo, hi = mean_r * unit, lo_r * unit, hi_r * unit
    wins, losses = [x for x in xs if x > 0], [x for x in xs if x <= 0]
    pf = sum(wins) / -sum(losses) if losses and sum(losses) < 0 else None
    equity, peak, dd = 0.0, 0.0, 0.0
    for x in xs:
        equity += x
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    var = sum((v - mean_r) ** 2 for v in rets) / max(1, n - 1)
    kelly = mean_r / var if var > 0 else 0
    out.update({"mean": round(mean, 3), "ci_low": round(lo, 3), "ci_high": round(hi, 3),
                "mean_pct": round(mean_r * 100, 2), "ci_low_pct": round(lo_r * 100, 2), "ci_high_pct": round(hi_r * 100, 2),
                "win_rate": round(len(wins) / n, 3), "profit_factor": round(pf, 2) if pf else None,
                "max_drawdown": round(dd, 2), "total": round(sum(xs), 2), "kelly": round(kelly, 3)})
    if n < MIN_TRADES:
        out.update(verdict="wait", why=f"{n}/{MIN_TRADES} trades clôturés : trop tôt pour conclure")
    elif lo <= 0:
        out.update(verdict="no", why=f"avantage non prouvé : le rendement moyen par trade peut être de {lo_r * 100:+.1f} % (IC 95 %)")
    elif dd > MAX_DRAWDOWN_SHARE * PAPER_BANKROLL_USD:
        out.update(verdict="no", why=f"drawdown de {dd:.0f} $ : plus de {MAX_DRAWDOWN_SHARE:.0%} de la banque")
    else:
        size = max(0.0, min(MAX_TICKET_SHARE, kelly / 4)) * PAPER_BANKROLL_USD
        out.update(verdict="yes", suggested_ticket=round(size, 2),
                   why=f"avantage prouvé : entre {lo_r * 100:+.1f} % et {hi_r * 100:+.1f} % par trade (IC 95 %)")
    return out


# the criteria fixed BEFORE the data came in (Oct 19), so a result can't move the goalposts
JUDGE_MIN_N = 200          # under this, no conclusion either way
JUDGE_STOP_N = 300         # at this many trades, a mean at or below zero ends the idea of living off it
JUDGE_EDGE_PCT = 3.0       # a mean this high, with the whole 95% interval above zero, is an edge


def judge(n: int, mean_pct: float | None, lo_pct: float | None) -> dict:
    """One verdict for any sample of trades (paper or backtest), on the criteria above."""
    if not n or mean_pct is None:
        return {"verdict": "wait", "why": "aucun trade"}
    if lo_pct is not None and lo_pct > 0 and mean_pct >= JUDGE_EDGE_PCT and n >= JUDGE_MIN_N:
        return {"verdict": "edge", "why": f"avantage probable : {mean_pct:+.1f} % par trade, intervalle entier au-dessus de 0"}
    if n >= JUDGE_STOP_N and mean_pct <= 0:
        return {"verdict": "stop", "why": f"{n} trades, moyenne {mean_pct:+.1f} % : abandonner l'idée d'en vivre"}
    if n < JUDGE_MIN_N:
        return {"verdict": "wait", "why": f"{n}/{JUDGE_MIN_N} trades : pas de conclusion possible"}
    return {"verdict": "flat", "why": f"{n} trades, moyenne {mean_pct:+.1f} % : aucun avantage démontré"}


BILAN_ON = "2026-10-26"    # the first week of paper trading, compared with the backtest


def bilan(card: dict | None) -> dict:
    """The Oct 26 review, computed by the desk itself: paper trades vs the backtest of the rule the desk
    runs. the rule set on Oct 19: if both are at or below zero, stop optimizing the trading."""
    st = stats()
    bt = ((card or {}).get("rules") or {}).get("early: desk now (60 min + graduation)") or {}
    paper_mean, bt_mean = st.get("mean_pct"), bt.get("mean")
    due = time.strftime("%Y-%m-%d") >= BILAN_ON
    out = {"due": due, "on": BILAN_ON, "paper_n": st["n"], "paper_mean": paper_mean,
           "paper_ci": [st.get("ci_low_pct"), st.get("ci_high_pct")],
           "bt_n": bt.get("n"), "bt_mean": bt_mean, "bt_ci": bt.get("ci95")}
    if paper_mean is None or bt_mean is None:
        out.update(verdict="wait", why="pas encore de trades clôturés ou pas de backtest")
    elif paper_mean <= 0 and bt_mean <= 0:
        out.update(verdict="stop", why="papier et backtest tous deux ≤ 0 : arrêter d'optimiser le trading, "
                                       "garder le filtre anti-rug comme produit")
    elif paper_mean > 0 and bt_mean > 0:
        out.update(verdict="go_on", why="papier et backtest tous deux > 0 : continuer à accumuler jusqu'à 200 trades")
    else:
        out.update(verdict="mixed", why="papier et backtest se contredisent : c'est du bruit, continuer à accumuler")
    if not due:
        out["why"] = f"bilan officiel le {BILAN_ON} · aujourd'hui : " + out["why"]
    return out


def living(target_month_usd: float = 2200.0) -> dict:
    """Could this pay a living? Not a promise: arithmetic on the desk's own closed trades.
    income per month = return per trade x what one trade can stake x trades a day x 30.
    what one trade can stake is capped by the market, not by the bankroll: a memecoin pool takes a
    ticket of max_ticket_share of its liquidity (FACTS) before the price impact eats the edge. so the
    ceiling is set by the pools the desk really bought, and no bankroll lifts it."""
    t = closed()
    n = len(t)
    if n < 2:
        return {"n": n, "ready": False, "why": "il faut des trades clôturés pour projeter quoi que ce soit"}
    st = stats()
    first = min(time.mktime(time.strptime(x["opened"], "%Y-%m-%d %H:%M")) for x in t)
    days = max(1.0, (time.time() - first) / 86400)
    per_day = n / days
    liq = {}
    if os.path.exists(LOG):
        with open(LOG, newline="") as f:
            for r in csv.DictReader(f):
                if r.get("liq_usd") not in (None, ""):
                    liq[r["mint"]] = float(r["liq_usd"])
    pools = [liq[x["mint"]] for x in t if x["mint"] in liq]
    cap = statistics.median(pools) * FACTS["max_ticket_share"] if pools else None
    month = lambda r: r / 100 * cap * per_day * 30 if cap else None
    proj = {k: month(st[k]) for k in ("mean_pct", "ci_low_pct", "ci_high_pct") if st.get(k) is not None}
    need_r = target_month_usd / (cap * per_day * 30) * 100 if cap else None
    return {"n": n, "ready": n >= MIN_TRADES, "trades_per_day": round(per_day, 1),
            "ticket_cap": round(cap, 0) if cap else None, "bankroll_needed": round(cap / MAX_TICKET_SHARE, 0) if cap else None,
            "month": {k: round(v, 0) for k, v in proj.items() if v is not None},
            "target": target_month_usd, "return_needed_pct": round(need_r, 1) if need_r else None,
            "why": ("projection sur trop peu de trades : l'intervalle est trop large pour dire quoi que ce soit"
                    if n < MIN_TRADES else "projection sur les trades du desk")}


if __name__ == "__main__":
    import json
    print(json.dumps(stats(), indent=2))
