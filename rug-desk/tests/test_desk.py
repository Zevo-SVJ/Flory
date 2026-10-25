# tests/test_desk.py
# offline tests: every API is faked, so this runs anywhere.  python -m unittest discover tests
import csv, json, os, sys, tempfile, threading, time, unittest
from unittest import mock

os.environ["RUG_DESK_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config, book, check, watch, report  # noqa: E402
book.COSTS = False      # the exact-number tests below check the rules; Costs tests the fees on their own

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
    d[211:243] = bytes(range(40, 72))          # coin_creator, the dev wallet
    return {"owner": facts.PUMPSWAP, "data": [base64.b64encode(bytes(d)).decode(), "base64"]}


class Chain:
    """Fake Solana RPC. Every holder is a funded wallet except the pool, which a program owns."""
    def __init__(self, mint_auth=None, freeze_auth=None, lp_live=0, lamports=None, dev_amount=0, largest=None):
        self.mint_auth, self.freeze_auth, self.lp_live = mint_auth, freeze_auth, lp_live
        self.largest = largest or []          # [(owner, amount)] the chain's biggest token accounts
        self.dev_amount = dev_amount
        self.lamports = lamports or {}

    def __call__(self, url, timeout=None, json=None):
        m, p = json["method"], json["params"]
        if m == "getAccountInfo" and p[0] == MINT:
            res = {"value": {"data": {"parsed": {"info": {"mintAuthority": self.mint_auth,
                                                          "freezeAuthority": self.freeze_auth}}}}}
        elif m == "getAccountInfo":
            res = {"value": pool_account()}
        elif m == "getTokenSupply":
            res = {"value": {"amount": "1000000" if p[0] == MINT else str(self.lp_live)}}
        elif m == "getTokenAccountsByOwner":
            res = {"value": [{"account": {"data": {"parsed": {"info": {"tokenAmount": {"amount": str(self.dev_amount)}}}}}}]}
        elif m == "getTokenLargestAccounts":
            res = {"value": [{"address": f"TA{i}", "amount": str(a)} for i, (_, a) in enumerate(self.largest)]}
        elif m == "getMultipleAccounts" and p[1].get("encoding") == "jsonParsed":
            res = {"value": [{"data": {"parsed": {"info": {"owner": self.largest[int(a[2:])][0]}}}} for a in p[0]]}
        elif m == "getMultipleAccounts":
            res = {"value": [{"owner": facts.PUMPSWAP, "lamports": 1} if a == VAULT_OWNER else
                             {"owner": facts.SYSTEM_PROGRAM, "lamports": self.lamports.get(a, 10**9 + i * 12345)}
                             for i, a in enumerate(p[0])]}
        return Resp({"jsonrpc": "2.0", "id": 1, "result": res})


def ds_pairs(price=0.001, liq=80000, age_min=120, buys=50, sells=30, dex="pumpswap", vol=20000, mcap=None):
    return [{"baseToken": {"address": MINT, "symbol": "TEST"}, "priceUsd": str(price),
             "liquidity": {"usd": liq}, "pairCreatedAt": (time.time() - age_min * 60) * 1000,
             "txns": {"h1": {"buys": buys, "sells": sells}}, "volume": {"h1": vol},
             "marketCap": mcap if mcap is not None else liq * 4,
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
    def get(url, timeout=None, params=None, headers=None):
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
        import market
        market._tickers.clear()                 # the ticker search cache would leak between tests
        for f in (config.LOG, config.POSITIONS, config.TRADES):
            if os.path.exists(f):
                os.remove(f)

    def verdict(self, **kw):
        with net(**kw):
            return check.check(MINT)


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
            "dev_holds": {"chain": Chain(dev_amount=60000)},
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

    def test_holders_from_chain_when_goplus_has_none(self):
        largest = [(VAULT_OWNER, 600000)] + [(f"W{i}", 20000 - i * 1500) for i in range(9)]
        with net(gp=goplus(holders=[], holder_count=None), chain=Chain(largest=largest)):
            t = facts.report(MINT, {"pair": PAIR, "dex": "pumpswap"})
        self.assertEqual(t["holders_source"], "chain")
        self.assertEqual(t["max_wallet_pct"], 2.0)          # the pool vault is not counted as a whale
        self.assertIsNone(facts.fact_kill(t))

    def test_graduates_from_the_migration_account(self):
        import grads
        if os.path.exists(grads.STATE):
            os.remove(grads.STATE)
        now = time.time()
        txs = {"S1": ["Program log: Instruction: MigrateV2"], "S2": ["Program log: Instruction: Buy"]}
        def post(url, timeout=None, json=None):
            m, p = json["method"], json["params"]
            if m == "getSignaturesForAddress":
                res = [{"signature": "S1", "blockTime": now, "err": None},
                       {"signature": "S2", "blockTime": now, "err": None},
                       {"signature": "S3", "blockTime": now, "err": {"x": 1}}]
            else:
                res = {"meta": {"logMessages": txs[p[0]], "postTokenBalances": [
                    {"mint": grads.WSOL}, {"mint": "Grad" + p[0] + "pump"}]}}
            return Resp({"jsonrpc": "2.0", "id": 1, "result": res})
        with mock.patch("requests.post", post):
            self.assertEqual(grads.fetch(), 1)
        self.assertEqual(grads.recent(), ["GradS1pump"])     # a non-migration tx adds nothing
        self.assertEqual(grads.load()["last_sig"], "S1")

    def test_fake_cap_and_dead_volume(self):
        # the Oct 19 clones: a $300M "cap" on a $1.5M pool trading $10k an hour
        self.assertEqual(self.verdict(ds=ds_pairs(liq=1500000, mcap=300e6, vol=10000))["reason"], "fake_cap")
        self.assertEqual(self.verdict(ds=ds_pairs(liq=200000, mcap=1e6, vol=2000))["reason"], "dead_volume")
        self.assertEqual(self.verdict(ds=ds_pairs(liq=20000, mcap=150000, vol=40000))["verdict"], "PASS")

    def test_goplus_also_says_mintable(self):
        v = self.verdict(gp=goplus(mintable={"status": "1"}))
        self.assertEqual(v["reason"], "mint_open")

    def test_pool_kills(self):
        cases = {
            "no_pool": [],
            "thin_pool": ds_pairs(liq=10000),
            "too_fresh": ds_pairs(age_min=10),
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


class Sizing(Base):
    def test_more_signals_bigger_ticket_capped_by_the_pool(self):
        import size
        calm = {"symbol": "A", "liq_usd": 80000, "vol_1h": 5000, "buys_5m": 2, "sells_5m": 2}
        hot = {"symbol": "B", "liq_usd": 80000, "vol_1h": 120000, "buys_5m": 40, "sells_5m": 10, "avg_trade_1h": 60}
        usd0, tier0, _ = size.ticket({"score": 60}, calm)
        usd1, tier1, sig = size.ticket({"score": 90}, hot)
        self.assertEqual((tier0, tier1), ("base", "max"), sig)       # tiers still recorded for AUDIT
        self.assertEqual(usd0, config.PAPER_BANKROLL_USD * config.SIZING["base"] / 100)
        self.assertEqual(usd1, usd0)                                  # flat tickets since Oct 19
        with mock.patch.dict(config.SIZING, {"strong": 8, "max": 14}):
            self.assertGreater(size.ticket({"score": 90}, hot)[0], usd0)   # the mechanism, once signals earn it
        thin = dict(hot, liq_usd=1500)                                # the pool caps the ticket below $40
        self.assertEqual(size.ticket({"score": 90}, thin)[0], 1500 * config.FACTS["max_ticket_share"])
        # the same activity made of $5 swaps (a bot farm) earns no signal
        self.assertEqual(size.ticket({"score": 60}, dict(hot, avg_trade_1h=5))[1], "base")


class Book(Base):
    def test_paper_buy_and_limits(self):
        check.ECHO_MODE = "observe"
        self.addCleanup(setattr, check, "ECHO_MODE", check.ECHO_MODE)
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

    def test_no_cash(self):
        with open(config.TRADES, "w") as f:
            f.write("time,mint,symbol,action,usd,pnl,reason\n2020-01-01 00:00,A,A,close,0,-990,stop\n")
        self.assertEqual(book.guard(MINT), "no_cash")

    def test_max_open(self):
        for i in range(config.MAX_OPEN):
            book.open_position(f"M{i}", "M", 1.0, 100000)
        self.assertEqual(book.guard(MINT), "max_open")


class Exits(Base):
    def tick(self, price, liq=80000):
        with mock.patch("requests.get", fake_get(ds=ds_pairs(price=price, liq=liq))):
            return [e["text"] for e in watch.watch()[0]]

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
            e = [x["text"] for x in watch.watch()[0]]
        self.assertIn("pool_gone", e[0])
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


class Agents(Base):
    def setUp(self):
        super().setUp()
        for f in (config.EVENTS, config.AGENTS, config.EQUITY, config.AUDIT):
            if os.path.exists(f):
                os.remove(f)

    def test_vigie_logs_balance_and_sells(self):
        import agents, events
        book.open_position(MINT, "TEST", 1.0, 80000)
        with mock.patch("requests.get", fake_get(ds=ds_pairs(price=2.0))):
            agents.vigie()
        with open(config.EQUITY) as f:
            last = f.read().strip().splitlines()[-1].split(",")
        # half sold at +100% (+12.5 realized), the other half still open at +100% (+12.5 latent)
        self.assertAlmostEqual(float(last[1]), config.PAPER_BANKROLL_USD + 25, places=2)
        sells = [e for e in events.recent() if e["kind"] == "sell"]
        self.assertEqual(sells[0]["reason"], "take_profit_100")

    def test_scout_hands_leads_to_garde(self):
        import agents, events
        check.ECHO_MODE = "observe"
        self.addCleanup(setattr, check, "ECHO_MODE", check.ECHO_MODE)
        prof = [{"chainId": "solana", "tokenAddress": MINT}]
        def get(url, timeout=None, params=None, headers=None):
            if "token-profiles" in url or "token-boosts" in url:
                return Resp(prof)
            return fake_get()(url, timeout, params)
        with mock.patch("requests.get", get), mock.patch("requests.post", Chain()):
            agents.scout()
        kinds = [e["kind"] for e in events.recent()]
        self.assertIn("pass", kinds)
        self.assertIn("buy", kinds)
        self.assertIn(MINT, book.load())

    def test_audit_scores_old_kills(self):
        import audit
        old = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - 8 * 3600))
        check.log({"time": old, "mint": MINT, "symbol": "TEST", "stage": "facts", "verdict": "SKIP",
                   "reason": "whale", "price": 1.0, "liq_usd": 50000})
        with mock.patch("requests.get", fake_get(ds=ds_pairs(price=0.2))):
            rows = audit.audit()
        self.assertEqual(rows[0]["change_pct"], -80.0)
        self.assertEqual(audit.summary()["killed"], {"n": 1, "crashed": 1})


class Inbox(Base):
    def test_pasted_ca_goes_through_garde(self):
        import agents, events
        check.ECHO_MODE = "observe"
        self.addCleanup(setattr, check, "ECHO_MODE", check.ECHO_MODE)
        for f in (config.EVENTS, config.AGENTS):
            if os.path.exists(f):
                os.remove(f)
        with open(agents.INBOX, "w") as f:
            f.write(MINT + "\n" + MINT + "\n")
        with net():
            agents.inbox()
        self.assertFalse(os.path.exists(agents.INBOX))
        kinds = [e["kind"] for e in events.recent()]
        self.assertEqual(kinds.count("buy"), 1)            # same CA twice is checked once
        self.assertIn(MINT, book.load())

    def test_report_names_a_number_to_question(self):
        import audit
        with open(config.AUDIT, "w") as f:
            f.write(",".join(audit.FIELDS) + "\n")
            for i, ch in enumerate([150, 220, -10, 300]):
                f.write(f"2026-01-01 00:00,M{i},S{i},pool,SKIP,too_fresh,1,1,{ch},6\n")
        out = report.report()
        self.assertIn("question: min_age_min", out)


class Gate(Base):
    """ECHO_MODE = gate: a PASS waits for ECHO's X read, and only an X BUY opens a position."""
    def setUp(self):
        super().setUp()
        import pending
        self.p = pending
        self.addCleanup(setattr, check, "ECHO_MODE", check.ECHO_MODE)
        check.ECHO_MODE = "gate"
        for f in (pending.PENDING, pending.X_READS, pending.X_QUEUE):
            if os.path.exists(f):
                os.remove(f)

    def test_observe_buys_at_once_and_echo_still_reads(self):
        check.ECHO_MODE = "observe"
        with net():
            v = check.run(MINT)
        self.assertIn("PAPER BUY", v["action"])
        self.assertIn(MINT, book.load())
        self.p.decide()
        with open(self.p.X_QUEUE) as f:
            self.assertIn(MINT, f.read())             # ECHO gets it to read
        self.x_read("SKIP")
        with net():
            ev = self.p.decide()
        self.assertEqual(self.p.load(), {})
        self.assertIn("after the buy", ev[0]["text"])
        self.assertIn(MINT, book.load())              # a SKIP is recorded only: ECHO said SKIP to nearly all
        self.x_read("SCAM")
        with net():
            ev = self.p.decide()
        self.assertNotIn(MINT, book.load())           # a SCAM (concrete evidence) closes it
        self.assertTrue(any(e.get("reason") == "x_scam" for e in ev), ev)

    def x_read(self, verdict):
        with open(self.p.X_READS, "w") as f:
            f.write(f"time,mint,symbol,verdict,raison\n2026-10-19 10:00,{MINT},TEST,{verdict},lecture test\n")

    def test_pass_waits_and_is_queued_for_echo(self):
        with net():
            v = check.run(MINT)
        self.assertIn("waiting for ECHO", v["action"])
        self.assertNotIn(MINT, book.load())
        self.p.decide()
        with open(self.p.X_QUEUE) as f:
            self.assertIn(MINT, f.read())

    def test_x_buy_opens_at_the_current_price(self):
        with net():
            check.run(MINT)
        self.x_read("BUY")
        with net(ds=ds_pairs(price=0.0012)):
            out = self.p.decide()
        self.assertEqual(out[0]["kind"], "buy")
        self.assertAlmostEqual(book.load()[MINT]["entry"], 0.0012)
        self.assertEqual(self.p.load(), {})

    def test_x_skip_drops_it(self):
        with net():
            check.run(MINT)
        self.x_read("SKIP")
        out = self.p.decide()
        self.assertEqual(out[0]["reason"], "x_skip")
        self.assertNotIn(MINT, book.load())

    def test_no_read_in_time_drops_it(self):
        with net():
            check.run(MINT)
        p = self.p.load(); p[MINT]["since"] -= 2 * 3600; self.p.save(p)
        out = self.p.decide()
        self.assertEqual(out[0]["reason"], "x_timeout")

    def test_low_score_is_not_bought(self):
        # bots: 300 holders trading $200k an hour, and a score under the explore floor too
        with net(gp=goplus(holder_count="300"), ds=ds_pairs()):
            with mock.patch("score.score", return_value={"score": 25, "flags": ["bot_volume"]}), \
                 mock.patch("check.score", return_value={"score": 25, "flags": ["bot_volume"]}):
                v = check.run(MINT)
        self.assertIn("not bought: score 25", v["action"])
        self.assertEqual(self.p.load(), {})


class Score(unittest.TestCase):
    def test_ranks_like_a_human(self):
        from score import score
        organic = score({"vol_1h": 25368, "buys_1h": 181, "sells_1h": 192, "age_min": 1470, "liq_usd": 49499},
                        {"holders": 2980, "top10_pct": 13.3, "max_wallet_pct": 2.1, "dev_pct": 0.19})
        bots = score({"vol_1h": 271889, "buys_1h": 1496, "sells_1h": 1451, "age_min": 588, "liq_usd": 113364},
                     {"holders": 399, "top10_pct": 23.7, "max_wallet_pct": 3.9, "dev_pct": 0})
        self.assertGreater(organic["score"], 80)
        self.assertLessEqual(bots["score"], 40)
        self.assertIn("bot_volume", bots["flags"])


class ExitRules(unittest.TestCase):
    """exits.decide on hand-built ticks, one rule at a time."""
    P = dict(config.EXIT)

    def pos(self, **kw):
        p = {"entry": 1.0, "qty0": 25, "qty": 25, "peak": 1.0, "peak_t": 0, "liq0": 100000, "opened": 0, "steps": 0}
        p.update(kw)
        return p

    def tick(self, price, t=600, **kw):
        s = {"t": t, "price": price, "liq": 100000, "b5": 10, "s5": 10, "v5": 1000, "vol": None, "v5_avg": 1000}
        s.update(kw)
        return s

    def test_lock_keeps_a_winner_from_turning_red(self):
        import exits
        self.assertEqual(exits.decide(self.pos(peak=1.45), self.tick(1.04), self.P), (1.0, "lock"))

    def test_chandelier_is_wider_on_a_wild_token(self):
        import exits
        pos = self.pos(peak=1.8)
        # calm token (3% bars -> 15% floor): 20% under the peak is out
        self.assertEqual(exits.decide(pos, self.tick(1.44, vol=3), self.P), (1.0, "trailing_stop"))
        # wild token (12% bars -> 36% trail): the same 20% dip is noise, hold
        self.assertIsNone(exits.decide(pos, self.tick(1.44, vol=12), self.P))

    def test_dump_needs_the_volume_to_collapse(self):
        import exits
        pos = self.pos(peak=1.6)
        wild = {"vol": 14}                                       # 40% trail, so the dump rule decides
        self.assertIsNone(exits.decide(pos, self.tick(1.1, v5=900, **wild), self.P))
        self.assertEqual(exits.decide(pos, self.tick(1.1, v5=300, **wild), self.P), (1.0, "dump"))

    def test_stall_takes_profit_when_sellers_take_over(self):
        import exits
        pos = self.pos(peak=1.3, peak_t=0)
        self.assertIsNone(exits.decide(pos, self.tick(1.25, t=10 * 60, b5=10, s5=30), self.P))     # too soon
        self.assertEqual(exits.decide(pos, self.tick(1.25, t=50 * 60, b5=10, s5=30), self.P), (1.0, "stall"))
        self.assertIsNone(exits.decide(pos, self.tick(1.25, t=50 * 60, b5=30, s5=30), self.P))    # buyers still there


class ExitLab(Base):
    def setUp(self):
        super().setUp()
        import exits, shutil
        if os.path.exists(exits.PROFILE):
            os.remove(exits.PROFILE)
        shutil.rmtree(config.PATHS, ignore_errors=True)

    def paths_of(self, shape, n=40):
        import paths
        base = time.time() - 3 * 86400
        with open(config.TRADES, "w") as f:
            f.write("time,mint,symbol,action,usd,pnl,reason\n")
            for i in range(n):
                t0 = base + i * 3600
                mint = f"LAB{i}"
                f.write(f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(t0))},{mint},L,open,25,0,entry\n")
                f.write(f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(t0 + 7200))},{mint},L,close,25,0,stop\n")
                for k in range(360):
                    paths.append(mint, {"t": t0 + k * 20, "price": shape(k), "liq": 100000, "b5": 10, "s5": 10, "v5": 1000})

    def test_current_profile_beats_the_article_on_a_slow_bleed(self):
        import exitlab
        self.paths_of(lambda k: 1 + 0.8 * k / 180 if k <= 180 else 1.8 - 1.1 * (k - 180) / 180)
        res = exitlab.run()
        pnl = {r["name"]: r["pnl"] for r in res["results"]}
        self.assertGreater(pnl["actif"], 0)
        self.assertLess(pnl["article"], 0)
        self.assertIsNone(res["switched"])          # nothing beats the active profile by the margin

    def test_autotune_switches_when_a_profile_wins_on_both_halves(self):
        import exitlab, exits
        # +60% then a one-tick crash to -50%: no trail can react, only selling into strength helps
        self.paths_of(lambda k: 1 + 0.6 * k / 60 if k <= 60 else 0.5)
        self.assertIsNone(exitlab.run()["switched"])            # off: VIGIE's guarded self-review decides now
        with mock.patch.object(exitlab, "EXIT_AUTOTUNE", True):
            res = exitlab.run()
        self.assertEqual(res["switched"], "early ladder +50% +100%")
        self.assertEqual(exits.active()["ladder"], [[50, 0.33], [100, 0.33]])

    def test_speed_test_replays_three_speeds(self):
        import exitlab
        # +60% in 20 min, held 2 min at the top, then -55% in one tick
        self.paths_of(lambda k: 1 + 0.6 * min(k, 60) / 60 if k <= 66 else 0.45, n=4)
        sp = exitlab.run()["speed"]
        self.assertEqual([r["every_s"] for r in sp], [20, 60, 120])
        self.assertEqual(len({r["n"] for r in sp}), 1)


