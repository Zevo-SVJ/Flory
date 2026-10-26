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


class Backtest(unittest.TestCase):
    def test_run_counts_costs(self):
        rows = ict.run([("2020-01-01", day([100.0] * 390)), ("2020-01-02", sb_day())], ict.silver_bullet)
        self.assertEqual(len(rows), 1)
        self.assertLess(rows[0]["r_net"], rows[0]["r"])


if __name__ == "__main__":
    unittest.main()
