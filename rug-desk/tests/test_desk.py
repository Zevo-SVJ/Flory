# tests/test_desk.py
# offline tests: every API is faked, so this runs anywhere.  python -m unittest discover tests
import os, sys, tempfile, time, unittest
from unittest import mock

os.environ["RUG_DESK_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config, book, check, watch, report  # noqa: E402

MINT = "Mint111111111111111111111111111111111111111"
CREATOR = "Dev1111111111111111111111111111111111111111"
VAULT = "Vault11111111111111111111111111111111111111"


def rc_report(**over):
    d = {
        "token": {"mintAuthority": None, "freezeAuthority": None, "supply": 1_000_000_000},
        "tokenMeta": {"symbol": "TEST"},
        "rugged": False, "score_normalised": 10, "risks": [{"name": "Low holders", "level": "warn"}],
        "markets": [{"lp": {"lpLockedPct": 100, "baseUSD": 40000, "quoteUSD": 40000}}],
        "topHolders": [{"address": VAULT, "owner": VAULT, "pct": 60, "insider": False}]
                      + [{"address": f"W{i}", "owner": f"O{i}", "pct": 2, "insider": False} for i in range(12)],
        "knownAccounts": {VAULT: {"name": "Raydium", "type": "AMM"}},
        "creator": CREATOR, "creatorBalance": 0, "graphInsidersDetected": 0, "totalHolders": 900,
    }
    d.update(over)
    return d


def ds_pairs(price=0.001, liq=80000, age_min=120, buys=50, sells=30):
    return [{"baseToken": {"address": MINT, "symbol": "TEST"}, "priceUsd": str(price),
             "liquidity": {"usd": liq}, "pairCreatedAt": (time.time() - age_min * 60) * 1000,
             "txns": {"h1": {"buys": buys, "sells": sells}}, "volume": {"h1": 1000},
             "url": "https://dexscreener.com/solana/x"}]


class Resp:
    def __init__(self, data, code=200):
        self.data, self.status_code = data, code

    def json(self):
        return self.data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def fake_get(rc=None, ds=None, rc_code=200):
    def get(url, timeout=None):
        if "rugcheck" in url:
            return Resp(rc if rc is not None else rc_report(), rc_code)
        return Resp(ds if ds is not None else ds_pairs())
    return get


class Base(unittest.TestCase):
    def setUp(self):
        for f in (config.LOG, config.POSITIONS, config.TRADES):
            if os.path.exists(f):
                os.remove(f)


class Filter(Base):
    def verdict(self, **kw):
        with mock.patch("requests.get", fake_get(**kw)):
            return check.check(MINT)

    def test_clean_token_passes_13_checks(self):
        v = self.verdict()
        self.assertEqual(v["verdict"], "PASS", v)
        self.assertEqual(v["x_ca"], f"https://x.com/search?q={MINT}&f=live")

    def test_pool_vault_not_counted_as_whale(self):
        # vault holds 60% but is an AMM: top10 = 10 x 2% = 20% < 30%
        self.assertEqual(self.verdict()["verdict"], "PASS")

    def test_fact_kills(self):
        cases = {
            "already_rugged": {"rugged": True},
            "mint_open": {"token": {"mintAuthority": "X", "freezeAuthority": None, "supply": 1}},
            "freeze_open": {"token": {"mintAuthority": None, "freezeAuthority": "X", "supply": 1}},
            "danger:Bad": {"risks": [{"name": "Bad", "level": "danger"}]},
            "risk_score": {"score_normalised": 41},
            "lp_unlocked": {"markets": [{"lp": {"lpLockedPct": 50, "baseUSD": 1, "quoteUSD": 1}}]},
            "top10_heavy": {"topHolders": [{"address": f"W{i}", "pct": 5} for i in range(10)]},
            "dev_holds": {"creatorBalance": 60_000_000},
            "insiders": {"graphInsidersDetected": 3},
            "no_report": {"score_normalised": None},
        }
        for reason, over in cases.items():
            with self.subTest(reason):
                v = self.verdict(rc=rc_report(**over))
                self.assertEqual((v["stage"], v["reason"]), ("facts", reason))

    def test_missing_creator_balance_kills(self):
        d = rc_report(); del d["creatorBalance"]
        self.assertEqual(self.verdict(rc=d)["reason"], "dev_holds")

    def test_pool_kills(self):
        cases = {
            "no_pool": [],
            "thin_pool": ds_pairs(liq=10000),
            "too_fresh": ds_pairs(age_min=10),
            "too_old": ds_pairs(age_min=80 * 60),
            "nobody_can_sell": ds_pairs(buys=40, sells=0),
        }
        for reason, ds in cases.items():
            with self.subTest(reason):
                v = self.verdict(ds=ds)
                self.assertEqual((v["stage"], v["reason"]), ("pool", reason))

    def test_source_down_is_skip(self):
        v = self.verdict(rc_code=500)
        self.assertEqual(v["verdict"], "SKIP")
        self.assertTrue(v["reason"].startswith("rugcheck failed"))


class Book(Base):
    def test_paper_buy_and_limits(self):
        with mock.patch("requests.get", fake_get()):
            v = check.run(MINT)
        self.assertIn("PAPER BUY", v["action"])
        self.assertIn(MINT, book.load())
        self.assertEqual(book.guard(MINT), "already_open")

    def test_daily_loss_halt(self):
        book.record("A", "A", "close", 0, -config.DAILY_LOSS_HALT_USD, "stop")
        self.assertEqual(book.guard(MINT), "halted_daily_loss")

    def test_cooldown(self):
        book.record(MINT, "T", "close", 10, 1, "stop")
        self.assertEqual(book.guard(MINT), "cooldown")

    def test_max_open(self):
        for i in range(config.MAX_OPEN):
            book.open_position(f"M{i}", "M", 1.0, 100000)
        self.assertEqual(book.guard(MINT), "max_open")


class Exits(Base):
    def tick(self, price, liq=80000):
        with mock.patch("requests.get", fake_get(ds=ds_pairs(price=price, liq=liq))):
            return watch.watch()

    def setUp(self):
        super().setUp()
        book.open_position(MINT, "TEST", 1.0, 80000)

    def test_silent_when_nothing_changes(self):
        self.assertEqual(self.tick(1.05), [])

    def test_stop(self):
        e = self.tick(0.6)
        self.assertIn("stop", e[0]); self.assertNotIn(MINT, book.load())

    def test_liquidity_pulled_beats_green(self):
        e = self.tick(1.5, liq=30000)
        self.assertIn("liquidity_pulled", e[0])

    def test_ladder_then_trail(self):
        self.assertIn("take_profit_100", self.tick(2.0)[0])
        self.assertAlmostEqual(book.load()[MINT]["qty"], 12.5)
        self.assertIn("take_profit_200", self.tick(3.0)[0])
        self.assertAlmostEqual(book.load()[MINT]["qty"], 6.25)
        self.assertEqual(self.tick(4.0), [])                 # new peak
        self.assertIn("trailing_stop", self.tick(2.7)[0])    # 32.5% off peak
        self.assertNotIn(MINT, book.load())
        pnl = sum(float(t["pnl"]) for t in book.trades())
        self.assertAlmostEqual(pnl, 12.5 * 1 + 6.25 * 2 + 6.25 * 1.7, places=1)

    def test_time_stop(self):
        b = book.load(); b[MINT]["opened"] -= 7 * 3600; book.save(b)
        self.assertIn("time_stop", self.tick(1.1)[0])

    def test_pool_gone(self):
        with mock.patch("requests.get", fake_get(ds=[])):
            e = watch.watch()
        self.assertIn("pool gone", e[0])
        self.assertAlmostEqual(book.today_pnl(), -25)

    def test_report_runs(self):
        self.tick(0.6)
        out = report.report()
        self.assertIn("realized pnl today: $-10.00", out)


if __name__ == "__main__":
    unittest.main()


class Scan(Base):
    def test_retryable_kills_come_back_after_30_min(self):
        import scan
        old = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - 3600))
        check.log({"time": old, "mint": "FRESH", "stage": "pool", "verdict": "SKIP", "reason": "too_fresh"})
        check.log({"time": old, "mint": "RUG", "stage": "facts", "verdict": "SKIP", "reason": "mint_open"})
        check.log({"time": time.strftime("%Y-%m-%d %H:%M"), "mint": "NEW", "stage": "pool",
                   "verdict": "SKIP", "reason": "too_fresh"})
        self.assertEqual(scan._done(), {"RUG", "NEW"})