class Regime(Base):
    def test_audit_splits_passes_by_sol_trend(self):
        import audit
        for f in (config.AUDIT,):
            if os.path.exists(f):
                os.remove(f)
        check.log({"time": "2026-01-01 00:00", "mint": "UP", "stage": "judge", "verdict": "PASS", "sol_24h": 2.5})
        check.log({"time": "2026-01-01 00:00", "mint": "DOWN", "stage": "judge", "verdict": "PASS", "sol_24h": -4})
        with open(config.AUDIT, "w") as f:
            f.write(",".join(audit.FIELDS) + "\n")
            f.write("2026-01-01 06:00,UP,U,judge,PASS,,1,1.2,20,6\n")
            f.write("2026-01-01 06:00,DOWN,D,judge,PASS,,1,0.3,-70,6\n")
        r = audit.summary()["regime"]
        self.assertEqual((r["SOL up"]["n"], r["SOL up"]["crashed"]), (1, 0))
        self.assertEqual((r["SOL down"]["n"], r["SOL down"]["crashed"]), (1, 1))


class Ruggers(Base):
    def setUp(self):
        super().setUp()
        import ruggers
        for f in (ruggers.FILE, config.AUDIT):
            if os.path.exists(f):
                os.remove(f)

    def test_audit_blacklists_the_creator_of_a_collapsed_token_and_garde_kills_its_next_one(self):
        import audit, ruggers
        dev = facts._b58(bytes(range(40, 72)))                 # the coin_creator in the fake pool
        old = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - 8 * 3600))
        check.log({"time": old, "mint": "OLDRUG", "symbol": "R", "stage": "judge", "verdict": "PASS",
                   "price": 1.0, "dev": dev})
        with mock.patch("requests.get", fake_get(ds=[])):     # pool gone: -100%
            audit.audit()
        self.assertIn(dev, ruggers.known())
        with net():
            v = check.check(MINT)
        self.assertEqual((v["stage"], v["reason"]), ("facts", "dev_rugged_before"))

    def test_vigie_blacklists_on_a_pulled_pool(self):
        import agents, ruggers
        check.log({"time": "2026-01-01 00:00", "mint": MINT, "symbol": "TEST", "stage": "judge",
                   "verdict": "PASS", "dev": "DEVWALLET"})
        book.open_position(MINT, "TEST", 1.0, 80000)
        with mock.patch("requests.get", fake_get(ds=ds_pairs(price=1.1, liq=20000))):
            agents.vigie()
        self.assertIn("DEVWALLET", ruggers.known())


class MomentumLane(Base):
    """Survivors older than 72 h are bought on their move, not on their youth."""
    def old(self, **kw):
        ds = ds_pairs(age_min=10 * 24 * 60, liq=kw.pop("liq", 400000), vol=kw.pop("vol", 120000),
                      dex=kw.pop("dex", "raydium"), mcap=2e6)
        ds[0]["volume"].update(h6=kw.pop("vol6", 300000), h24=kw.pop("vol24", 1500000))
        ds[0]["priceChange"] = {"m5": kw.pop("m5", 1.5), "h1": kw.pop("h1", 12), "h24": kw.pop("h24", 40)}
        ds[0]["txns"]["h1"] = {"buys": 900, "sells": 700}
        return ds

    def test_a_rising_survivor_passes_without_lp_proof(self):
        v = self.verdict(ds=self.old())                     # Raydium: no LP burn readable, no dev recorded
        self.assertEqual(v["verdict"], "PASS", v)
        self.assertEqual(v.get("lane"), "momentum")

    def test_no_move_no_buy(self):
        self.assertEqual(self.verdict(ds=self.old(h1=0.5))["reason"], "no_momentum")
        self.assertEqual(self.verdict(ds=self.old(vol=40000))["reason"], "no_momentum")     # volume fading
        self.assertEqual(self.verdict(ds=self.old(h1=150))["reason"], "overextended")
        self.assertEqual(self.verdict(ds=self.old(liq=60000))["reason"], "thin_pool")

    def test_a_launch_still_needs_its_lp_proof(self):
        self.assertEqual(self.verdict(ds=ds_pairs(dex="raydium"))["reason"], "lp_unverified")


class GraduationRule(Base):
    def test_a_launch_under_its_graduation_price_waits(self):
        import grads
        if os.path.exists(grads.STATE):
            os.remove(grads.STATE)
        now = time.time()
        def post(url, timeout=None, json=None):
            m, p = json["method"], json["params"]
            if m == "getSignaturesForAddress":
                res = [{"signature": "S1", "blockTime": now - 7200, "err": None}]
            else:
                res = {"meta": {"logMessages": ["Program log: Instruction: Migrate"], "postTokenBalances": [
                    {"mint": grads.WSOL, "owner": "POOL", "uiTokenAmount": {"uiAmount": 80.0}},
                    {"mint": MINT, "owner": "POOL", "uiTokenAmount": {"uiAmount": 200_000_000.0}},
                    {"mint": grads.WSOL, "owner": "BUYER", "uiTokenAmount": {"uiAmount": 2.0}},
                    {"mint": MINT, "owner": "BUYER", "uiTokenAmount": {"uiAmount": 1_000_000.0}}]}}
            return Resp({"jsonrpc": "2.0", "id": 1, "result": res})
        with mock.patch("requests.post", post):
            grads.fetch()
        self.assertAlmostEqual(grads.birth_price(MINT), 80 / 200_000_000)       # the pool, not the buyer
        ds = ds_pairs(); ds[0]["priceNative"] = str(0.5 * 80 / 200_000_000)      # half its graduation price
        self.assertEqual(self.verdict(ds=ds)["reason"], "below_graduation")
        ds[0]["priceNative"] = str(1.3 * 80 / 200_000_000)
        self.assertNotEqual(self.verdict(ds=ds)["reason"], "below_graduation")
        os.remove(grads.STATE)


class Farms(Base):
    """The Oct 19 rugs: FOMO and Gemini, one factory, bot volume, hundreds of identical bags."""
    def test_micro_trades_kill(self):
        ds = ds_pairs(liq=80000, vol=20000)
        ds[0]["txns"]["h1"] = {"buys": 2500, "sells": 2400}        # $4 a swap
        self.assertEqual(self.verdict(ds=ds)["reason"], "micro_trades")

    def test_a_recycled_name_is_a_serial_farm(self):
        import market
        market._tickers.clear()
        dead = [{"chainId": "solana", "dexId": "pumpswap", "baseToken": {"address": f"DEAD{i}", "symbol": "TEST"},
                 "liquidity": {"usd": 1880}, "pairCreatedAt": (time.time() - (5 + i) * 3600) * 1000,
                 "volume": {"h24": 60000}, "txns": {"h24": {"buys": 6000, "sells": 6000}}} for i in range(3)]
        def get(url, timeout=None, params=None):
            if "search" in url:
                return Resp({"pairs": dead})
            return fake_get()(url, timeout, params)
        with mock.patch("requests.get", get), mock.patch("requests.post", Chain()):
            self.assertEqual(check.check(MINT)["reason"], "serial_farm")
        # namesakes that died with human-sized swaps (copies of a runner) are not a factory
        market._tickers.clear()
        for d in dead:
            d["txns"]["h24"] = {"buys": 600, "sells": 600}
        with mock.patch("requests.get", get), mock.patch("requests.post", Chain()):
            self.assertNotEqual(check.check(MINT)["reason"], "serial_farm")

    def test_identical_bags_are_a_farm(self):
        supply = 10**15
        farm = [{"owner": f"F{i}", "amount": str(460_000_000_000 + i * 1000)} for i in range(300)]   # 0.046% each
        organic = [{"owner": f"O{i}", "amount": str(int(supply * 0.002 * (0.9 ** i)))} for i in range(40)]
        n, pct = facts.holder_farm(farm + organic, supply, set())
        self.assertGreaterEqual(n, 300)
        self.assertGreater(pct, 13)
        self.assertLess(facts.holder_farm(organic, supply, set())[0], 3)
        t = {"mint_authority": None, "freeze_authority": None, "danger": [], "lp_burned_pct": 100, "dev_pct": 0,
             "top10_pct": 10, "max_wallet_pct": 2, "same_sol_wallets": 1, "ladder_wallets": 1,
             "farm_wallets": n, "farm_pct": pct}
        self.assertEqual(facts.fact_kill(t), "holder_farm")

    def test_stale_dexscreener_data_is_not_bought(self):
        ds = ds_pairs()
        ds[0]["liquidity"]["quote"] = 500.0                         # DexScreener still shows 500 SOL...
        with net(ds=ds), mock.patch.object(facts, "pool_vaults", lambda pair: ["VB", "VQ"]), \
                mock.patch.object(facts, "reserves", lambda v: [990e6, 0.4]):                  # ...the chain 0.4
            self.assertEqual(check.check(MINT)["reason"], "stale_data")


class DeepRead(Base):
    def test_jupiter_kills(self):
        import jup
        t = {"id": MINT, "organicScore": 12.5, "audit": {"devMints": 3},
             "stats1h": {"buyVolume": 50000, "sellVolume": 50000, "buyOrganicVolume": 1000,
                         "sellOrganicVolume": 1000, "numTraders": 400}}
        with mock.patch("requests.get", lambda *a, **k: Resp([t])):
            j = jup.fetch(MINT)
        self.assertEqual(j["organic_vol_share"], 2.0)
        self.assertEqual(jup.kill(j, config.DEEP), "inorganic_volume")
        self.assertEqual(jup.kill(dict(j, sus=True), config.DEEP), "jup_sus")
        self.assertEqual(jup.kill(dict(j, dev_mints=80), config.DEEP), "serial_dev")
        # nothing known is never a kill
        self.assertIsNone(jup.kill({k: None for k in j} | {"sus": False}, config.DEEP))

    def test_solana_tracker_kills_bundles(self):
        import stracker
        risk = {"risk": {"rugged": False, "snipers": {"totalPercentage": 3}, "insiders": {"totalPercentage": 2},
                         "bundlers": {"totalPercentage": 31, "totalInitialPercentage": 40}, "top10": 20,
                         "dev": {"percentage": 0}, "risks": [], "score": 4}}
        with mock.patch.object(stracker, "key", lambda: "K"), mock.patch("requests.get", lambda *a, **k: Resp(risk)):
            st = stracker.fetch(MINT)
        self.assertEqual(stracker.kill(st, config.DEEP), "bundled")

    def test_one_funder_behind_the_top_holders(self):
        import cluster
        holders = [(f"H{i}", 3.0) for i in range(6)]
        def rpc(method, params):
            if method == "getSignaturesForAddress":
                return [{"signature": "S" + params[0]}] * (5 if params[0].startswith("H") else 10)
            if method == "getTransaction":       # H0-H3 got their first SOL from FARM, the rest from elsewhere
                w = params[0][1:]
                src = "FARM" if w in ("H0", "H1", "H2", "H3") else "X" + w
                return {"transaction": {"message": {"accountKeys": [src, w]}},
                        "meta": {"preBalances": [10**10, 0], "postBalances": [10**10 - 10**8, 10**8]}}
        with mock.patch.object(facts, "_rpc", rpc):
            c = cluster.analyze(holders)
        self.assertEqual((c["cluster_funder"], c["cluster_wallets"], c["cluster_pct"]), ("FARM", 4, 12.0))
        self.assertEqual(cluster.kill(c, config.DEEP, set()), "funded_cluster")
        self.assertEqual(cluster.kill(c, config.DEEP, {"XH4"}), "rug_funder")

    def test_factory_wallets_are_remembered(self):
        import smart
        wallets = [f"W{i}" for i in range(8)]
        for i, mint in enumerate(("RUG1", "RUG2")):
            smart.snapshot(mint, wallets)
            smart.learn(mint, -95)
        self.assertEqual(smart.toxic(wallets + ["OTHER"]), 8)
        self.assertEqual(smart.learn("RUG2", -95), 0)          # never counted twice
        token = {"all_owners": wallets}
        self.assertEqual(check.deep_read(MINT, token)["kill"], "factory_wallets")
        import shutil
        shutil.rmtree(smart.HOLDERS, ignore_errors=True)
        if os.path.exists(smart.MEMORY):
            os.remove(smart.MEMORY)


