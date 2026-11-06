# diag.py
# why the backtest earns what it earns: the same replay, cost-free, long-only and short-only, per period.
# it changes NO rule. tuning rules on the post-publication years would spend the only honest test we have.
#   python3 diag.py
import json
import backtest, data, strategy
from config import COSTS, GATE

NOCOST = {k: 0.0 for k in COSTS}
_signal = strategy.signal


def only(side):
    def f(*a):
        s = _signal(*a)
        return s if s == side else 0
    return f


def periods(rows):
    a, b = GATE["paper_period"]
    out = {}
    for name, (s, e) in {"paper": (a, b), "post_pub": (backtest.POST_PUB, None)}.items():
        st = backtest.stats([r["ret"] for r in backtest.between(rows, s, e)])
        out[name] = {k: st.get(k) for k in ("cagr_pct", "sharpe", "max_dd_pct")}
    return out


def main():
    days = data.days()
    res = {}
    for name, sig, costs in [("net", _signal, COSTS), ("gross", _signal, NOCOST),
                             ("long_only_net", only(1), COSTS), ("short_only_net", only(-1), COSTS)]:
        strategy.signal = sig
        res[name] = periods(backtest.run(days, c=costs))
    strategy.signal = _signal
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
