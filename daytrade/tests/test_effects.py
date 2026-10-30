# documented effects on hand-built days.
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import effects
from test_strategy import day

NOCOST = {"commission_per_share": 0.0, "min_commission": 0.0, "slippage_per_share": 0.0}


class Effects(unittest.TestCase):
    def setUp(self):
        self._cost = effects.cost
        effects.cost = lambda price, c=None: 0.0

    def tearDown(self):
        effects.cost = self._cost

    def test_last30_follows_first_half_hour(self):
        y = day([100.0] * 390)
        d = day([100.0] * 29 + [101.0] * 331 + [102.0] * 30)   # up at 10:00 -> long 15:30 -> close
        r = effects.last30(effects.summarize([("a", y), ("b", d)]))
        self.assertAlmostEqual(r[0][1], 102 / 101 - 1)

    def test_hedge30_short_after_a_down_day(self):
        y = day([100.0] * 390)
        d = day([99.0] * 360 + [98.0] * 30)
        r = effects.hedge30(effects.summarize([("a", y), ("b", d)]))
        self.assertAlmostEqual(r[0][1], -(98 / 99 - 1))

    def test_half_day_is_flat(self):
        y = day([100.0] * 390)
        d = day([101.0] * 210)
        self.assertEqual(effects.last30(effects.summarize([("a", y), ("b", d)]))[0][1], 0.0)

    def test_night_is_close_to_open(self):
        y = day([100.0] * 390)
        d = day([102.0] * 390)                                   # day() opens at the first price
        self.assertAlmostEqual(effects.night(effects.summarize([("a", y), ("b", d)]))[0][1], 0.02)

    def test_tom_holds_last_day_and_first_three(self):
        dates = ["2020-01-02", "2020-01-03", "2020-01-06", "2020-01-29",
                 "2020-01-30", "2020-01-31", "2020-02-03", "2020-02-04", "2020-02-05", "2020-02-06"]
        px = [97, 98, 99, 100, 101, 102, 103, 104, 105, 106]
        s = effects.summarize([(d, day([float(p)] * 390)) for d, p in zip(dates, px)])
        held = [round(r, 4) for _, r in effects.tom(s)][3:]     # from 01-30
        self.assertEqual(held[0], 0.0)                            # 01-30: not yet
        self.assertGreater(held[1], 0)                            # 01-31: last day of January
        self.assertTrue(all(h > 0 for h in held[2:5]))            # first three days of February
        self.assertEqual(held[5], 0.0)                            # 02-06: out


class Costs(unittest.TestCase):
    def test_round_trip_cost(self):
        self.assertAlmostEqual(effects.cost(500.0), 2 * (200 * 0.001 + 200 * 0.0035) / 100_000)


if __name__ == "__main__":
    unittest.main()
