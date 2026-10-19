# tests/test_desk.py
# offline tests: every API is faked, so this runs anywhere.  python -m unittest discover tests
import os, sys, tempfile, time, unittest
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


class Sizing(Base):
    def test_more_signals_bigger_ticket_capped_by_the_pool(self):
        import size
        calm = {"symbol": "A", "liq_usd": 80000, "vol_1h": 5000, "buys_5m": 2, "sells_5m": 2}
        hot = {"symbol": "B", "liq_usd": 80000, "vol_1h": 120000, "buys_5m": 40, "sells_5m": 10}
        usd0, tier0, _ = size.ticket({"score": 60}, calm)
        usd1, tier1, sig = size.ticket({"score": 90}, hot)
        self.assertEqual((tier0, tier1), ("base", "max"), sig)
        self.assertEqual(usd0, config.PAPER_BANKROLL_USD * config.SIZING["base"] / 100)
        self.assertGreater(usd1, usd0)
        thin = dict(hot, liq_usd=5000)
        self.assertEqual(size.ticket({"score": 90}, thin)[0], 5000 * config.FACTS["max_ticket_share"])


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
        def get(url, timeout=None, params=None):
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
        self.assertIn(MINT, book.load())              # the read is recorded, the position stays
        self.assertIn("after the buy", ev[0]["text"])

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
        # bots: 300 holders trading $200k an hour
        with net(gp=goplus(holder_count="300"), ds=ds_pairs()):
            with mock.patch("score.score", return_value={"score": 30, "flags": ["bot_volume"]}), \
                 mock.patch("check.score", return_value={"score": 30, "flags": ["bot_volume"]}):
                v = check.run(MINT)
        self.assertIn("not bought: score 30", v["action"])
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


class Copycat(Base):
    def test_a_smaller_token_under_a_bigger_ticker_is_killed(self):
        import market
        market._tickers.clear()
        big = {"chainId": "solana", "baseToken": {"address": "BIGONE", "symbol": "TEST"}, "liquidity": {"usd": 900000},
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
        book.open_position(MINT, "T", 1.0, 50000)            # $25 on $50k: 0.1% impact + 0.3% fee
        p = book.load()[MINT]
        self.assertAlmostEqual(p["entry"], 1.004, places=6)
        pnl = book.sell(MINT, 1.0, 1.0, "flat", 50000)       # flat price still loses the round trip
        self.assertLess(pnl, -0.2)
        self.assertGreater(pnl, -0.35)


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
        self.assertEqual(edge.stats([rng.gauss(0.1, 8) for _ in range(80)])["verdict"], "no")
        good = edge.stats([rng.gauss(2.0, 5) for _ in range(80)])
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