class EchoScam(Base):
    def test_a_scam_read_sells_the_open_position(self):
        import pending
        for f in (pending.PENDING, pending.X_READS, pending.X_QUEUE):
            if os.path.exists(f):
                os.remove(f)
        self.addCleanup(setattr, check, "ECHO_MODE", check.ECHO_MODE)
        check.ECHO_MODE = "observe"
        with net():
            check.run(MINT)
        self.assertIn(MINT, book.load())
        with open(pending.X_READS, "w") as f:
            f.write(f"time,mint,symbol,verdict,raison\n2026-10-19 10:00,{MINT},TEST,SCAM,nom deja rug cette semaine\n")
        with net():
            ev = pending.decide()
        self.assertNotIn(MINT, book.load())
        self.assertTrue(any(e["kind"] == "sell" and e["reason"] == "x_scam" for e in ev), ev)


class EchoSkipRetro(Base):
    def test_a_position_echo_already_skipped_is_sold(self):
        import pending
        for f in (pending.PENDING, pending.X_READS, pending.X_QUEUE):
            if os.path.exists(f):
                os.remove(f)
        book.open_position(MINT, "TEST", 0.001, 80000)
        with open(pending.X_READS, "w") as f:
            f.write(f"time,mint,symbol,verdict,raison\n2026-10-19 12:00,{MINT},TEST,SKIP,pas de narratif\n")
        with net():
            pending.decide()
        self.assertIn(MINT, book.load())                            # an old SKIP no longer sells
        with open(pending.X_READS, "w") as f:
            f.write(f"time,mint,symbol,verdict,raison\n2026-10-19 12:00,{MINT},TEST,SCAM,phishing recycle\n")
        with net():
            ev = pending.decide()
        self.assertNotIn(MINT, book.load())                         # an old SCAM does
        self.assertEqual(ev[-1]["reason"], "x_scam")
        with net():
            self.assertEqual(check.check(MINT)["reason"], "x_scam_before")   # and it is never bought again
        os.remove(pending.X_READS)


class Living(Base):
    def test_income_is_capped_by_the_pools_not_the_bankroll(self):
        import edge
        t0 = time.time() - 10 * 86400
        with open(config.TRADES, "w") as f:
            f.write("time,mint,symbol,action,usd,pnl,reason\n")
            for i in range(50):                     # 50 trades over 10 days, +5% each on $50
                ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(t0 + i * 3600))
                f.write(f"{ts},M{i},M,open,50,0,entry\n{ts},M{i},M,close,52.5,2.5,trail\n")
        for i in range(50):
            check.log({"time": "2026-10-19 10:00", "mint": f"M{i}", "verdict": "PASS", "liq_usd": 40000})
        with mock.patch.object(edge, "RULES_SINCE", "2000-01-01 00:00"):    # these trades predate today's rules
            L = edge.living(2200)
        self.assertEqual(L["ticket_cap"], 40000 * config.FACTS["max_ticket_share"])     # $800
        self.assertAlmostEqual(L["trades_per_day"], 5.0, delta=0.1)
        self.assertAlmostEqual(L["month"]["mean_pct"], 0.05 * 800 * 5 * 30, delta=150)  # ~$6,000
        self.assertAlmostEqual(L["return_needed_pct"], 2200 / (800 * 5 * 30) * 100, delta=0.2)


class Team(Base):
    """What makes them a team: one book, shared dossiers, a rug that reaches every agent."""
    def test_a_rug_sells_the_positions_its_holders_are_in(self):
        import agents, smart
        wallets = [f"F{i}" for i in range(8)]
        smart.snapshot("RUGGED", wallets)
        smart.snapshot(MINT, wallets[:6] + ["X1", "X2"])        # 6 holders in common
        smart.snapshot("CLEAN", ["Y1", "Y2", "F0"])             # 1 in common
        book.open_position(MINT, "TWIN", 0.001, 80000)
        book.open_position("CLEAN", "CLEAN", 0.001, 80000)
        with net():
            agents.on_rug("RUGGED", "RUG", "liquidity_pulled")
        self.assertNotIn(MINT, book.load())
        self.assertIn("CLEAN", book.load())
        import shutil
        shutil.rmtree(smart.HOLDERS, ignore_errors=True)
        for f in (smart.MEMORY,):
            if os.path.exists(f):
                os.remove(f)

    def test_a_sale_on_a_closed_position_is_a_no_op(self):
        book.open_position(MINT, "TEST", 0.001, 80000)
        book.sell(MINT, 1.0, 0.002, "test")
        self.assertEqual(book.sell(MINT, 1.0, 0.002, "test again"), 0.0)

    def test_every_agent_writes_the_same_dossier(self):
        import dossier, pending
        for f in (pending.PENDING, pending.X_READS, pending.X_QUEUE):
            if os.path.exists(f):
                os.remove(f)
        self.addCleanup(setattr, check, "ECHO_MODE", check.ECHO_MODE)
        check.ECHO_MODE = "observe"
        with net():
            check.run(MINT)
            pending.decide()
        whats = [(e["agent"], e["what"]) for e in dossier.load(MINT)["entries"]]
        self.assertIn(("GARDE", "PASS"), whats)
        self.assertIn(("GARDE", "achat"), whats)
        with open(pending.X_QUEUE) as f:
            self.assertIn("note", f.read())                     # ECHO's queue carries GARDE's case

    def test_vigie_runs_on_its_own_thread(self):
        import agents, threading
        calls = []
        with mock.patch.object(agents, "vigie", lambda: calls.append(1) or "ok"):
            stop = threading.Event()
            th = agents.start_vigie(stop)
            time.sleep(0.3)
            stop.set(); th.join(2)
        self.assertTrue(calls)


class OnChainVigie(Base):
    def test_a_drained_pool_is_sold_even_if_dexscreener_lags(self):
        book.open_position(MINT, "TEST", 0.001, 80000, vaults=["VB", "VQ"], sol0=200)
        ds = ds_pairs(price=0.001, liq=80000)          # DexScreener still shows the old pool...
        ds[0]["priceNative"] = "0.00000500"            # SOL = $200
        with mock.patch("requests.get", fake_get(ds=ds)), \
                mock.patch.object(facts, "reserves", lambda v: [990e6, 0.4]):    # ...the chain: drained
            watch._mismatch.clear()
            watch.watch()                                  # first tick: the chain must agree twice
            out = watch.watch()[0]
        self.assertTrue(out and out[0]["reason"] == "liquidity_pulled", out)
        self.assertNotIn(MINT, book.load())


class QuoteTokens(Base):
    def setUp(self):
        super().setUp()
        watch._mismatch.clear(); watch._quote_usd.clear()

    def test_a_pool_quoted_in_xmr_is_priced_in_xmr(self):
        # Oct 19 soak test: LUKE's PumpSwap pool is against XMR, priced as SOL it read -84%
        book.open_position(MINT, "LUKE", 0.0005672, 71600, vaults=["VB", "VQ"], sol0=58.7)
        ds = ds_pairs(price=0.0005672, liq=71600)
        ds[0]["priceNative"] = "0.000000953"                     # in XMR: XMR = $595
        with mock.patch("requests.get", fake_get(ds=ds)), \
                mock.patch.object(facts, "reserves", lambda v: [64_800_000, 61.75]):   # 61.75 XMR / 64.8M tokens
            out = watch.watch()[0]
        self.assertEqual(out, [])
        self.assertIn(MINT, book.load())

    def test_one_misread_tick_never_sells(self):
        book.open_position(MINT, "TEST", 0.001, 80000, vaults=["VB", "VQ"], sol0=200)
        ds = ds_pairs(price=0.001, liq=80000)
        ds[0]["priceNative"] = "0.00000500"
        bad = mock.patch.object(facts, "reserves", lambda v: [990e6, 0.4])        # a drained-looking read
        with mock.patch("requests.get", fake_get(ds=ds)), bad:
            self.assertEqual(watch.watch()[0], [])                                 # first tick: wait
            self.assertIn(MINT, book.load())
            out = watch.watch()[0]                                                  # second tick agrees: sell
        self.assertTrue(out and out[0]["reason"] == "liquidity_pulled", out)


class Copycat(Base):
    def test_a_smaller_token_under_a_bigger_ticker_is_killed(self):
        import market
        market._tickers.clear()
        big = {"chainId": "solana", "baseToken": {"address": "BIGONE", "symbol": "TEST"}, "liquidity": {"usd": 900000},
               "volume": {"h24": 2000000},
               "pairCreatedAt": (time.time() - 9 * 3600) * 1000}
        def get(url, timeout=None, params=None):
            if "search" in url:
                return Resp({"pairs": [big]})
            return fake_get()(url, timeout, params)
        with mock.patch("requests.get", get), mock.patch("requests.post", Chain()):
            v = check.check(MINT)
        self.assertEqual((v["stage"], v["reason"]), ("pool", "copycat"))
        # the same name on a token from last year is not a rival: no kill
        market._tickers.clear()
        big["pairCreatedAt"] = (time.time() - 400 * 86400) * 1000
        with mock.patch("requests.get", get), mock.patch("requests.post", Chain()):
            self.assertNotEqual(check.check(MINT).get("reason"), "copycat")
        # a bigger namesake launched AFTER this token is its copy, not its original: no kill (DAC, Oct 19)
        market._tickers.clear()
        big["pairCreatedAt"] = (time.time() - 30 * 60) * 1000          # our token is 120 min old
        with mock.patch("requests.get", get), mock.patch("requests.post", Chain()):
            self.assertNotEqual(check.check(MINT).get("reason"), "copycat")
        market._tickers.clear()


class Breakdown(Base):
    def test_groups_closed_positions_by_entry_hour_and_age(self):
        import audit
        with open(config.TRADES, "w") as f:
            f.write("time,mint,symbol,action,usd,pnl,reason\n"
                    "2026-01-01 02:10,A,A,open,25,0,entry\n2026-01-01 03:00,A,A,close,10,-15,stop\n"
                    "2026-01-01 14:10,B,B,open,25,0,entry\n2026-01-01 15:00,B,B,close,40,15,trailing_stop\n")
        check.log({"time": "2026-01-01 02:10", "mint": "A", "stage": "judge", "verdict": "PASS", "age_min": 90})
        check.log({"time": "2026-01-01 14:10", "mint": "B", "stage": "judge", "verdict": "PASS", "age_min": 900})
        bd = audit.breakdown()
        hour = {b["bucket"]: b for b in bd["hour"]}
        age = {b["bucket"]: b for b in bd["age"]}
        self.assertEqual((hour["00-04"]["n"], hour["00-04"]["pnl"]), (1, -15.0))
        self.assertEqual((hour["12-16"]["n"], hour["12-16"]["pnl"]), (1, 15.0))
        self.assertEqual(age["< 3 h"]["pnl"], -15.0)
        self.assertEqual(age["12-36 h"]["pnl"], 15.0)


class Costs(Base):
    def test_a_round_trip_pays_fees_impact_and_tx(self):
        book.COSTS = True
        self.addCleanup(setattr, book, "COSTS", False)
        book.open_position(MINT, "T", 1.0, 50000)            # $25 on $50k: 0.1% impact + 0.3% fee + 1% MEV
        p = book.load()[MINT]
        self.assertAlmostEqual(p["entry"], 1.014, places=6)
        pnl = book.sell(MINT, 1.0, 1.0, "flat", 50000)       # a flat price loses ~4.7% of a $25 round trip
        self.assertLess(pnl, -1.0)
        self.assertGreater(pnl, -1.4)


class EchoSilent(Base):
    def setUp(self):
        super().setUp()
        import pending
        self.p = pending
        self.addCleanup(setattr, check, "ECHO_MODE", check.ECHO_MODE)
        check.ECHO_MODE = "gate"
        for f in (pending.PENDING, pending.X_READS, pending.X_QUEUE):
            if os.path.exists(f):
                os.remove(f)


    def test_a_strong_pass_is_bought_without_x_when_echo_is_silent(self):
        with net():
            check.run(MINT)
        p = self.p.load(); p[MINT]["since"] -= 50 * 60; p[MINT]["score"] = 80; self.p.save(p)
        with net():
            out = self.p.decide()
        self.assertEqual(out[0]["kind"], "buy")
        self.assertEqual(self.p.reads()[MINT]["verdict"], "NO_X")

    def test_a_weaker_pass_still_waits_then_drops(self):
        with net():
            check.run(MINT)
        p = self.p.load(); p[MINT]["since"] -= 50 * 60; p[MINT]["score"] = 60; self.p.save(p)
        self.assertEqual(self.p.decide(), [])
        self.assertIn(MINT, self.p.load())

    def test_no_fallback_while_echo_is_reading(self):
        with open(self.p.X_READS, "w") as f:
            f.write(f"time,mint,symbol,verdict,raison\n{time.strftime('%Y-%m-%d %H:%M')},OTHER,O,SKIP,lu\n")
        with net():
            check.run(MINT)
        p = self.p.load(); p[MINT]["since"] -= 50 * 60; p[MINT]["score"] = 90; self.p.save(p)
        self.assertEqual(self.p.decide(), [])


class Smart(Base):
    def setUp(self):
        super().setUp()
        import smart, shutil
        shutil.rmtree(smart.HOLDERS, ignore_errors=True)
        if os.path.exists(smart.MEMORY):
            os.remove(smart.MEMORY)
        self.s = smart

    def test_wallets_early_in_two_runners_become_smart_and_lift_the_score(self):
        from score import score
        m = {"vol_1h": 25000, "buys_1h": 180, "sells_1h": 190, "age_min": 600, "liq_usd": 50000,
             "socials": ["telegram", "twitter"]}
        t = {"holders": 2500, "top10_pct": 14, "max_wallet_pct": 2, "dev_pct": 0, "wallets": ["A", "B", "C"]}
        before = score(m, t)["score"]
        for mint in ("R1", "R2"):
            self.s.snapshot(mint, ["A", "B", "X"])
            self.s.learn(mint, 150)
        for mint in ("C1", "C2"):
            self.s.snapshot(mint, ["X"]); self.s.learn(mint, -80)
        self.assertEqual(self.s.count(["A", "B", "C", "X"]), 2)     # X: 2 runs, 2 crashes -> not smart
        after = score(m, t)
        self.assertEqual(after["score"], min(100, before + 10))
        self.assertIn("smart_money", after["flags"])

    def test_no_socials_costs_points(self):
        from score import score
        t = {"holders": 2500, "top10_pct": 14, "max_wallet_pct": 2, "dev_pct": 0}
        base = {"vol_1h": 25000, "buys_1h": 180, "sells_1h": 190, "age_min": 600, "liq_usd": 50000}
        self.assertEqual(score({**base, "socials": ["telegram", "twitter"]}, t)["score"] - score(base, t)["score"], 10)


