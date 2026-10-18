# tests/test_desk.py
# offline tests: every API is faked, so this runs anywhere.  python -m unittest discover tests
import os, sys, tempfile, time, unittest
from unittest import mock

os.environ["RUG_DESK_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config, book, check, watch, report  # noqa: E402

MINT = "Mint111111111111111111111111111111111111111"
PAIR = "Pair111111111111111111111111111111111111111"
VAULT_OWNER = PAIR

import base64, struct, facts  # noqa: E402


def wallets(n=10, pct=0.02):
    """Organic-looking holders: each bag 10% smaller than the one before."""
    return [{"account": f"W{i}", "percent": str(pct * (1 - 0.1 * i)), "is_locked": 0, "tag": ""}
            for i in range(n)]


def goplus(**over):
    g = {"mintable": {"status": "0"}, "freezable": {"status": "0"}, "closable": {"status": "0"},
         "balance_mutable_authority": {"status": "0"}, "transfer_fee_upgradable": {"status": "0"},
         "transfer_hook_upgradable": {"status": "0"}, "default_account_state_upgradable": {"status": "0"},
         "non_transferable": "0", "transfer_fee": {}, "transfer_hook": [], "default_account_state": "1",
         "metadata": {"symbol": "TEST"}, "holder_count": "900",
         "holders": [{"account": VAULT_OWNER, "percent": "0.6", "is_locked": 0, "tag": ""}] + wallets(9)}
    g.update(over)
    return g


def pool_account(lp_minted=1000, base_mint=MINT):
    d = bytearray(301)
    n = 0
    for c in base_mint:
        n = n * 58 + facts.B58.index(c)
    d[43:75] = n.to_bytes(32, "big")
    d[107:139] = bytes(range(1, 33))
    d[203:211] = struct.pack("<Q", lp_minted)
    return {"owner": facts.PUMPSWAP, "data": [base64.b64encode(bytes(d)).decode(), "base64"]}


class Chain:
    """Fake Solana RPC. Every holder is a funded wallet except the pool, which a program owns."""
    def __init__(self, mint_auth=None, freeze_auth=None, lp_live=0, lamports=None):
        self.mint_auth, self.freeze_auth, self.lp_live = mint_auth, freeze_auth, lp_live
        self.lamports = lamports or {}

    def __call__(self, url, timeout=None, json=None):
        m, p = json["method"], json["params"]
        if m == "getAccountInfo" and p[0] == MINT:
            res = {"value": {"data": {"parsed": {"info": {"mintAuthority": self.mint_auth,
                                                          "freezeAuthority": self.freeze_auth}}}}}
        elif m == "getAccountInfo":
            res = {"value": pool_account()}
        elif m == "getTokenSupply":
            res = {"value": {"amount": str(self.lp_live)}}
        elif m == "getMultipleAccounts":
            res = {"value": [{"owner": facts.PUMPSWAP, "lamports": 1} if a == VAULT_OWNER else
                             {"owner": facts.SYSTEM_PROGRAM, "lamports": self.lamports.get(a, 10**9 + i * 12345)}
                             for i, a in enumerate(p[0])]}
        return Resp({"jsonrpc": "2.0", "id": 1, "result": res})


def ds_pairs(price=0.001, liq=80000, age_min=120, buys=50, sells=30, dex="pumpswap"):
    return [{"baseToken": {"address": MINT, "symbol": "TEST"}, "priceUsd": str(price),
             "liquidity": {"usd": liq}, "pairCreatedAt": (time.time() - age_min * 60) * 1000,
             "txns": {"h1": {"buys": buys, "sells": sells}}, "volume": {"h1": 1000},
             "dexId": dex, "pairAddress": PAIR, "url": "https://dexscreener.com/solana/x"}]


class Resp:
    def __init__(self, data, code=200):
        self.data, self.status_code = data, code

    def json(self):
        return self.data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def fake_get(gp=None, ds=None, gp_code=200):
    def get(url, timeout=None, params=None):
        if "gopluslabs" in url:
            return Resp({"code": 1, "message": "ok", "result": {MINT: gp if gp is not None else goplus()}}, gp_code)
        return Resp(ds if ds is not None else ds_pairs())
    return get


def net(gp=None, ds=None, chain=None, gp_code=200):
    """Patch every network call the desk makes."""
    stack = mock.patch("requests.get", fake_get(gp, ds, gp_code)), mock.patch("requests.post", chain or Chain())
    class Both:
        def __enter__(self):
            for s in stack: s.__enter__()
        def __exit__(self, *a):
            for s in stack: s.__exit__(*a)
    return Both()


class Base(unittest.TestCase):
    def setUp(self):
        for f in (config.LOG, config.POSITIONS, config.TRADES):
            if os.path.exists(f):
                os.remove(f)


class Filter(Base):
    def verdict(self, **kw):
        with net(**kw):
            return check.check(MINT)

    def test_clean_token_passes(self):
        v = self.verdict()
        self.assertEqual(v["verdict"], "PASS", v)
        self.assertEqual(v["x_ca"], f"https://x.com/search?q={MINT}&f=live")

    def test_pool_vault_not_counted_as_whale(self):
        # the pool holds 60% but a program owns it: top 10 = the 9 wallets + the smallest again
        with net():
            t = facts.report(MINT, {"dex": "pumpswap", "pair": PAIR})
        self.assertEqual(t["top10_pct"], round(sum(2 * (1 - 0.1 * i) for i in range(9)) + 2 * 0.2, 2))
        self.assertEqual(t["lp_burned_pct"], 100.0)

    def test_fact_kills(self):
        cases = {
            "mint_open": {"chain": Chain(mint_auth="X")},
            "freeze_open": {"chain": Chain(freeze_auth="X")},
            "danger:balance_editable": {"gp": goplus(balance_mutable_authority={"status": "1"})},
            "danger:transfer_hook": {"gp": goplus(transfer_hook=["HookProgram"])},
            "lp_unlocked": {"chain": Chain(lp_live=500)},
            "lp_unverified": {"ds": ds_pairs(dex="raydium")},
            "no_holders": {"gp": goplus(holders=[])},
            "top10_heavy": {"gp": goplus(holders=wallets(10, 0.07))},
            "whale": {"gp": goplus(holders=wallets(1, 0.08) + wallets(5, 0.01))},
            "bundle_same_sol": {"chain": Chain(lamports={"W1": 10_000_000, "W2": 10_000_001, "W3": 10_000_000})},
            "bundle_ladder": {"gp": goplus(holders=[{"account": f"W{i}", "percent": str(0.0128 - i * 0.00005)}
                                                     for i in range(10)])},
        }
        for reason, kw in cases.items():
            with self.subTest(reason):
                v = self.verdict(**kw)
                self.assertEqual((v["stage"], v["reason"]), ("facts", reason))

    def test_goplus_also_says_mintable(self):
        v = self.verdict(gp=goplus(mintable={"status": "1"}))
        self.assertEqual(v["reason"], "mint_open")

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
        v = self.verdict(gp_code=500)
        self.assertEqual(v["verdict"], "SKIP")
        self.assertTrue(v["reason"].startswith("facts failed"))


class Book(Base):
    def test_paper_buy_and_limits(self):
        with net():
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
