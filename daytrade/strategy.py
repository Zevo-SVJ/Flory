# strategy.py
# the intraday momentum strategy of Zarattini, Aziz and Barbon (2024), one day at a time.
#
# the "noise area": on a normal day SPY wanders around its open by about as much as it did, at the same
# minute, over the last 14 days. a move beyond that band means real demand or supply, and it tends to last
# into the close (Gao et al., JFE 2018). so:
#   UB(m) = max(open, prev_close) * (1 + sigma(m))     LB(m) = min(open, prev_close) * (1 - sigma(m))
#   sigma(m) = mean over the previous 14 days of |close at minute m / open of that day - 1|
# every 30 minutes from 10:00 to 15:30: long if close > max(UB, VWAP), short if close < min(LB, VWAP),
# otherwise flat. VWAP and the band act as the trailing stop. everything is flat at the close.
#
# no look-ahead: a decision uses the bar that just closed and only past days; it is executed at the NEXT
# bar's open, paying slippage and commission.
import math
from config import STRATEGY, COSTS


def closes(bars: list[dict]) -> list[float]:
    """One close per minute from 09:30 to the day's last bar; a missing minute repeats the last close."""
    if not bars:
        return []
    out, last, i = [], bars[0]["o"], 0
    for m in range(bars[-1]["m"] + 1):
        while i < len(bars) and bars[i]["m"] <= m:
            last = bars[i]["c"]
            i += 1
        out.append(last)
    return out


def moves(bars: list[dict]) -> list[float]:
    """|close / open - 1| at each minute of the day: what the noise area is made of."""
    o = bars[0]["o"]
    return [abs(c / o - 1) for c in closes(bars)]


def sigma(history: list[list[float]], n: int = 390) -> list[float | None]:
    """The noise band at each minute, from the moves of the previous days (oldest first). a minute that
    fewer than half the days reached (half sessions) has no band and never trades."""
    need = max(1, len(history) // 2)
    out = []
    for m in range(n):
        vals = [h[m] for h in history if m < len(h)]
        out.append(sum(vals) / len(vals) if len(vals) >= need else None)
    return out


def daily_vol(rets: list[float]) -> float | None:
    """Standard deviation of the last daily close-to-close returns (sample)."""
    if len(rets) < 2:
        return None
    mu = sum(rets) / len(rets)
    return math.sqrt(sum((r - mu) ** 2 for r in rets) / (len(rets) - 1))


def leverage(vol: float | None, p: dict = STRATEGY) -> float:
    if not vol:
        return 0.0
    return min(p["max_leverage"], p["target_daily_vol"] / vol)


def fee(shares: int, c: dict = COSTS) -> float:
    """Cost of trading this many shares once: slippage on each share plus the commission."""
    if shares <= 0:
        return 0.0
    return shares * c["slippage_per_share"] + max(c["min_commission"], shares * c["commission_per_share"])


def is_decision(end_min: int, p: dict = STRATEGY) -> bool:
    return (end_min % p["decide_every_min"] == 0
            and p["first_decision_min"] <= end_min <= p["last_decision_min"])


def signal(close: float, vwap: float, ub: float, lb: float) -> int:
    if close > max(ub, vwap):
        return 1
    if close < min(lb, vwap):
        return -1
    return 0


def run_day(bars: list[dict], sig: list[float | None], prev_close: float, aum: float, lev: float,
            p: dict = STRATEGY, c: dict = COSTS) -> dict:
    """Trade one session. bars: [{m, o, h, l, c, v, vw}] sorted by minute. returns the day's net P&L in
    dollars and what happened."""
    out = {"pnl": 0.0, "fees": 0.0, "trades": 0, "shares": 0, "long_min": 0, "short_min": 0, "fills": []}
    if not bars or lev <= 0 or not prev_close:
        return out
    o = bars[0]["o"]
    shares = int(aum * lev / o)
    out["shares"] = shares
    if shares <= 0:
        return out
    up, down = max(o, prev_close), min(o, prev_close)
    pos, entry, pv, vol, go = 0, 0.0, 0.0, 0.0, None
    last = len(bars) - 1

    def trade(new: int, px: float, m: int):
        nonlocal pos, entry
        if new == pos:
            return
        out["pnl"] += pos * shares * (px - entry)
        f = fee(abs(new - pos) * shares, c)      # a flip trades twice the size
        out["pnl"] -= f
        out["fees"] += f
        out["trades"] += 1
        out["fills"].append({"m": m, "px": px, "from": pos, "to": new})
        pos, entry = new, px

    for i, b in enumerate(bars):
        if go is not None:                              # the previous bar's decision, filled at this open
            trade(go, b["o"], b["m"])
            go = None
        if pos > 0:
            out["long_min"] += 1
        elif pos < 0:
            out["short_min"] += 1
        pv += b["vw"] * b["v"]
        vol += b["v"]
        vwap = pv / vol if vol else b["c"]
        end_min = b["m"] + 1
        if i < last and is_decision(end_min, p):
            s = sig[b["m"]] if b["m"] < len(sig) else None
            want = 0 if s is None else signal(b["c"], vwap, up * (1 + s), down * (1 - s))
            if want != pos:
                go = want
    trade(0, bars[last]["c"], bars[last]["m"] + 1)        # flat at the close
    return out