class Edge(unittest.TestCase):
    def test_verdicts(self):
        import edge, random
        rng = random.Random(3)
        self.assertEqual(edge.stats([1.0] * 10)["verdict"], "wait")
        self.assertEqual(edge.stats([rng.gauss(0.1, 8) for _ in range(80)])["verdict"], "wait")    # 80 < 200
        self.assertEqual(edge.stats([rng.gauss(0.1, 8) for _ in range(250)])["verdict"], "no")
        good = edge.stats([rng.gauss(2.0, 5) for _ in range(250)])
        self.assertEqual(good["verdict"], "yes")
        self.assertLessEqual(good["suggested_ticket"], 0.05 * config.PAPER_BANKROLL_USD)


class Momentum(Gate):
    def test_a_token_that_fell_while_echo_read_is_not_bought(self):
        with net():
            check.run(MINT)                                # PASS at 0.001
        self.x_read("BUY")
        with net(ds=ds_pairs(price=0.0007)):              # -30% by the time ECHO said BUY
            out = self.p.decide()
        self.assertEqual(out[0]["reason"], "momentum_lost")
        self.assertNotIn(MINT, book.load())


class Narratives(Base):
    def test_echo_words_are_searched_first(self):
        import scan
        with open(scan.NARRATIVES, "w") as f:
            f.write("$Gork\nriot\n")
        self.assertEqual(scan.narratives(), ["gork", "riot"])
        seen = []
        def get(url, timeout=None, params=None):
            seen.append((params or {}).get("q"))
            return Resp({"pairs": []})
        with mock.patch("requests.get", get):
            scan.searched(["TICK"])
        self.assertEqual(seen[:3], ["gork", "riot", "tick"])
        os.remove(scan.NARRATIVES)


class MomentumBacktest(Base):
    """The momentum lane replayed from 5-min candles, on tokens SCOUT saw at the time."""
    T0 = 1_000_200

    def candles(self, rise=True):
        cs, price = [], 1.0
        for k in range(-300, 85):                       # 25 h before the sighting, 7 h after
            t = self.T0 + k * 300
            vol = 1500.0
            if rise and k >= -12:                       # the move: +0.4% a candle on doubled volume
                price *= 1.004 if k < 30 else 0.99
                vol = 3000.0
            cs.append((t, price, price, price, price, vol))
        return cs

    def sight(self):
        return {"mint": MINT, "pair": PAIR, "t": self.T0, "liq": 500000, "mcap": None, "avg_trade": 80, "n1h": 300}

    def test_a_move_on_rising_volume_is_entered_and_costed(self):
        import mbacktest
        r = mbacktest.replay(self.sight(), self.candles())
        self.assertTrue(r.get("entered"), r)
        self.assertLessEqual(r["wait_min"], 60)
        self.assertGreater(r["peak_pct"], 0)

    def test_a_flat_token_is_never_entered(self):
        import mbacktest
        self.assertEqual(mbacktest.replay(self.sight(), self.candles(rise=False))["skip"], "no_signal")

    def test_scout_notes_a_momentum_pool_once_per_6h(self):
        import mbacktest
        if os.path.exists(mbacktest.SEEN):
            os.remove(mbacktest.SEEN)
        mbacktest._last_seen.clear()
        m = {"pair": PAIR, "symbol": "OLD", "liq_usd": 200000, "age_min": 10 * 24 * 60, "mcap": 1e6}
        young = {**m, "age_min": 90}
        mbacktest.note({MINT: m, "Young": young})
        mbacktest.note({MINT: m})
        self.assertEqual(mbacktest.n_sightings(), 1)
        os.remove(mbacktest.SEEN)
        mbacktest._last_seen.clear()


class CumulativeBacktest(Base):
    def test_seed_and_new_rows_merge_by_mint_and_score(self):
        import backtest, json as _j
        seed = backtest.rows_all()
        self.assertGreaterEqual(len(seed), 500)
        with open(backtest.ROWS, "w") as f:
            f.write(_j.dumps({**seed[0], "skip": "replayed again"}) + "\n")
        self.assertEqual(len(backtest.rows_all()), len(seed))
        card = backtest.scorecard()
        self.assertIn("early: desk now (60 min + graduation)", card["rules"])
        self.assertEqual(card["rules"]["early: desk now (60 min + graduation)"]["verdict"], "wait")
        os.remove(backtest.ROWS)

    def test_audit_starts_one_batch_every_6h(self):
        import agents, backtest
        if os.path.exists(backtest.STATE):
            os.remove(backtest.STATE)
        started = []

        class Proc:
            def __init__(self, *a, **k):
                started.append(a)

            def poll(self):
                return 0
        agents._bt["proc"] = None
        with mock.patch("subprocess.Popen", Proc):
            agents.backtest_kick()
            agents.backtest_kick()
        self.assertEqual(len(started), 1)
        os.remove(backtest.STATE)
        agents._bt["proc"] = None


class Judge(Base):
    def test_criteria_fixed_on_oct_19(self):
        import edge
        self.assertEqual(edge.judge(18, 2.9, -21)["verdict"], "wait")
        self.assertEqual(edge.judge(300, -0.5, -9)["verdict"], "stop")
        self.assertEqual(edge.judge(250, 1.0, -4)["verdict"], "flat")
        self.assertEqual(edge.judge(250, 4.0, 0.5)["verdict"], "edge")

    def test_bilan_stops_when_paper_and_backtest_are_both_at_or_below_zero(self):
        import edge
        card = {"rules": {"early: desk now (60 min + graduation)": {"n": 40, "mean": -3.0, "ci95": [-20, 10]}}}
        with mock.patch.object(edge, "stats", return_value={"n": 12, "mean_pct": -5.0}):
            self.assertEqual(edge.bilan(card)["verdict"], "stop")
        with mock.patch.object(edge, "stats", return_value={"n": 12, "mean_pct": 4.0}):
            self.assertEqual(edge.bilan(card)["verdict"], "mixed")


class TelegramBot(Base):
    """GARDE as a product: reads only, answers any CA, never touches the book."""
    def test_answers_a_ca_and_logs_it_without_trading(self):
        import tgbot
        sent = []
        r = {"symbol": "RUG", "flags": ["holder_farm", "no_holders"], "context": {"liq": 30000, "age_min": 90}}
        with mock.patch.object(tgbot, "inspect", return_value=r), \
             mock.patch.object(tgbot, "send", lambda tok, chat, msg: sent.append(msg)), \
             mock.patch.object(tgbot.env, "get", lambda k: None):
            tgbot.handle("T", {"chat": {"id": 42}, "text": f"regarde {MINT} stp"})
            tgbot.handle("T", {"chat": {"id": 42}, "text": "/start"})
        self.assertIn("RISQUE ÉLEVÉ", sent[0])
        self.assertIn("ferme de wallets", sent[0])
        self.assertIn("pas un conseil financier", sent[1])
        self.assertEqual(tgbot.stats()["today"], 1)
        self.assertEqual(book.load(), {})

    def test_an_established_token_is_not_red_for_its_cap_alone(self):
        import tgbot
        r = {"symbol": "BONK", "flags": [], "context": {"age_min": 1000 * 1440, "notes": ["fake_cap"]}}
        self.assertEqual(tgbot.verdict(r), "green")
        self.assertIn("exchange", tgbot.text(MINT, {**r, "context": {**r["context"], "notes": ["whale"]}}))

    def test_rate_limit_per_chat(self):
        import tgbot
        sent = []
        tgbot._recent.clear()
        r = {"symbol": "X", "flags": [], "context": {}}
        with mock.patch.object(tgbot, "inspect", return_value=r), \
             mock.patch.object(tgbot, "send", lambda tok, chat, msg: sent.append(msg)), \
             mock.patch.object(tgbot.env, "get", lambda k: None):
            for _ in range(tgbot.PER_CHAT_HOUR + 1):
                tgbot.handle("T", {"chat": {"id": 7}, "text": MINT})
        self.assertIn("Limite", sent[-1])


class HoldersFromHelius(Base):
    """GoPlus and getTokenLargestAccounts empty, Helius DAS full: the top 10 comes from DAS."""
    def test_das_list_fills_the_top_10(self):
        class DasChain(Chain):
            def __call__(self, url, timeout=None, json=None):
                if json["method"] == "getTokenAccounts":
                    accs = [{"owner": PAIR, "amount": "600000"}] + \
                           [{"owner": f"W{i}", "amount": str(20000 - i * 1000)} for i in range(12)]
                    return Resp({"jsonrpc": "2.0", "id": 1, "result": {"token_accounts": accs}})
                return super().__call__(url, timeout=timeout, json=json)
        with net(gp=goplus(holders=[]), chain=DasChain()), mock.patch.object(facts, "RPC_URL", "https://x.helius-rpc.com"):
            t = facts.report(MINT, {"dex": "pumpswap", "pair": PAIR})
        self.assertIsNotNone(t["top10_pct"])
        self.assertEqual(t["holders_source"], "helius_das")
        self.assertAlmostEqual(t["max_wallet_pct"], 2.0)          # the pool's 60% is not a whale


class BacktestAlive(Base):
    def test_a_killed_run_is_started_again_not_waited_for(self):
        import agents, backtest, json as _j
        dead = {"started": time.time() - 3600, "pid": 999999}      # killed an hour ago, never finished
        with open(backtest.STATE, "w") as f:
            _j.dump(dead, f)
        self.assertFalse(backtest.alive(dead))
        started = []

        class Proc:
            def __init__(self, *a, **k):
                started.append(a)

            def poll(self):
                return None
        agents._bt["proc"] = None
        with mock.patch("subprocess.Popen", Proc):
            agents.backtest_kick()
        self.assertEqual(len(started), 1)
        self.assertTrue(backtest.alive({"started": time.time(), "pid": os.getpid()}))
        os.remove(backtest.STATE)
        agents._bt["proc"] = None


class Shadow(Base):
    """GARDE's kills bought in shadow and replayed: the measure of the filter's value."""
    def test_a_kill_is_followed_once_and_scored_after_6h(self):
        import shadow, paths
        for f in (shadow.FILE, paths.GHOSTS):
            if os.path.exists(f):
                os.remove(f)
        v = {"verdict": "SKIP", "stage": "facts", "reason": "top10_heavy", "price": 1.0, "liq_usd": 50000, "symbol": "K"}
        self.assertTrue(shadow.note(MINT, v))
        self.assertFalse(shadow.note(MINT, v))                     # a retried kill is the same token
        self.assertIn(MINT, paths.ghosts())
        self.assertFalse(shadow.note("Other", {**v, "stage": "limits", "reason": "max_open"}))
        self.assertFalse(shadow.note("Thin", {**v, "stage": "pool", "reason": "thin_pool"}))
        self.assertEqual(shadow.results()["waiting"], 1)
        rows = shadow._rows()
        t0 = time.time() - 7 * 3600
        with open(shadow.FILE, "w", newline="") as f:              # the kill was 7 h ago, the token crashed
            import csv as _c
            w = _c.DictWriter(f, fieldnames=shadow.FIELDS); w.writeheader(); w.writerow({**rows[0], "t": t0})
        for k in range(1, 40):
            paths.append(MINT, {"t": t0 + k * 300, "price": max(0.05, 1 - k * 0.03), "liq": 50000})
        r = shadow.results()
        self.assertEqual(r["all"]["n"], 1)
        self.assertLess(r["all"]["mean"], 0)                       # GARDE was right
        self.assertEqual(r["reasons"][0]["reason"], "top10_heavy")
        os.remove(shadow.FILE)


class ShadowLowScore(Base):
    def test_a_pass_not_bought_for_its_score_is_followed(self):
        import shadow
        if os.path.exists(shadow.FILE):
            os.remove(shadow.FILE)
        v = {"verdict": "PASS", "stage": "judge", "reason": "passed", "price": 1.0, "liq_usd": 30000,
             "action": "not bought: score 40 < 55 (bot_volume)"}
        self.assertTrue(shadow.note(MINT, v))
        self.assertEqual(shadow._rows()[0]["reason"], "low_score")
        os.remove(shadow.FILE)


class Waiver(Base):
    """A soft kill whose shadow buys made money is lifted by the desk itself; a hard one never."""
    def test_lifted_only_when_clear_and_soft(self):
        import shadow
        res = {"reasons": [
            {"reason": "bundle_same_sol", "n": 25, "mean": 9.0, "half1": 6.0, "half2": 12.0, "low": 2.0},
            {"reason": "serial_dev", "n": 25, "mean": 9.0, "half1": 6.0, "half2": 12.0, "low": -4.0},   # noise
            {"reason": "copycat", "n": 25, "mean": 9.0, "half1": -3.0, "half2": 21.0},      # one half only
            {"reason": "low_score", "n": 12, "mean": 30.0, "half1": 20.0, "half2": 40.0},   # too few
            {"reason": "whale", "n": 40, "mean": 20.0, "half1": 20.0, "half2": 20.0},       # hard
            {"reason": "lp_unverified", "n": 30, "mean": -12.0, "half1": -10.0, "half2": -14.0}]}
        shadow._waived["t"] = 0
        with mock.patch.object(shadow, "results", return_value=res):
            self.assertEqual(shadow.waived(), {"bundle_same_sol"})
        shadow._waived.update(t=0, v=set())

    def test_fact_kill_passes_over_a_lifted_reason_and_applies_the_rest(self):
        t = {"mint_authority": None, "freeze_authority": None, "danger": [], "lp_burned_pct": None, "dev_pct": 0,
             "top10_pct": 45, "max_wallet_pct": 2, "same_sol_wallets": 1, "ladder_wallets": 1}
        self.assertEqual(facts.fact_kill(t), "lp_unverified")
        self.assertEqual(facts.fact_kill(t, skip={"lp_unverified"}), "top10_heavy")
        self.assertIsNone(facts.fact_kill(t, skip={"lp_unverified", "top10_heavy"}))


class TelegramOwner(Base):
    def test_pairing_with_the_dashboard_code_makes_alerts_and_leads_flow(self):
        import tgbot, agents
        for f in (tgbot.STATE, agents.INBOX):
            if os.path.exists(f):
                os.remove(f)
        sent = []
        with mock.patch.object(tgbot, "send", lambda tok, chat, msg: sent.append((chat, msg))), \
             mock.patch.object(tgbot.env, "get", lambda k: "T" if k == "TELEGRAM_BOT_TOKEN" else None), \
             mock.patch.object(tgbot, "inspect", return_value={"symbol": "X", "flags": [], "context": {}}):
            tgbot.handle("T", {"chat": {"id": 99}, "text": "/lier 000000x"})
            self.assertIsNone(tgbot.owner())
            tgbot.handle("T", {"chat": {"id": 42}, "text": "/lier " + tgbot.pair_code()})
            self.assertEqual(tgbot.owner(), "42")
            tgbot.handle("T", {"chat": {"id": 42}, "text": MINT})
            tgbot.handle("T", {"chat": {"id": 7}, "text": "Other111111111111111111111111111111111111"})
        with open(agents.INBOX) as f:
            self.assertEqual(f.read().split(), [MINT])           # only the owner's CA reaches the desk
        os.remove(agents.INBOX); os.remove(tgbot.STATE)


