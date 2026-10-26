# daytrade

SPY intraday momentum (Zarattini, Aziz, Barbon 2024, "Beat the Market"). Step 1: reproduce the paper's backtest
on our own Alpaca data. Nothing trades, not even on paper, until `backtest.py` prints `GATE: PASS`.

    cd daytrade
    # .env (chmod 600): ALPACA_KEY_ID=...  ALPACA_SECRET_KEY=...   (paper keys)
    python3 data.py fetch 2016-01-01 2026-10-24     # ~10 years of minute bars, cached by month in data/bars/
    python3 backtest.py                             # summary + data/backtest.json + data/backtest_days.csv
    python3 -m unittest discover -s tests

- `config.py`: every number (strategy, costs, gate).
- `strategy.py`: noise area, signal, one day of trading. Decisions fill at the next bar's open.
- `backtest.py`: replay, stats, gate, post-publication period (2024-03 onward = out of sample).

## ICT setups (ict.py)

Silver Bullet and IFVG reversal, coded as fixed rules (config.ICT) before any run: discovery 2016-2021, holdout
2022 onward, gate written in advance. SPY stands for ES, QQQ for NQ:

    python3 ict.py
    DAYTRADE_SYMBOL=QQQ python3 data.py fetch 2016-01-01 2026-10-24
    DAYTRADE_SYMBOL=QQQ python3 ict.py
