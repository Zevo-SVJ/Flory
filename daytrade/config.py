# config.py
# every number of the day-trading desk lives here.
#
# the strategy is the one published by Zarattini, Aziz and Barbon, "Beat the Market: An Effective Intraday
# Momentum Strategy for S&P500 ETF (SPY)" (Swiss Finance Institute RP 24-97, 2024, revised Feb 2025):
# 2007 to early 2024, net of costs, +19.6% a year, Sharpe 1.33. the desk first REPRODUCES that backtest on
# its own data (backtest.py). nothing trades, not even on paper, until the reproduction holds.
from __future__ import annotations   # python 3.9 (the Mac's own python3) reads the type hints
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("DAYTRADE_DATA") or os.path.join(HERE, "data")

SYMBOL = os.environ.get("DAYTRADE_SYMBOL", "SPY")   # DAYTRADE_SYMBOL=QQQ python3 ... for the Nasdaq
TZ = "America/New_York"
SESSION_MINUTES = 390            # 09:30 -> 16:00, one bar per minute

STRATEGY = {
    "lookback_days": 14,         # the noise area: average move from the open at each minute, last 14 days
    "decide_every_min": 30,      # positions are reviewed at 10:00, 10:30 ... 15:30 only
    "first_decision_min": 30,    # minutes after 09:30
    "last_decision_min": 360,    # 15:30
    "stop_every_min": 30,        # trailing stop (VWAP / band) checked at this pace; 30 = as in the paper
    "target_daily_vol": 0.02,    # position size targets 2% daily volatility of the account...
    "max_leverage": 4.0,         # ...capped at 4x, as in the paper. the live desk starts far lower (LIVE below)
    "vol_lookback_days": 14,     # daily volatility of SPY used for that sizing
}

COSTS = {                        # the paper's own assumptions (Interactive Brokers tiered)
    "commission_per_share": 0.0035,
    "min_commission": 0.35,
    "slippage_per_share": 0.001,
}

# the reproduction must hold before anything else happens
GATE = {
    "paper_period": ("2016-01-01", "2024-02-29"),   # the part of the paper's sample our data covers
    "min_sharpe": 0.9,                              # the paper reports 1.33 on 2007-2024; we ask for 0.9+
    "both_halves_positive": True,                   # and a positive result on each half of the period
}

# paper trading later (live.py, not written yet): much smaller than the backtest
LIVE = {"max_leverage": 1.0, "daily_loss_halt_pct": 2.0}

# ict.py: the ICT setups, written as fixed rules BEFORE seeing any result. a setup counts only if it holds on
# the discovery years AND on the holdout years it never saw. no rule is changed after the first run.
ICT = {
    "discovery": ("2016-01-01", "2021-12-31"),
    "holdout": ("2022-01-01", "2099-12-31"),
    "bar_min": 5,                    # FVGs are read on 5-minute candles
    "risk_pct": 0.5,                 # each trade risks 0.5% of the account between entry and stop...
    "max_leverage": 4.0,             # ...within 4x the account
    "target_r": 2.0,                 # take profit at 2R, else stop, else out at the close
    "min_gap_pct": 0.02,             # an FVG smaller than 0.02% of price is noise
    "min_risk_pct": 0.03,            # a stop closer than 0.03% of price is not a real stop
    "sb_window": (30, 90),           # Silver Bullet: FVG formed and filled between 10:00 and 11:00
    "ifvg_window": (15, 150),        # IFVG: inversion between 09:45 and 12:00
    # batch 2, fixed on Oct 26 before any run. a setup is kept only if it PASSES on SPY and on QQQ
    "soup_window": 120,              # turtle soup: sweep of yesterday's low and close back above it, by 11:30
    "judas_min": 30,                 # judas swing (PO3/AMD): the first 30 minutes fake one way...
    "judas_fake_pct": 0.10,          # ...by at least 0.10% beyond the open, then close back across it
    "ob_window": (30, 150),          # order block: displacement FVG after a sweep, 10:00-12:00, retest of the OB
    "ob_lookback": 4,                # the OB is the last down candle within 4 candles before the displacement
    "gate": {"min_trades": 100, "min_avg_r": 0.10, "min_t": 2.0, "holdout_min_avg_r": 0.0, "holdout_min_t": 1.0},
}
