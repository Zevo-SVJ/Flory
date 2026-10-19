# tests/test_desk.py
# offline tests: every API is faked, so this runs anywhere.  python -m unittest discover tests
import os, sys, tempfile, threading, time, unittest
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
            {"reason": "bundle_same_sol", "n": 25, "mean": 9.0, "half1": 6.0, "half2": 12.0},
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