class TelegramLoopKeepsCode(Base):
    def test_polling_does_not_wipe_the_pairing_code(self):
        import tgbot
        if os.path.exists(tgbot.STATE):
            os.remove(tgbot.STATE)
        stop = threading.Event()
        calls = []
        code_box = {}

        def get(url, timeout=None, params=None):
            calls.append(1)
            if len(calls) == 1:
                code_box["code"] = tgbot.pair_code()             # the dashboard shows a code meanwhile
                return Resp({"result": [{"update_id": 5, "message": {}}]})
            stop.set()
            return Resp({"result": []})
        with mock.patch.object(tgbot, "token", return_value="T"), mock.patch("requests.get", get):
            tgbot.loop(stop)
        self.assertEqual(tgbot.pair_code(), code_box["code"])
        self.assertEqual(tgbot._state()["offset"], 6)
        os.remove(tgbot.STATE)


class ExploreTier(Base):
    """Paper: a full pass under MIN_SCORE is bought small in its own tier; under the floor it is not."""
    def test_low_score_pass_is_bought_small_as_explore(self):
        import shadow
        shadow._waived.update(t=time.time(), v=set())
        low = {"verdict": "PASS", "stage": "judge", "reason": "ok", "symbol": "LOW", "price": 0.001,
               "liq_usd": 80000, "score": 40, "flags": "bot_volume"}
        with mock.patch.object(check, "check", return_value=dict(low)):
            self.assertTrue(check.run("Mint3333333333333333333333333333333333333")["action"].startswith("not bought"))
        # off by default since Oct 19 (low scores at -85% median 6 h later); the floor turns it back on
        with mock.patch.dict(config.SIZING, {"explore_min_score": 30}), mock.patch.object(check, "check", return_value={"verdict": "PASS", "stage": "judge", "reason": "ok",
                               "symbol": "LOW", "price": 0.001, "liq_usd": 80000, "score": 40, "ticket": 40,
                               "tier": "base", "flags": "bot_volume"}):
            v = check.run(MINT)
        self.assertEqual(v["tier"], "explore")
        self.assertIn(MINT, book.load())
        self.assertLess(book.load()[MINT]["qty"] * 0.001, 40)          # smaller than a base ticket
        with mock.patch.object(check, "check", return_value={"verdict": "PASS", "stage": "judge", "reason": "ok",
                               "symbol": "BAD", "price": 0.001, "liq_usd": 80000, "score": 20, "flags": ""}):
            v = check.run("Mint2222222222222222222222222222222222222")
        self.assertTrue(v["action"].startswith("not bought"))


class ChiefOfStaff(Base):
    def test_etat_answers_the_owner_in_five_lines_and_nobody_else(self):
        import tgbot, report
        sent = []
        with mock.patch.object(tgbot, "send", lambda tok, chat, msg: sent.append((chat, msg))), \
             mock.patch.object(tgbot, "owner", return_value="42"), \
             mock.patch.object(tgbot.env, "get", lambda k: None):
            tgbot.handle("T", {"chat": {"id": 42}, "text": "/etat"})
            tgbot.handle("T", {"chat": {"id": 7}, "text": "/etat"})
        self.assertLessEqual(len(sent[0][1].splitlines()), 6)
        self.assertIn("SCOUT", sent[0][1])
        self.assertNotIn("SCOUT", sent[1][1])                     # a stranger gets the help text


EVM = "0x020bfC650A365f8BB26819deAAbF3E21291018b4"
EVM_PAIR = "0xa70fc67c9f69da90b63a0e4c05d229954574e313"


def evm_pair(chain="robinhood", liq=80000, age_min=120, vol=20000, buys=50, sells=30):
    return [{"chainId": chain, "dexId": "uniswap", "pairAddress": EVM_PAIR, "url": f"https://dexscreener.com/{chain}/x",
             "baseToken": {"address": EVM, "symbol": "CAT"}, "priceUsd": "0.002", "priceNative": "0.0000006",
             "liquidity": {"usd": liq}, "pairCreatedAt": (time.time() - age_min * 60) * 1000, "marketCap": liq * 4,
             "txns": {"h1": {"buys": buys, "sells": sells}}, "volume": {"h1": vol}}]


def evm_goplus(**over):
    g = {"is_honeypot": "0", "buy_tax": "0", "sell_tax": "0", "cannot_sell_all": "0", "is_mintable": "0",
         "transfer_pausable": "0", "is_blacklisted": "0", "owner_change_balance": "0", "hidden_owner": "0",
         "is_open_source": "1", "creator_address": "0xCREATOR", "creator_percent": "0.01", "holder_count": "1500",
         "token_symbol": "CAT",
         "dex": [{"pair": EVM_PAIR}],
         "holders": [{"address": EVM_PAIR, "is_contract": 1, "is_locked": 0, "percent": "0.55"}] +
                    [{"address": f"0xW{i}", "is_contract": 0, "is_locked": 0, "percent": str(0.02 * (1 - 0.1 * i))}
                     for i in range(9)],
         "lp_holders": [{"address": "0x000000000000000000000000000000000000dead", "percent": "0.97", "is_locked": 0}]}
    g.update(over)
    return g


def evm_net(ds=None, gp=None):
    def get(url, timeout=None, params=None, headers=None):
        if "gopluslabs" in url:
            return Resp({"code": 1, "message": "OK", "result": {EVM.lower(): gp or evm_goplus()}})
        if "dexscreener.com/tokens/v1/" in url or "latest/dex/tokens/" in url:
            return Resp(ds if ds is not None else evm_pair()) if "tokens/v1/" in url else Resp({"pairs": ds if ds is not None else evm_pair()})
        if "search" in url:
            return Resp({"pairs": []})
        return Resp({})
    return mock.patch("requests.get", get)


class MultiChain(Base):
    """Robinhood Chain, BNB Chain, Base, Ethereum...: one desk, the EVM checks from GoPlus."""
    KEY = "robinhood:" + EVM.lower()

    def test_keys_and_prices_per_chain(self):
        import chains, market
        self.assertEqual(chains.key("robinhood", EVM), self.KEY)
        self.assertEqual(chains.split(self.KEY), ("robinhood", EVM.lower()))
        self.assertEqual(chains.split(MINT), ("solana", MINT))
        with evm_net():
            m = market.pool(self.KEY)
        self.assertEqual((m["chain"], m["symbol"]), ("robinhood", "CAT"))

    def test_a_clean_robinhood_token_passes_and_is_bought_with_its_chain_costs(self):
        with evm_net(), mock.patch("requests.post", Chain()):
            v = check.run(self.KEY)
        self.assertIn(v["verdict"], ("PASS", "BUY"), v)
        self.assertIn(self.KEY, book.load())
        self.assertIn(EVM.lower(), v["x_ca"])

    def test_honeypot_and_tax_are_killed_hard(self):
        with evm_net(gp=evm_goplus(is_honeypot="1")), mock.patch("requests.post", Chain()):
            self.assertEqual(check.check(self.KEY)["reason"], "danger:honeypot")
        with evm_net(gp=evm_goplus(sell_tax="0.25")), mock.patch("requests.post", Chain()):
            self.assertEqual(check.check(self.KEY)["reason"], "danger:high_tax")
        with evm_net(gp=evm_goplus(is_mintable="1")), mock.patch("requests.post", Chain()):
            self.assertEqual(check.check(self.KEY)["reason"], "mint_open")

    def test_v3_lp_held_by_a_wallet_is_unlocked_by_a_contract_is_fine(self):
        import facts_evm
        nft = [{"NFT_id": "1"}]
        wallet_lp = [{"address": "0xDEV", "is_contract": 0, "is_locked": 0, "percent": "0.8", "NFT_list": nft},
                     {"address": "0xLOCKER", "is_contract": 1, "is_locked": 0, "percent": "0.2", "NFT_list": nft}]
        with evm_net(gp=evm_goplus(lp_holders=wallet_lp)):
            self.assertEqual(facts_evm.report(self.KEY, {"pair": EVM_PAIR})["lp_burned_pct"], 20.0)
        locker_lp = [{**wallet_lp[1], "percent": "1.0"}]
        with evm_net(gp=evm_goplus(lp_holders=locker_lp)):
            t = facts_evm.report(self.KEY, {"pair": EVM_PAIR})
        self.assertEqual(t["lp_burned_pct"], 100.0)
        self.assertAlmostEqual(t["max_wallet_pct"], 2.0)            # the pool's 55% is not a whale

    def test_ethereum_gas_eats_a_small_ticket(self):
        import market
        k = "ethereum:" + EVM.lower()
        with evm_net(ds=evm_pair(chain="ethereum")):
            self.assertEqual(market.market_kill(market.pool(k)), "fees_eat_ticket")

    def test_a_bare_0x_address_is_found_on_its_chain(self):
        import market
        with evm_net():
            self.assertEqual(market.locate(EVM), self.KEY)


class RulesRegime(Base):
    def test_the_decision_counts_only_trades_under_the_current_rules(self):
        import edge
        with open(config.TRADES, "w") as f:
            f.write("time,mint,symbol,action,usd,pnl,reason\n")
            f.write("2026-10-19 10:00,OLD,O,open,40,0,entry\n2026-10-19 11:00,OLD,O,close,0,-20,stop\n")
            f.write("2026-10-20 10:00,base:0xnew,N,open,40,0,entry\n2026-10-20 11:00,base:0xnew,N,close,0,8,trail\n")
        self.assertEqual([t["mint"] for t in edge.closed()], ["base:0xnew"])
        self.assertEqual(len(edge.closed(None)), 2)
        import chains
        self.assertEqual(edge.split(lambda t: chains.split(t["mint"])[0])[0], {"group": "base", "n": 1, "mean_pct": 20.0, "total": 8.0})
        os.remove(config.TRADES)

    def test_backtest_main_block_comes_after_every_function_it_calls(self):
        src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backtest.py")).read()
        self.assertGreater(src.index('if __name__ == "__main__":'), src.index("def variants("))

    def test_goplus_holders_without_addresses_are_dropped(self):
        with net(gp=goplus(holders=[{"account": "", "percent": "0.2", "is_locked": 0, "tag": ""}] * 10)):
            t = facts.report(MINT, {"dex": "pumpswap", "pair": PAIR})
        self.assertNotEqual(t.get("holders_source"), "goplus")          # read from the chain instead


class DecisionReport(Base):
    def test_sent_once_on_review_day_and_a_preview_does_not_block_it(self):
        import agents, edge, report, glob
        for f in glob.glob(os.path.join(config.DATA, "rapport_decision_*.txt")):
            os.remove(f)
        sent = []
        report.weekly(save=False)                                       # /rapport before the day
        with mock.patch.object(agents, "post", lambda t: sent.append(t)), \
             mock.patch.object(edge, "BILAN_ON", time.strftime("%Y-%m-%d")):
            agents.plume()
            agents.plume()
        self.assertEqual(sum("RAPPORT DE DÉCISION" in t for t in sent), 1)
        self.assertTrue(any("DÉCISION : NON" in t for t in sent))      # no trades: the rule says no
        for f in glob.glob(os.path.join(config.DATA, "rapport_decision_*.txt")):
            os.remove(f)


class Learning(Base):
    """learn.py: every judged token is a lesson; the model decides only if it beats chance on unseen data."""
    def synthetic(self, n, signal=True, seed=1):
        import random
        rng = random.Random(seed)
        data = []
        for i in range(n):
            bot = rng.random() < 0.5
            sol = rng.uniform(-5, 5)
            row = {"score": rng.randint(30, 90), "liq_usd": rng.uniform(15e3, 2e5), "age_min": rng.uniform(60, 3000),
                   "flags": "bot_volume" if bot else "", "sol_1h": sol, "chain": "solana", "lane": "early"}
            y = rng.gauss(0, 30) + ((-40 if bot else 10) + 4 * sol if signal else 0)
            data.append({"x": __import__("learn").features(row), "y": max(-100, min(200, y)), "t": i})
        return data

    def run_train(self, data):
        import learn
        with mock.patch.object(learn, "dataset", return_value=data):
            return learn.train()

    def test_a_real_signal_is_learned_and_trusted(self):
        import learn
        res = self.run_train(self.synthetic(300))
        self.assertTrue(res["trusted"], res)
        lessons = {l["feature"]: l["effect"] for l in res["lessons"]}
        self.assertLess(lessons["flag:bot_volume"], -20)                  # it found the planted -50 gap
        learn._cache["t"] = 0
        good = {"flags": "", "sol_1h": 4, "chain": "solana", "lane": "early", "score": 60}
        bad = {"flags": "bot_volume", "sol_1h": -4, "chain": "solana", "lane": "early", "score": 60}
        self.assertGreater(learn.expected(good), learn.expected(bad))
        os.remove(learn.MODEL); learn._cache["t"] = 0

    def test_noise_is_not_trusted(self):
        import learn
        # luck must not pass for skill: 15 draws of pure noise, none trusted
        self.assertEqual(sum(bool(self.run_train(self.synthetic(300, signal=False, seed=s))["trusted"])
                             for s in range(15)), 0)
        res = self.run_train(self.synthetic(300, signal=False))
        self.assertFalse(res["trusted"], res)
        learn._cache["t"] = 0
        self.assertIsNone(learn.expected({"flags": ""}))                  # untrusted: the rules decide
        os.remove(learn.MODEL); learn._cache["t"] = 0

    def test_too_few_lessons_is_not_trusted(self):
        res = self.run_train(self.synthetic(50))
        self.assertFalse(res["trusted"])
        self.assertIn("il en faut", res["why"])
        os.remove(__import__("learn").MODEL); __import__("learn")._cache["t"] = 0

    def test_the_model_overrides_soft_kills_only(self):
        import learn
        with mock.patch.object(learn, "expected", return_value=12.0):
            self.assertTrue(check._model_override("bundle_same_sol", {}))
            self.assertFalse(check._model_override("mint_open", {}))       # hard: never
            self.assertFalse(check._model_override("danger:honeypot", {}))
            self.assertFalse(check._model_override("whale", {}))
        with mock.patch.object(learn, "expected", return_value=2.0):
            self.assertFalse(check._model_override("bundle_same_sol", {}))  # not enough expected


