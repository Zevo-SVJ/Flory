# ICT setups on hand-built days where the right trade is known.
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ict
from test_strategy import day

PREV = {"h": 101.5, "l": 99.0}


def sb_day():
    # flat, sweep under yesterday's low at 10:00, fast move up leaves a bullish FVG (10:15), retrace, run to 101
    return day([100.0] * 30 + [98.8] * 10 + [99.5] * 5 + [100.2] * 5 + [100.5] * 5 + [99.4] * 5 + [101.0] * 330)


class SilverBullet(unittest.TestCase):
    def test_sweep_fvg_retrace_target(self):
        t = ict.silver_bullet(sb_day(), PREV)
        self.assertEqual(t["m"], 55)
        self.assertAlmostEqual(t["entry"], 99.5)
        self.assertAlmostEqual(t["stop"], 98.79)
        self.assertAlmostEqual(t["r"], 2.0)

    def test_no_sweep_no_trade(self):
        bars = sb_day()
        bars[10]["l"] = 98.5                            # the opening range low sits under the 10:00 dip
        self.assertIsNone(ict.silver_bullet(bars, {"h": 101.5, "l": 98.0}))

    def test_short_is_the_mirror(self):
        bars = ict.mirror(sb_day())
        for b in bars:                                  # back to positive prices, falling instead of rising
            for k in ("o", "h", "l", "c"):
                b[k] += 200.0
        t = ict.day_trades(bars, {"h": 200 - PREV["l"], "l": 200 - PREV["h"]}, ict.silver_bullet)
        self.assertEqual(t[0]["side"], -1)
        self.assertAlmostEqual(t[0]["entry"], 100.5)
        self.assertAlmostEqual(t[0]["r"], 2.0)

    def test_stop_first_when_both_touched(self):
        bars = sb_day()
        for b in bars:
            if b["m"] == 60:
                b["l"] = 98.0                           # the target bar also trades under the stop
        self.assertAlmostEqual(ict.silver_bullet(bars, PREV)["r"], -1.0)


class Fills(unittest.TestCase):
    def test_no_target_in_the_limit_fill_minute(self):
        bars = sb_day()
        for b in bars:
            if b["m"] == 55:
                b["h"] = 101.5                          # the high may have printed before the dip that filled
        t = ict.silver_bullet(bars, PREV)
        self.assertEqual(t["exit_m"], 60)

    def test_gap_through_stop_exits_at_open(self):
        bars = day([100.0] * 10 + [99.0] * 380)
        bars[20]["o"], bars[20]["l"] = 97.0, 97.0
        px, m = ict.manage(bars, 15, 99.0, 98.0, 101.0)
        self.assertEqual((px, m), (97.0, 20))


class InverseFVG(unittest.TestCase):
    def test_bearish_gap_swept_then_closed_through(self):
        bars = day([100.0] * 15 + [98.9] * 10 + [100.3] * 365)
        t = ict.ifvg(bars, PREV)
        self.assertEqual(t["m"], 30)
        self.assertAlmostEqual(t["entry"], 100.3)
        self.assertAlmostEqual(t["stop"], 98.89)
        self.assertAlmostEqual(t["r"], 0.0)

    def test_without_sweep_nothing(self):
        bars = day([100.0] * 15 + [98.9] * 10 + [100.3] * 365)
        self.assertIsNone(ict.ifvg(bars, {"h": 101.5, "l": 98.0}))


class Batch2(unittest.TestCase):
    def test_turtle_soup(self):
        bars = day([100.0] * 10 + [98.5] * 5 + [99.5] * 375)      # under 99 at 09:40, back above in the 09:45 candle
        t = ict.turtle_soup(bars, PREV)
        self.assertEqual(t["m"], 20)
        self.assertAlmostEqual(t["stop"], 98.49)

    def test_judas(self):
        bars = day([100.0] * 5 + [99.7] * 10 + [100.2] * 375)     # fake drop 0.3%, back above the open by 10:00
        t = ict.judas(bars, PREV)
        self.assertEqual(t["m"], 30)
        self.assertAlmostEqual(t["entry"], 100.2)
        self.assertAlmostEqual(t["stop"], 99.69)
        self.assertIsNone(ict.judas(day([100.0] * 5 + [99.95] * 10 + [100.2] * 375), PREV))   # 0.05%: no fake

    def test_order_block(self):
        # down candle 09:55-10:00 (the OB, top 99.8), sweep, displacement leaves an FVG, retest of 99.8
        px = [100.0] * 25 + [99.8] * 4 + [98.8] * 1 + [98.8] * 5 + [99.6] * 5 + [100.4] * 5 + [99.7] * 5 + [102.0] * 340
        t = ict.order_block(day(px), PREV)
        self.assertIsNotNone(t)
        self.assertLess(t["entry"], 100.4)
        self.assertLess(t["stop"], 98.8)


class Backtest(unittest.TestCase):
    def test_run_counts_costs(self):
        rows = ict.run([("2020-01-01", day([100.0] * 390)), ("2020-01-02", sb_day())], ict.silver_bullet)
        self.assertEqual(len(rows), 1)
        self.assertLess(rows[0]["r_net"], rows[0]["r"])


if __name__ == "__main__":
    unittest.main()
