# tests for the day-trading desk: synthetic sessions where the right answer is known by hand.
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import strategy
import backtest

NOCOST = {"commission_per_share": 0.0, "min_commission": 0.0, "slippage_per_share": 0.0}


def day(prices, vol=1000.0):
    """One bar per minute; open = previous close (first bar opens at prices[0])."""
    bars, prev = [], prices[0]
    for m, c in enumerate(prices):
        bars.append({"m": m, "o": prev, "h": max(prev, c), "l": min(prev, c), "c": c, "v": vol, "vw": (prev + c) / 2})
        prev = c
    return bars


def flat_sig(x, n=390):
    return [x] * n


class Noise(unittest.TestCase):
    def test_sigma_is_mean_abs_move_per_minute(self):
        h = [[0.0, 0.01, 0.02], [0.0, 0.03, 0.04]]
        self.assertEqual(strategy.sigma(h, 3), [0.0, 0.02, 0.03])

    def test_half_session_minutes_have_no_band(self):
        h = [[0.01] * 210] + [[0.01] * 390] * 3
        s = strategy.sigma(h, 390)
        self.assertIsNotNone(s[300])          # 3 of 4 days reached minute 300
        h = [[0.01] * 210] * 3 + [[0.01] * 390]
        self.assertIsNone(strategy.sigma(h, 390)[300])

    def test_moves_fill_missing_minutes(self):
        bars = [{"m": 0, "o": 100, "c": 101}, {"m": 3, "o": 101, "c": 102}]
        self.assertEqual(strategy.closes(bars), [101, 101, 101, 102])


class Sizing(unittest.TestCase):
    def test_leverage_targets_vol_and_caps(self):
        self.assertAlmostEqual(strategy.leverage(0.01), 2.0)
        self.assertEqual(strategy.leverage(0.001), 4.0)
        self.assertEqual(strategy.leverage(None), 0.0)

    def test_fee_has_minimum(self):
        self.assertAlmostEqual(strategy.fee(10), 10 * 0.001 + 0.35)
        self.assertAlmostEqual(strategy.fee(1000), 1000 * 0.001 + 3.5)
        self.assertEqual(strategy.fee(0), 0.0)


class Day(unittest.TestCase):
    def test_quiet_day_never_trades(self):
        r = strategy.run_day(day([100.0] * 390), flat_sig(0.01), 100.0, 100_000, 1.0)
        self.assertEqual(r["trades"], 0)
        self.assertEqual(r["pnl"], 0.0)

    def test_breakout_goes_long_at_next_open_and_flat_at_close(self):
        # flat until 09:59, jumps above the band at minute 29 (decision at 10:00), stays there
        px = [100.0] * 29 + [102.0] * 361
        r = strategy.run_day(day(px), flat_sig(0.01), 100.0, 100_000, 1.0, c=NOCOST)
        self.assertEqual(r["fills"][0], {"m": 30, "px": 102.0, "from": 0, "to": 1})
        self.assertEqual(r["fills"][-1]["to"], 0)
        self.assertEqual(r["fills"][-1]["m"], 390)
        self.assertEqual(r["trades"], 2)

    def test_no_decision_before_ten(self):
        px = [100.0] * 5 + [105.0] * 385        # breaks out at 09:35, first look is 10:00
        r = strategy.run_day(day(px), flat_sig(0.01), 100.0, 100_000, 1.0, c=NOCOST)
        self.assertEqual(r["fills"][0]["m"], 30)

    def test_pnl_counts_from_fill_price(self):
        # long filled at 102 (minute 30), close 104: 1000 shares * 2 = 2000
        px = [100.0] * 29 + [102.0] * 100 + [104.0] * 261
        r = strategy.run_day(day(px), flat_sig(0.01), 100.0, 100_000, 1.0, c=NOCOST)
        self.assertEqual(r["shares"], 1000)
        self.assertAlmostEqual(r["pnl"], 2000.0)

    def test_short_side(self):
        px = [100.0] * 29 + [97.0] * 361
        r = strategy.run_day(day(px), flat_sig(0.01), 100.0, 100_000, 1.0, c=NOCOST)
        self.assertEqual(r["fills"][0]["to"], -1)
        self.assertAlmostEqual(r["pnl"], 0.0)       # sold at 97, bought back at 97

    def test_vwap_stop_closes_long(self):
        # long at 10:00, then falls back inside the band: out at the 10:30 look
        px = [100.0] * 29 + [102.0] * 30 + [100.2] * 331
        r = strategy.run_day(day(px), flat_sig(0.01), 100.0, 100_000, 1.0, c=NOCOST)
        self.assertEqual([f["to"] for f in r["fills"]], [1, 0])
        self.assertEqual(r["fills"][1]["m"], 60)

    def test_flip_trades_double_size(self):
        px = [100.0] * 29 + [102.0] * 30 + [97.0] * 331
        r = strategy.run_day(day(px), flat_sig(0.01), 100.0, 100_000, 1.0)
        self.assertEqual([f["to"] for f in r["fills"]], [1, -1, 0])
        self.assertAlmostEqual(r["fees"], strategy.fee(1000) + strategy.fee(2000) + strategy.fee(1000))

    def test_gap_up_widens_lower_band_reference(self):
        # yesterday closed at 105, opens at 100: the short band is measured from 100, the long one from 105
        px = [100.0] * 29 + [104.0] * 361          # +4% from open but under 105 * 1.01
        r = strategy.run_day(day(px), flat_sig(0.01), 105.0, 100_000, 1.0, c=NOCOST)
        self.assertEqual(r["trades"], 0)

    def test_no_band_no_trade(self):
        px = [100.0] * 29 + [110.0] * 361
        r = strategy.run_day(day(px), [None] * 390, 100.0, 100_000, 1.0)
        self.assertEqual(r["trades"], 0)

    def test_decision_uses_only_closed_bar(self):
        # the spike at minute 30 comes after the 10:00 decision: no trade until 10:30
        px = [100.0] * 30 + [102.0] * 360
        r = strategy.run_day(day(px), flat_sig(0.01), 100.0, 100_000, 1.0, c=NOCOST)
        self.assertEqual(r["fills"][0]["m"], 60)


class Backtest(unittest.TestCase):
    def test_warmup_and_compounding(self):
        quiet = [(f"2020-01-{i:02d}", day([100.0 + (i % 2) * 0.5] * 390)) for i in range(1, 17)]
        trend = [("2020-01-17", day([100.5] * 29 + [104.0] * 100 + [106.0] * 261))]
        rows = backtest.run(quiet + trend)
        self.assertEqual([r["date"] for r in rows], ["2020-01-16", "2020-01-17"])   # 14 days of history first
        self.assertGreater(rows[-1]["ret"], 0)
        self.assertAlmostEqual(rows[-1]["aum"], backtest.START_AUM * (1 + rows[0]["ret"]) * (1 + rows[1]["ret"]), 2)

    def test_stats(self):
        s = backtest.stats([0.01, -0.01] * 126)
        self.assertEqual(s["days"], 252)
        self.assertLess(s["max_dd_pct"], 0)


if __name__ == "__main__":
    unittest.main()