class Coach(Base):
    """Agents improve themselves only through guarded, logged, reversible changes."""
    def setUp(self):
        super().setUp()
        self.clean()
        self.addCleanup(self.clean)

    def clean(self):
        import coach, shadow, pending
        for f in (coach.JOURNAL, coach.TUNING, coach.REVIEWS, shadow.FILE, pending.X_READS):
            if os.path.exists(f):
                os.remove(f)

    def test_the_guards(self):
        import coach, random
        rng = random.Random(4)
        self.assertFalse(coach.paired([200.0])["ok"])                                    # one spectacular case
        self.assertFalse(coach.paired([rng.gauss(0, 30) for _ in range(200)], k=10)["ok"])   # noise
        self.assertFalse(coach.paired([-5.0] * 30 + [25.0] * 30)["ok"])                  # one half only
        self.assertTrue(coach.paired([rng.gauss(8, 10) for _ in range(80)], k=10)["ok"])  # a real, repeated gain
        # the bar rises with the number of variants tried
        self.assertGreater(coach.z_for(10), coach.z_for(1))

    def test_one_change_a_day_then_undone_if_it_disappoints(self):
        import coach
        ok = {"ok": True, "why": "test", "n": 80, "mean": 5}
        e = coach.apply("VIGIE", "exit_profile", "no ladder", ok, 900.0)
        self.assertEqual(coach.get("exit_profile"), "no ladder")
        self.assertIsNone(coach.apply("VIGIE", "exit_profile", "chandelier k2", ok, 900.0))   # 24 h rule
        self.assertIsNone(coach.apply("SCOUT", "source_rank", ["a"], {"ok": False}, 900.0))    # no evidence
        with mock.patch.object(coach, "EVAL_S", 0):
            out = coach.evaluate({"exit_profile": lambda entry: {"n": 40, "mean": -3.0}})
        self.assertEqual(out[0]["status"], "rolled_back")
        self.assertIsNone(coach.get("exit_profile"))                                   # back to the old value
        self.assertEqual(coach.journal()[-1]["status"], "rolled_back")

    def test_circuit_breaker(self):
        import coach
        coach.apply("ECHO", "echo_skip_sells", True, {"ok": True, "why": "t"}, 900.0)
        self.assertEqual(coach.circuit(880.0), [])                                     # -20: within limits
        self.assertEqual(len(coach.circuit(790.0)), 1)                                 # -110: tripped
        self.assertIsNone(coach.get("echo_skip_sells"))

    def shadows(self, n, price_fn, reason="pass"):
        """n shadowed tokens 7 h old, each with a 6 h price path from price_fn(token, step)."""
        import shadow, paths
        t0 = time.time() - 7 * 3600
        with open(shadow.FILE, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=shadow.FIELDS)
            w.writeheader()
            for i in range(n):
                mint = f"Sh{i:03d}" + "1" * 36
                if os.path.exists(paths._file(mint)):      # another test's path for the same name: start clean
                    os.remove(paths._file(mint))
                w.writerow({"t": t0 + i, "mint": mint, "symbol": f"S{i}", "stage": "pass", "reason": reason,
                            "price": 1.0, "liq": 80000})
                for k in range(1, 72):
                    paths.append(mint, {"t": t0 + i + k * 300, "price": price_fn(i, k), "liq": 80000})

    def test_vigie_learns_from_shadows_and_ignores_a_lone_case(self):
        import reviews, coach, exits, csv as _c
        # one token pumps +60% then crashes: only that one would reward selling early. not enough
        self.shadows(41, lambda i, k: (1 + 0.6 * k / 30 if k <= 30 else 0.5) if i == 0 else 1.0 + 0.001 * k)
        reviews.vigie(900.0)
        self.assertIsNone(coach.get("exit_profile"))
        # the same shape on 60 tokens: a repeated pattern, the profile that sells into strength wins
        self.shadows(60, lambda i, k: 1 + 0.6 * k / 30 if k <= 30 else 0.5)
        out = reviews.vigie(900.0)
        self.assertIsNotNone(coach.get("exit_profile"), out)
        self.assertNotEqual(exits.active(), dict(config.EXIT))
        import shadow
        os.remove(shadow.FILE)

    def test_echo_skips_sell_again_only_if_they_foresee_drops(self):
        import reviews, coach, pending, shadow
        self.shadows(90, lambda i, k: (1 - 0.6 * k / 71) if i % 2 == 0 else (1 + 0.2 * k / 71))
        with open(pending.X_READS, "w") as f:
            f.write("time,mint,symbol,verdict,raison\n")
            for i in range(0, 90, 2):                        # ECHO said SKIP to exactly the ones that fell
                f.write(f"2026-10-20 00:00,Sh{i:03d}{'1' * 36},S{i},SKIP,t\n")
        reviews.echo(900.0)
        self.assertTrue(coach.get("echo_skip_sells"))
        self.assertEqual(pending.sell_on(), ("SCAM", "SKIP"))
        os.remove(pending.X_READS); os.remove(shadow.FILE)


class Trend(Base):
    """TENDANCE: the 200-day rule on the majors, its backtest, its paper book, the regime dial."""
    def setUp(self):
        super().setUp()
        self.clean()
        self.addCleanup(self.clean)

    def clean(self):
        import majors, coach
        for f in (majors.PRICES, majors.STATE, majors.BT, majors.FILLS, majors.EQUITY, coach.JOURNAL, coach.TUNING):
            if os.path.exists(f):
                os.remove(f)
        majors._dial["t"] = 0

    @staticmethod
    def bars(closes, crypto=True, end=None):
        """Daily bars ending yesterday (all complete): crypto every day, ETFs on weekdays at the 09:30 open."""
        end = end or (int(time.time()) // 86400) * 86400 - 86400
        if crypto:
            return [[end - (len(closes) - 1 - i) * 86400, c] for i, c in enumerate(closes)]
        out, d = [], end
        for c in reversed(closes):
            while time.gmtime(d).tm_wday >= 5:
                d -= 86400
            out.append([d + 13.5 * 3600, c]); d -= 86400
        return out[::-1]

    def fake(self, closes: dict):
        import majors
        return mock.patch.object(majors, "_fetch", lambda n, have: (self.bars(closes[n], majors.ASSETS[n]["kind"] == "crypto"), "test")
                                 if n in closes else (_ for _ in ()).throw(RuntimeError("source down")))

    def test_the_bands_keep_it_from_trading_every_cross(self):
        import majors
        flat = [100.0] * 200
        s = majors.signals(flat + [100.5, 101.5, 99.0, 98.0, 96.0, 100.5, 101.6])
        self.assertEqual(s[199], False)                     # first verdict: not above its average
        self.assertEqual(s[200:], [False, True, True, True, False, False, True])
        self.assertIsNone(majors.signals([1.0] * 10)[-1])    # no average yet: no opinion

    def test_backtest_cuts_the_drawdown_and_pays_costs(self):
        import majors
        up = [100 * 1.004 ** i for i in range(400)]
        down = [up[-1] * 0.995 ** i for i in range(1, 300)]
        again = [down[-1] * 1.004 ** i for i in range(1, 400)]
        data = {"BTC": {"bars": self.bars(up + down + again)}}
        r = majors.backtest_one(data, ["BTC"])
        self.assertLess(r["trend"]["mdd"], r["hold"]["mdd"])
        self.assertGreater(r["costs"], 0)
        self.assertIn(r["verdict"], ("DATA VALIDATED", "TRADE-OFF", "NO EDGE"))
        # a coin flip market: the rule must not be called validated
        import random
        rng = random.Random(7)
        p, noise = 100.0, []
        for _ in range(1100):
            p *= 1 + rng.gauss(0, 0.03); noise.append(p)
        r = majors.backtest_one({"BTC": {"bars": self.bars(noise)}}, ["BTC"])
        self.assertNotEqual(r["verdict"], "DATA VALIDATED", r)

    def test_a_late_asset_joins_the_book_instead_of_cutting_the_history(self):
        import majors
        btc = [100 * 1.001 ** i for i in range(1200)]
        sol = [10 * 1.001 ** i for i in range(400)]
        data = {"BTC": {"bars": self.bars(btc)}, "SOL": {"bars": self.bars(sol)}}
        r = majors.backtest_one(data, ["BTC", "SOL"])
        self.assertEqual(r["days"], 1001)                     # from BTC's 200th close, not SOL's
        series, days = majors._series(data, ["BTC", "SOL"])
        held = majors.simulate(series, days, 0, len(days), "hold")
        self.assertGreaterEqual(held["trades"], 3)            # BTC, then SOL joins (and BTC is trimmed)

    def test_the_whole_crypto_history_is_read_once(self):
        import majors
        calls = []
        def fetch(n, deep):
            calls.append((n, deep))
            return self.bars([100.0] * 250, majors.ASSETS[n]["kind"] == "crypto"), "coinbase" if n in ("BTC", "ETH", "SOL") else "yahoo"
        with mock.patch.object(majors, "_fetch", fetch), mock.patch.object(majors, "REFRESH_S", 0):
            majors.refresh(); majors.refresh()
        self.assertEqual([d for n, d in calls if n == "BTC"], [True, False])
        self.assertEqual([d for n, d in calls if n == "QQQ"], [False, False])

    def test_tick_trades_only_when_the_set_changes(self):
        import majors
        rising = [100 * 1.002 ** i for i in range(260)]
        falling = [100 * 0.998 ** i for i in range(260)]
        closes = {"BTC": rising, "ETH": falling, "SOL": rising, "QQQ": rising, "SPY": falling}
        with self.fake(closes), mock.patch.object(majors, "REFRESH_S", 0):
            line, did = majors.tick()
            self.assertEqual(sorted(majors.book()["qty"]), ["BTC", "QQQ", "SOL"])
            self.assertEqual(len(did), 3)
            eq = majors.equity()
            self.assertLess(eq, 1000)                                     # costs were paid
            self.assertGreater(eq, 1000 * (1 - 0.004))
            self.assertEqual(majors.tick()[1], [])                        # nothing changed: no order
            closes["BTC"] = rising + [rising[-1] * 0.7] * 2               # BTC breaks down
            line, did = majors.tick()
        self.assertEqual(sorted(majors.book()["qty"]), ["QQQ", "SOL"])
        self.assertTrue(any(d.startswith("vend BTC") for d in did), did)
        self.assertEqual({f["asset"] for f in majors.fills() if f["side"] == "vente"}, {"BTC"})
        self.assertTrue(os.path.exists(majors.BT))                         # the backtest ran on the way

    def test_a_source_down_never_sells_blind(self):
        import majors
        rising = [100 * 1.002 ** i for i in range(260)]
        with self.fake({"BTC": rising}), mock.patch.object(majors, "REFRESH_S", 0):
            majors.tick()
        self.assertEqual(list(majors.book()["qty"]), ["BTC"])
        data = majors.prices()
        data["BTC"]["bars"] = data["BTC"]["bars"][:50]                     # history lost, source down
        majors._write(majors.PRICES, data)
        with self.fake({}), mock.patch.object(majors, "REFRESH_S", 0):
            line, did = majors.tick()
        self.assertEqual(did, [])
        self.assertIn("BTC", majors.book()["qty"])
        self.assertIn("source en panne", line)

    def test_the_dial_and_what_garde_logs(self):
        import majors
        up, down = [100 * 1.002 ** i for i in range(260)], [100 * 0.998 ** i for i in range(260)]
        data = {"BTC": {"bars": self.bars(up)}, "ETH": {"bars": self.bars(down)}, "SOL": {"bars": self.bars(up)},
                "checked": time.time()}
        d = majors.dial(data)
        self.assertEqual(d["value"], 0.67)
        self.assertEqual(d["parts"], {"BTC>200j": True, "ETH>200j": False, "SOL>50j": True})
        majors._write(majors.PRICES, data)
        self.assertEqual(majors.dial_value(), 0.67)
        import learn
        self.assertEqual(learn.features({"dial": "0.67"})["dial"], 0.67)

    def test_memecoins_stand_down_only_when_the_coach_says_so(self):
        import coach, majors, shadow
        self.addCleanup(setattr, check, "ECHO_MODE", check.ECHO_MODE)
        check.ECHO_MODE = "observe"
        with mock.patch.object(majors, "dial_value", lambda: 0.0), net():
            v = check.run(MINT)
        self.assertIn("PAPER BUY", v["action"])                              # no gate without evidence
        self.assertEqual(v["dial"], 0.0)
        Base.setUp(self)                                                     # empty book again
        coach._write(coach.TUNING, {"meme_dial_gate": 0.5})
        with mock.patch.object(majors, "dial_value", lambda: 0.0), net():
            v = check.run(MINT)
        self.assertIn("regime dial", v["action"])
        self.assertNotIn(MINT, book.load())
        # still followed as a pass: the gate's own re-test needs these tokens
        with mock.patch.object(shadow, "paths"), mock.patch.object(shadow, "FILE", os.path.join(config.DATA, "sh_t.csv")):
            self.assertTrue(shadow.note(MINT, v))
            self.assertEqual(shadow._rows()[0]["reason"], "pass")
            os.remove(shadow.FILE)

    def test_trend_review_needs_evidence(self):
        import reviews, coach
        out = reviews.trend(1000.0)
        self.assertIsNone(coach.get("meme_dial_gate"))
        self.assertIn("quel que soit le cadran", out["change"])
        self.assertEqual(reviews._whipsaws([{"asset": "BTC", "side": "achat", "price": "100"},
                                            {"asset": "BTC", "side": "vente", "price": "95"}]), ["BTC -5.0 %"])

    def test_volume_fade_is_a_lab_profile_only(self):
        import exits, exitlab
        t0 = 1_000_000.0
        pos = {"entry": 1.0, "peak": 1.1, "peak_t": t0, "opened": t0, "liq0": 1000, "steps": 0, "qty": 1, "qty0": 1}
        s = {"t": t0 + 3600, "price": 1.05, "liq": 1000, "b5": 5, "s5": 5, "v5": 10, "v5_avg": 100, "vol": 5}
        p = {**config.EXIT, **exitlab.PROFILES["volume fade 25%"]}
        self.assertEqual(exits.decide(pos, s, p), (1.0, "volume_fade"))
        self.assertIsNone(exits.decide(pos, {**s, "v5": None}, p))          # volume unknown is not a fade
        self.assertIsNone(exits.decide(pos, s, dict(config.EXIT)))          # off in the live profile

    def test_status_and_dashboard_show_it(self):
        import majors, dashboard
        rising = [100 * 1.002 ** i for i in range(260)]
        with self.fake({"BTC": rising}), mock.patch.object(majors, "REFRESH_S", 0):
            majors.tick()
        self.assertIn("TENDANCE", report.status())
        st = dashboard.trend_state()
        self.assertEqual([a["asset"] for a in st["assets"] if a["usd"]], ["BTC"])
        self.assertIn("TREND", [a[0] for a in dashboard.AGENTS])


class Sources20(Base):
    """GeckoTerminal's shared budget, RugCheck's second opinion, the chart's three books."""
    def test_geckoterminal_budget_keeps_room_for_scout(self):
        import gt
        if os.path.exists(gt.FILE):
            os.remove(gt.FILE)
        self.addCleanup(lambda: os.path.exists(gt.FILE) and os.remove(gt.FILE))
        with mock.patch.object(gt, "BUDGET", 3), mock.patch.object(gt, "BACKGROUND", 1):
            self.assertTrue(gt._slot(True, 0))             # the backtest takes its share...
            self.assertFalse(gt._slot(True, 0))            # ...and no more
            self.assertTrue(gt._slot(False, 0))            # SCOUT still has room
            self.assertTrue(gt._slot(False, 0))
            self.assertFalse(gt._slot(False, 0))           # the wall, for everyone
        os.remove(gt.FILE)
        gt.cool(60)                                        # a 429: nobody calls for a minute
        self.assertFalse(gt._slot(False, 0))
        self.assertTrue(gt.state()["cooling"])

    def test_rugcheck_is_read_never_a_kill(self):
        import rugcheck
        ok = Resp({"score_normalised": 72, "lpLockedPct": 0,
                   "risks": [{"name": "Mutable metadata", "level": "warn"}, {"name": "Top holder", "level": "danger"}]})
        with mock.patch("requests.get", lambda *a, **k: ok):
            self.assertEqual(rugcheck.fetch(MINT), {"rc_score": 72, "rc_danger": 1, "rc_lp_locked": 0})
        with mock.patch("requests.get", lambda *a, **k: Resp({}, 401)):
            self.assertIsNone(rugcheck.fetch(MINT))
        with mock.patch.object(rugcheck, "fetch", lambda m: {"rc_score": 99, "rc_danger": 5, "rc_lp_locked": 0}):
            v = self.verdict()
        self.assertEqual(v["verdict"], "PASS", v)          # logged, not a kill
        self.assertEqual(v["rc_score"], 99)
        import learn
        self.assertEqual(learn.features(v)["rc_danger"], 5)

    def test_chart_books_add_up(self):
        import dashboard, majors
        for f in (config.EQUITY, majors.EQUITY):
            if os.path.exists(f):
                os.remove(f)
        self.addCleanup(lambda: [os.remove(f) for f in (config.EQUITY, majors.EQUITY) if os.path.exists(f)])
        now = time.time()
        with open(config.EQUITY, "w") as f:
            f.write("t,balance,realized,unrealized,open\n" + f"{now - 100},900,0,0,0\n{now - 10},880,0,0,0\n")
        with open(majors.EQUITY, "w") as f:
            f.write("t,equity,cash,dial\n" + f"{now - 50},1010,0,0.67\n")
        tot = dashboard.book_curve("total", None, now)
        self.assertEqual([v for _, v in tot], [900 + 1000, 900 + 1010, 880 + 1010])
        self.assertEqual(dashboard.book_curve("tendance", 900, now), [[now - 50, 1010.0]])
        self.assertEqual(dashboard.state("live", "total")["range_s"], 900)


class ModelRescues(Base):
    """Option B (Oct 20): the trusted model may buy what a pool-stage soft rule refused, never a hard kill."""
    def run_with(self, trusted, exp, kill="copycat"):
        import market, learn
        with mock.patch.object(market, "copycat", lambda m, mint: kill), \
                mock.patch.object(learn, "load", lambda: {"trusted": trusted}), \
                mock.patch.object(learn, "expected", lambda row: exp if trusted else None):
            return self.verdict()

    def test_untrusted_model_changes_nothing(self):
        v = self.run_with(False, None)
        self.assertEqual((v["verdict"], v["stage"], v["reason"]), ("SKIP", "pool", "copycat"))

    def test_trusted_model_rescues_only_when_it_expects_a_profit(self):
        v = self.run_with(True, 12.0)
        self.assertEqual(v["verdict"], "PASS", v)
        self.assertEqual(v["override"], "copycat")
        v = self.run_with(True, 1.0)
        self.assertEqual((v["verdict"], v["reason"]), ("SKIP", "copycat"))
        self.assertEqual(v["expected"], 1.0)

    def test_a_rug_factory_is_never_held(self):
        v = self.run_with(True, 50.0, kill="serial_farm")
        self.assertEqual((v["verdict"], v["reason"]), ("SKIP", "serial_farm"))


class PageScript(unittest.TestCase):
    def test_the_page_script_parses(self):
        """A script that does not parse leaves the whole page on '…' (Oct 20: a name declared twice)."""
        import re, shutil, subprocess
        node = shutil.which("node")
        if not node:
            self.skipTest("node absent")
        with open(os.path.join(config.HERE, "dashboard.html")) as f:
            js = "\n".join(re.findall(r"<script>(.*?)</script>", f.read(), re.S))
        path = os.path.join(config.DATA, "page.js")
        with open(path, "w") as f:
            f.write(js)
        r = subprocess.run([node, "--check", path], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])


