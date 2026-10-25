# config.py
# every number of the day-trading desk lives here.
#
# the strategy is the one published by Zarattini, Aziz and Barbon, "Beat the Market: An Effective Intraday
# Momentum Strategy for S&P500 ETF (SPY)" (Swiss Finance Institute RP 24-97, 2024, revised Feb 2025):
# 2007 to early 2024, net of costs, +19.6% a year, Sharpe 1.33. the desk first REPRODUCES that backtest on
# its own data (backtest.py). nothing trades, not even on paper, until the reproduction holds.
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("DAYTRADE_DATA") or os.path.join(HERE, "data")

SYMBOL = "SPY"
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