class EchoWatch(Base):
    """ECHO re-reads every open position on X every 15 min, and the desk says when ECHO's loop is down."""
    def setUp(self):
        super().setUp()
        import pending
        for f in (pending.X_READS, pending.X_WATCH):
            if os.path.exists(f):
                os.remove(f)
        self.addCleanup(lambda: [os.remove(f) for f in (pending.X_READS, pending.X_WATCH) if os.path.exists(f)])

    def test_watch_lists_open_positions_and_what_is_due(self):
        import pending
        book.open_position(MINT, "TEST", 1.0, 20000, usd=25)
        pending.write_watch(pending.reads())
        with open(pending.X_WATCH, newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual((rows[0]["mint"], rows[0]["due"]), (MINT, "oui"))            # never read: due
        with open(pending.X_READS, "w") as f:
            f.write("time,mint,symbol,verdict,raison\n" + time.strftime("%Y-%m-%d %H:%M") + f",{MINT},TEST,BUY,rien de neuf\n")
        pending.write_watch(pending.reads())
        with open(pending.X_WATCH, newline="") as f:
            self.assertEqual(next(csv.DictReader(f))["due"], "non")                    # just read: not due
        self.assertLess(pending.echo_gap_min(), 2)

    def test_alarm_when_echo_is_silent_with_positions_open(self):
        import agents
        book.open_position(MINT, "TEST", 1.0, 20000, usd=25)
        agents._echo_alarm["t"] = 0
        said = []
        with mock.patch.object(agents, "emit", lambda *a, **k: said.append(a)), \
                mock.patch.object(agents, "post", lambda t: said.append(t)), \
                mock.patch.object(agents.pending, "decide", lambda: []):
            agents.gate()
            agents.gate()                                                             # once an hour, not every 30 s
        self.assertEqual(len(said), 2)
        self.assertIn("ECHO ne lit plus X", said[0][2])


class BalanceRestart(Base):
    """Oct 20: the balance starts again at the bankroll, positions and history kept."""
    def test_reset_keeps_positions_and_history(self):
        import dashboard
        self.addCleanup(lambda: os.path.exists(book.RESET) and os.remove(book.RESET))
        book.open_position(MINT, "OLD", 1.0, 20000, usd=25)
        book.sell(MINT, 1.0, 0.5, "stop")                       # an old loss
        book.open_position("Mint222222222222222222222222222222222222222", "OPEN", 1.0, 20000, usd=25)
        with open(config.EQUITY, "w") as f:
            f.write("t,balance,realized,unrealized,open\n1,990,0,0,0\n")
        self.assertLess(book.realized(), -10)
        info = book.reset()
        self.assertEqual(book.realized(), 0.0)
        self.assertIn("Mint222222222222222222222222222222222222222", book.load())   # still open
        self.assertEqual(len(book.trades()), 3)                                     # nothing deleted
        self.assertFalse(os.path.exists(config.EQUITY))                             # the curve starts fresh
        self.assertLess(info["realized_before"], -10)
        self.assertEqual(dashboard.state()["wins"] + dashboard.state()["losses"], 0)
        book.sell("Mint222222222222222222222222222222222222222", 1.0, 1.2, "take")  # a new trade counts
        self.assertGreater(book.realized(), 0)
        self.assertEqual(dashboard.state()["wins"], 1)


class Incidents(Base):
    """Oct 20: a fall of the balance is graded against the noise; only a real incident changes anything."""
    def setUp(self):
        super().setUp()
        import incidents
        self.clean()
        self.addCleanup(self.clean)

    def clean(self):
        import incidents
        for f in (incidents.LOG, incidents.STATE, incidents.URGENT, config.EQUITY, book.RESET):
            if os.path.exists(f):
                os.remove(f)

    def equity(self, values, step=20, end=None):
        end = end or time.time()
        with open(config.EQUITY, "w") as f:
            f.write("t,balance,realized,unrealized,open\n")
            for i, v in enumerate(values):
                f.write(f"{end - (len(values) - 1 - i) * step},{v},0,0,0\n")

    def wiggle(self, n=4000, amp=1.5):
        import random
        rng = random.Random(3)
        return [1000 + amp * rng.uniform(-1, 1) for _ in range(n)]

    def test_noise_is_not_an_incident(self):
        import incidents
        self.equity(self.wiggle())
        incidents.tick()                                   # first run: sets its marks
        self.assertEqual(incidents.tick(), [])
        self.assertEqual(incidents.paused(), 0)

    def test_a_small_drop_is_explained_and_changes_nothing(self):
        import incidents
        self.equity(self.wiggle() + [1004, 1003, 1001, 999, 998])    # -$6 in under 10 min, like Oct 20
        incidents.tick(); os.remove(incidents.LOG) if os.path.exists(incidents.LOG) else None
        st = incidents._read(incidents.STATE, {}); st.pop("last_note", None); incidents._write(incidents.STATE, st)
        out = incidents.tick()
        self.assertEqual([r["level"] for r in out], ["note"])
        self.assertIn("ANALYSE", out[0]["text"])
        self.assertEqual(incidents.paused(), 0)                 # no pause, no change
        self.assertIsNone(book.guard(MINT))

    def test_a_big_fall_is_an_incident_with_a_pause(self):
        import incidents
        incidents.tick()
        self.equity(self.wiggle() + [1000 - 2 * i for i in range(1, 40)])   # -$78 in 13 min
        out = incidents.tick()
        self.assertEqual(out[0]["level"], "incident")
        self.assertGreater(incidents.paused(), 25 * 60)
        self.assertEqual(book.guard(MINT), "incident_pause")
        self.assertIn("jamais de mise plus grosse", out[0]["text"])

    def test_a_rug_exit_is_an_incident_and_echo_rereads(self):
        import incidents, pending
        self.equity(self.wiggle())
        incidents.tick()
        book.open_position(MINT, "RUG", 1.0, 20000, usd=25)
        book.open_position("Mint333333333333333333333333333333333333333", "OTHER", 1.0, 20000, usd=25)
        book.sell(MINT, 1.0, 0.02, "liquidity_pulled")
        out = incidents.tick()
        self.assertEqual((out[0]["level"], out[0]["cause"]), ("incident", "rug"))
        self.assertIn(MINT, out[0]["lessons"])
        self.assertIn("Mint333333333333333333333333333333333333333", incidents.urgent()["mints"])
        with open(pending.X_READS, "w") as f:                  # read 5 min BEFORE the incident: due again
            f.write("time,mint,symbol,verdict,raison\n" + time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - 300))
                    + ",Mint333333333333333333333333333333333333333,OTHER,BUY,ok\n")
        self.addCleanup(lambda: os.path.exists(pending.X_READS) and os.remove(pending.X_READS))
        pending.write_watch(pending.reads())
        with open(pending.X_WATCH, newline="") as f:
            self.assertEqual(next(csv.DictReader(f))["due"], "oui")

    def test_drawdown_cuts_tickets_never_raises_them(self):
        import incidents
        self.equity([1000, 1050, 1040])
        self.assertEqual(incidents.prudence()["factor"], 1.0)    # 1 % under the peak: nothing
        self.equity([1000, 1050, 940])                           # 11 % under the peak
        self.assertEqual(incidents.prudence()["factor"], 0.8)
        self.equity([1000, 1050, 600])                           # 45 %: three steps at most
        self.assertEqual(incidents.prudence()["factor"], 0.512)
        import size
        self.equity([1000, 1000])                                # back at the peak: full tickets
        with mock.patch.object(incidents, "prudence", lambda: {"factor": 0.8}):
            small = size.ticket({"score": 60}, {"liq_usd": 1e6, "symbol": "X"})[0]
        big = size.ticket({"score": 60}, {"liq_usd": 1e6, "symbol": "X"})[0]
        self.assertLess(small, big)


class IncidentAttribution(Base):
    def test_a_winner_giving_back_before_its_stop_is_the_cause(self):
        """Wick, Oct 20: sold at +181% by its trailing stop after a +273% peak; the fall is Wick, not the others."""
        import incidents, paths
        for f in (incidents.LOG, incidents.STATE, config.EQUITY):
            if os.path.exists(f):
                os.remove(f)
        now = time.time()
        W = "Wick111111111111111111111111111111111111111"     # its own price path: other tests write MINT's
        book.open_position(W, "WICK", 1.0, 20000, usd=10)
        paths.append(W, {"t": now - 500, "price": 3.7, "liq": 20000})
        paths.append(W, {"t": now - 30, "price": 2.8, "liq": 20000})
        book.sell(W, 1.0, 2.8, "trailing_stop")
        r = incidents.analyze("note", "test", 600, 9.0, 1100, now, 3.0)
        self.assertEqual(r["cause"], "gains rendus")
        self.assertIn("WICK", r["detail"])
        self.assertIn("stop suiveur", r["detail"])
        self.assertTrue(r["normal"])
        self.assertLess(r["moves"][0]["usd"], 0)                  # its part of the fall
        self.assertGreater(r["moves"][0]["pnl"], 0)               # yet a winning trade

    def test_an_hour_of_gains_handed_back_is_no_incident(self):
        """Oct 20: -$37.79 in an hour, nearly all of it winners handing back unbanked gains: an analysis, no pause."""
        import incidents, paths
        for f in (incidents.LOG, incidents.STATE, incidents.URGENT, config.EQUITY):
            if os.path.exists(f):
                os.remove(f)
        self.addCleanup(lambda: [os.remove(f) for f in (incidents.LOG, incidents.STATE, incidents.URGENT, config.EQUITY) if os.path.exists(f)])
        now = time.time()
        W = "Give111111111111111111111111111111111111111"
        book.open_position(W, "GIVE", 1.0, 20000, usd=25)               # entry ~1.0
        paths.append(W, {"t": now - 3000, "price": 3.0, "liq": 20000})
        paths.append(W, {"t": now - 20, "price": 1.5, "liq": 20000})   # still above entry: all gains handed back
        mk = os.path.join(config.DATA, "marks.json")
        self.addCleanup(lambda: os.path.exists(mk) and os.remove(mk))
        with open(mk, "w") as f:
            f.write('{"t": %d, "marks": {"%s": 1.5}}' % (now, W))
        incidents.tick(now - 120)                                       # first run: marks
        import random
        rng = random.Random(5)
        vals = [1000 + rng.uniform(-1, 1) for _ in range(4000)] + [1070 - i for i in range(0, 40)]
        with open(config.EQUITY, "w") as f:
            f.write("t,balance,realized,unrealized,open\n")
            for i, v in enumerate(vals):
                f.write(f"{now - (len(vals) - 1 - i) * 20},{v},0,0,0\n")
        out = incidents.tick(now)
        self.assertEqual([r["level"] for r in out], ["note"])
        self.assertEqual(out[0]["cause"], "gains rendus")
        self.assertEqual(incidents.paused(), 0)


class SlowSlide(Base):
    def test_a_slow_slide_is_written_up_and_the_reading_always_says_why(self):
        """Oct 21: -$36 over 40 min never crossed the 10-min bar and left no line. a slow slide gets its analysis,
        and the cause of any move is worked out every minute and shown."""
        import incidents, random
        for f in (incidents.LOG, incidents.STATE, incidents.URGENT, config.EQUITY):
            if os.path.exists(f):
                os.remove(f)
        self.addCleanup(lambda: [os.remove(f) for f in (incidents.LOG, incidents.STATE, incidents.URGENT, config.EQUITY) if os.path.exists(f)])
        now = time.time()
        rng = random.Random(9)
        vals = [1000 + rng.uniform(-0.6, 0.6) for _ in range(4000)] + [1000 - 0.09 * i for i in range(1, 181)]
        with open(config.EQUITY, "w") as f:
            f.write("t,balance,realized,unrealized,open\n")
            for i, v in enumerate(vals):
                f.write(f"{now - (len(vals) - 1 - i) * 20},{v},0,0,0\n")
        incidents.tick(now - 60)
        st = incidents._read(incidents.STATE, {}); st.pop("last_note", None); incidents._write(incidents.STATE, st)
        out = incidents.tick(now)
        self.assertEqual([(r["level"], r["window_min"]) for r in out], [("note", 60)])
        self.assertIn("baisse lente", out[0]["why"])
        self.assertEqual(incidents.paused(), 0)
        self.assertIn("sur 1 h", incidents.status()["reading"]["text"])


class IncidentWording(Base):
    def test_noise_ignores_rare_jumps(self):
        """Oct 21: two +$25 take-profits made the usual noise ±$9.10; it is ±$1-3 without them."""
        import incidents, random
        rng = random.Random(2)
        pts, b = [], 1000.0
        for i in range(600):
            b += rng.uniform(-1.5, 1.5) + (25 if i in (200, 400) else 0)
            pts.append((i * 600.0, b))
        self.assertLess(incidents.noise(pts), 2.0)

    def test_a_scam_sold_in_time_is_named_so_and_the_rest_of_the_fall_too(self):
        import incidents
        for f in (incidents.LOG, incidents.STATE, config.EQUITY):
            if os.path.exists(f):
                os.remove(f)
        P = "Pepi111111111111111111111111111111111111111"
        book.open_position(P, "Pepina", 1.0, 20000, usd=25)
        book.sell(P, 1.0, 0.95, "x_scam")
        r = incidents.analyze("incident", "test", 3600, 26.3, 1180, time.time(), 3.0)
        self.assertEqual(r["cause"], "scam repéré")
        self.assertIn("vendu à temps", r["detail"])
        self.assertIn("VIGIE vend ce qui partage", r["text"])


class LongSlide(Base):
    """Oct 21: $1,190 -> $1,140 over three hours, no bar crossed, no line. the slide from the day's peak is
    analysed, past $50 of real loss the desk turns prudent, and it stops being prudent once half is won back."""
    def setUp(self):
        super().setUp()
        import incidents
        self.files = (incidents.LOG, incidents.STATE, incidents.URGENT, config.EQUITY)
        for f in self.files:
            if os.path.exists(f):
                os.remove(f)
        self.addCleanup(lambda: [os.remove(f) for f in self.files if os.path.exists(f)])

    def write(self, vals, now):
        with open(config.EQUITY, "w") as f:
            f.write("t,balance,realized,unrealized,open\n")
            for i, v in enumerate(vals):
                f.write(f"{now - (len(vals) - 1 - i) * 20},{v},0,0,0\n")

    def test_slide_prudence_and_recovery(self):
        import incidents, random
        rng = random.Random(4)
        now = time.time()
        base = [1150 + rng.uniform(-0.5, 0.5) for _ in range(2000)] + [1190.0]
        slide = [1190 - 0.08 * i for i in range(1, 640)]                   # -$51 over 3.5 h, $14 an hour
        self.write(base + slide, now)
        incidents.tick(now - 60)
        st = incidents._read(incidents.STATE, {}); st["dd_level"] = 0; st.pop("prudent", None); incidents._write(incidents.STATE, st)
        out = incidents.tick(now)
        self.assertEqual([r["level"] for r in out], ["prudence"])
        self.assertIn("depuis le plus haut de", out[0]["text"])
        self.assertIn("seulement les tokens notés 65", out[0]["text"])
        self.assertEqual(incidents.strict_score(), 65)
        self.assertEqual(incidents.prudence()["factor"], 0.8)
        self.assertEqual(incidents.paused(), 0)                              # prudence is no pause
        self.write(base + slide + [1150 + i for i in range(1, 25)], now + 600)   # back to $1,174: half won back
        out = incidents.tick(now + 600)
        self.assertIn("PRUDENCE levée", " ".join(r["text"] for r in out))
        self.assertIsNone(incidents.strict_score())

    def test_prudence_buys_only_the_better_setups(self):
        import incidents
        incidents._write(incidents.STATE, {"prudent": {"t": time.time(), "peak": 1190, "low": 1140}})
        self.addCleanup(setattr, check, "ECHO_MODE", check.ECHO_MODE)
        check.ECHO_MODE = "observe"
        with net(), mock.patch.object(incidents, "PRUDENT_MIN_SCORE", 80):    # the test token scores 73
            v = check.run(MINT)
        self.assertIn("prudence", v["action"])
        self.assertNotIn(MINT, book.load())
        with net():                                                           # 73 >= 65: bought, smaller
            v = check.run(MINT)
        self.assertIn("PAPER BUY", v["action"])


class ReplayRealism(unittest.TestCase):
    def test_a_drained_pool_pays_what_it_holds(self):
        """Oct 21: an unlocked-LP token replayed at +263,944,237% from a glitch price in an empty pool."""
        import exitlab
        self.assertEqual(exitlab.fill(40.0, 80000), 40.0)                 # a normal sale: as quoted
        self.assertLess(exitlab.fill(10_000_000.0, 50), 25.0)            # $50 of pool: at most what it holds
        self.assertEqual(exitlab.fill(40.0, 0), 0.0)
        t = 1_000_000.0
        path = [{"t": t, "price": 1.0, "liq": 20000}] + \
               [{"t": t + k * 300, "price": 1.0 + k, "liq": 20000} for k in range(1, 5)] + \
               [{"t": t + 2000, "price": 2_000_000.0, "liq": 30}]           # LP pulled, price reads x2M
        import config
        pnl = exitlab.simulate(path, dict(config.EXIT))
        self.assertLess(pnl, 200)                                          # not $80M on a $25 ticket


class IncidentMemory(Base):
    def test_one_token_is_one_lesson_and_an_old_scam_is_not_the_cause(self):
        import incidents
        for f in (incidents.LOG, incidents.STATE):
            if os.path.exists(f):
                os.remove(f)
        self.addCleanup(lambda: [os.remove(f) for f in (incidents.LOG,) if os.path.exists(f)])
        facts = {"chain": "robinhood", "lane": "early", "source": "tendance GeckoTerminal", "flags": "", "score": "70"}
        with open(incidents.LOG, "w") as f:
            for _ in range(3):                                    # the same Pepina in three analyses
                f.write(json.dumps({"t": time.time(), "lessons": {"PepinaMint": facts}}) + "\n")
        self.assertEqual(incidents.patterns(), [])               # one token: no pattern
        P = "Pepi222222222222222222222222222222222222222"
        book.open_position(P, "Pepina", 1.0, 20000, usd=25)
        book.sell(P, 1.0, 0.95, "x_scam")
        r = incidents.analyze("note", "test", 6 * 3600, 60, 1190, time.time() + 2 * 3600, 3.0)   # 2 h later
        self.assertNotEqual(r["cause"], "scam repéré")


class CopyAlerts(unittest.TestCase):
    """the Telegram lines a human copies: chain, CA, and a sale said as a share of what is still held."""

    def test_buy_line(self):
        import agents
        t = agents.copy_buy("bsc:0xabc", "WICK", "early")
        self.assertIn("ACHAT À COPIER · bsc · voie early · $WICK", t)
        self.assertIn("CA: 0xabc", t)
        self.assertIn("dexscreener.com/bsc/0xabc", t)

    def test_sell_share_of_what_is_left(self):
        import agents
        # the ladder: 50% of the original, then 25% of the original = half of what is left
        t = agents.copy_sell({"mint": "bsc:0xabc", "symbol": "WICK", "share": 0.5, "pct": 210, "reason": "take_profit_2"})
        self.assertIn("vends 50 % de ce qui reste à +210 %", t)
        t = agents.copy_sell({"mint": "So1", "symbol": "X", "closed": True, "share": 0.25, "reason": "x_scam"})
        self.assertIn("solana · $X · vends TOUT", t)


class Live(unittest.TestCase):
    """real money: the paper book's orders, the caps, and the wall around what may ever be signed."""
    TOKEN = "0x" + "ab" * 20
    MINT = "bsc:" + TOKEN

    def setUp(self):
        import live
        self.live = live
        for m in ("dry", "on"):
            if os.path.exists(live._path(m)):
                os.remove(live._path(m))
        for p in (live.STOP, live.LOG):
            if os.path.exists(p):
                os.remove(p)
        self.said = []
        self.patches = [mock.patch.object(live, "say", lambda text, **k: self.said.append(text)),
                        mock.patch.object(live, "honeypot", lambda t: None),
                        mock.patch.object(live, "bnb_usd", lambda: 650.0),
                        mock.patch.object(live, "decimals", lambda t: 18)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_tests_never_trade(self):
        self.assertEqual(self.live.mode(), "off")      # RUG_DESK_DATA is set: real money is off whatever .env says

    def test_only_the_router_is_ever_paid_or_approved(self):
        live, cap = self.live, int(20 / 650 * 1e18)
        live.check_tx(live.ROUTER, cap, "0xdeadbeef", cap)
        with self.assertRaises(RuntimeError):
            live.check_tx(live.ROUTER, cap + 1, "0x", cap)                       # above the cap
        live.check_tx(self.TOKEN, 0, live.APPROVE + live._word(live.ROUTER) + live._word(5), 0)
        with self.assertRaises(RuntimeError):                                    # approving anyone else
            live.check_tx(self.TOKEN, 0, live.APPROVE + live._word("0x" + "11" * 20) + live._word(5), 0)
        with self.assertRaises(RuntimeError):                                    # a transfer(to, amount)
            live.check_tx(self.TOKEN, 0, "0xa9059cbb" + live._word("0x" + "11" * 20) + live._word(5), 0)
        with self.assertRaises(RuntimeError):                                    # BNB sent to an address
            live.check_tx("0x" + "11" * 20, 1, "0x", cap)

    def test_book_sends_buy_and_shares_of_what_is_left(self):
        orders = []
        with mock.patch.object(self.live, "submit", orders.append):
            book.open_position(self.MINT, "WICK", 1.0, 50000, usd=25)
            book.sell(self.MINT, 0.5, 2.0, "take_profit_100")
            book.sell(self.MINT, 0.25, 3.0, "take_profit_200")
            book.sell(self.MINT, 1.0, 2.5, "trailing_stop")
        self.assertEqual([o["side"] for o in orders], ["buy", "sell", "sell", "sell"])
        self.assertAlmostEqual(orders[1]["share"], 0.5)
        self.assertAlmostEqual(orders[2]["share"], 0.5)      # a quarter of the original is half of what is left
        self.assertEqual(orders[3]["share"], 1.0)

    def test_submit_keeps_to_live_chains(self):
        live = self.live
        with mock.patch.object(live, "mode", lambda: "dry"), mock.patch.object(live, "start", lambda: None):
            n = live._q.qsize()
            live.submit({"side": "buy", "mint": "base:" + self.TOKEN})
            live.submit({"side": "buy", "mint": "SoLMint1111"})
            live.submit({"side": "buy", "mint": "bsc:0xnothex"})
            self.assertEqual(live._q.qsize(), n)
            live.submit({"side": "buy", "mint": self.MINT})
            self.assertEqual(live._q.qsize(), n + 1)
            live._q.get_nowait()

    def test_dry_round_trip(self):
        live = self.live
        routes = [{"amountOut": str(13 * 10 ** 18), "gasUsd": "0.05"},      # 13 $ of BNB -> 13 tokens
                  {"amountOut": str(int(10 / 650 * 1e18)), "gasUsd": "0.05"},  # half of them -> 10 $ of BNB
                  {"amountOut": str(int(10 / 650 * 1e18)), "gasUsd": "0.05"}]
        with mock.patch.object(live, "mode", lambda: "dry"), mock.patch.object(live, "route", lambda *a: routes.pop(0)):
            live.buy({"mint": self.MINT, "symbol": "WICK", "price": 0.9})
            pos = live.load()["positions"][self.MINT]
            self.assertEqual(pos["tokens"], 13 * 10 ** 18)
            self.assertAlmostEqual(pos["price"], 13.05 / 13)
            live.sell(self.MINT, 0.5, "take_profit_100")
            self.assertEqual(live.load()["positions"][self.MINT]["tokens"], 13 * 10 ** 18 // 2)
            live.sell(self.MINT, 1.0, "trailing_stop")
            s = live.load()
            self.assertFalse(s["positions"])
            self.assertAlmostEqual(s["closed"][0]["usd_out"], 19.9, places=1)
            self.assertTrue(any("SIMULÉ · vendu tout de $WICK" in t for t in self.said))

    def test_caps_refuse_before_any_network(self):
        live = self.live
        s = live.load("dry")
        s["positions"] = {f"bsc:0x{i:040x}": {} for i in range(3)}
        self.assertIn("3 positions", live.refuse_buy(s, self.MINT))
        s["positions"] = {}
        s["buys"] = [time.time()] * 8
        self.assertIn("8 achats", live.refuse_buy(s, self.MINT))
        s["buys"] = []
        open(live.STOP, "w").close()
        self.assertIn("STOP", live.refuse_buy(s, self.MINT))
        os.remove(live.STOP)
        s["stopped"] = True
        self.assertIn("arrêt", live.refuse_buy(s, self.MINT))

    def test_real_buy_pays_the_router_within_the_cap(self):
        live = self.live
        acct = mock.Mock(address="0x" + "cd" * 20)
        sent = []

        def send(a, to, value, data, cap):
            live.check_tx(to, value, data, cap)
            sent.append((to, value, cap))
            return "0xhash", True, int(0.0001 * 1e18)
        balances = iter([0, 12 * 10 ** 18])
        with mock.patch.object(live, "mode", lambda: "on"), mock.patch.object(live, "account", lambda: acct), \
                mock.patch.object(live, "bnb_balance", lambda a: int(0.1 * 1e18)), \
                mock.patch.object(live, "balance_of", lambda t, o: next(balances)), \
                mock.patch.object(live, "equity", lambda *a: 65.0), \
                mock.patch.object(live, "route", lambda *a: {"amountOut": "1"}), \
                mock.patch.object(live, "build", lambda *a: {"routerAddress": live.ROUTER, "data": "0x12"}), \
                mock.patch.object(live, "send", send):
            live.buy({"mint": self.MINT, "symbol": "WICK", "price": 1.0})
        to, value, cap = sent[0]
        self.assertEqual(to, live.ROUTER)
        self.assertAlmostEqual(value / 1e18 * 650, 13, places=2)
        self.assertLessEqual(value, cap)
        s = live.load("on")
        self.assertEqual(s["start_usd"], 65.0)
        self.assertEqual(s["positions"][self.MINT]["tokens"], 12 * 10 ** 18)

    def test_stop_at_minus_30(self):
        live = self.live
        s = live.load("on")
        s["start_usd"] = 60.0
        live.save(s, "on")
        acct = mock.Mock(address="0x" + "cd" * 20)
        with mock.patch.object(live, "mode", lambda: "on"), mock.patch.object(live, "account", lambda: acct), \
                mock.patch.object(live, "bnb_balance", lambda a: int(40 / 650 * 1e18)):
            st = live.status()
        self.assertTrue(st["stopped"])
        self.assertTrue(live.load("on")["stopped"])
        self.assertTrue(any("arrêt à -30 %" in t for t in self.said))


class SmartNotRugger(unittest.TestCase):
    """a blacklisted creator never counts as smart money, and EVM case does not split a wallet in two."""

    def test_rugger_excluded_and_case_merged(self):
        import smart, ruggers
        mem = {"Good1": {"runs": 3, "crashes": 0}, "Bad1": {"runs": 3, "crashes": 0},
               "0xAbC": {"runs": 2, "crashes": 0}}
        with mock.patch.object(smart, "memory", lambda: mem), \
                mock.patch.object(ruggers, "known", lambda: {"Bad1"}):
            self.assertEqual(smart.count(["Good1", "Bad1"]), 1)
            self.assertEqual(smart.count(["0xabc", "0xABC"]), 1)


class ReplayGlitch(unittest.TestCase):
    """Oct 25 audit: a one-tick x44,600 quote must not be sold in a replay; a confirmed move still is."""

    def test_spike_dropped_real_move_kept(self):
        import exitlab
        base = [{"t": i, "price": 1.0, "liq": 50000} for i in range(6)]
        spike = base + [{"t": 6, "price": 44600.0, "liq": 88770}, {"t": 7, "price": 1.0, "liq": 1.99}]
        self.assertNotIn(44600.0, [p["price"] for p in exitlab.clean(spike)])
        real = base + [{"t": 6, "price": 12.0, "liq": 50000}, {"t": 7, "price": 11.0, "liq": 50000}]
        self.assertIn(12.0, [p["price"] for p in exitlab.clean(real)])

    def test_comma_in_reason_does_not_break_reads(self):
        import pending
        with open(pending.X_READS, "w") as f:
            f.write("time,mint,symbol,verdict,raison\n2026-10-25 10:00,M1,ANTI,BUY,un, deux\n")
        r = pending.reads()["M1"]
        self.assertEqual(r["verdict"], "BUY")
        self.assertEqual(r["raison"], "un, deux")
        os.remove(pending.X_READS)
