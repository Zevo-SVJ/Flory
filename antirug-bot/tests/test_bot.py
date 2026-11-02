# tests/test_bot.py
# offline: Telegram and the desk's analysis are faked.   python3 -m pytest -q tests   (from antirug-bot/)
import csv, os, sys, tempfile, time, unittest
from unittest import mock

os.environ["ANTIRUG_DATA"] = tempfile.mkdtemp()
os.environ["RUG_DESK_DATA"] = tempfile.mkdtemp()
os.environ["ANTIRUG_BOT_TOKEN"] = "test"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import local, bot, tgpro, posts  # noqa: E402

CA = "So1anaMint1111111111111111111111111111111"
RED = {"symbol": "RUG", "flags": ["danger:honeypot"], "context": {"liq": 20000, "age_min": 90}, "key": CA}


def msg(text, user=7, lang="en", **extra):
    return {"message": {"chat": {"id": user}, "from": {"id": user, "language_code": lang}, "text": text, **extra}}


class Bot(unittest.TestCase):
    def setUp(self):
        for f in (tgpro.FILE, bot.STATE, bot.USAGE):
            if os.path.exists(f):
                os.remove(f)
        self.sent = []
        self.calls = []
        p1 = mock.patch.object(bot, "send", lambda chat, m: self.sent.append((chat, m)))
        p2 = mock.patch.object(bot, "call", lambda method, **k: self.calls.append((method, k)) or {"ok": True})
        p3 = mock.patch("tgbot.inspect", lambda m: dict(RED, key=m))
        for p in (p1, p2, p3):
            p.start()
            self.addCleanup(p.stop)

    def test_free_quota_then_pro(self):
        for _ in range(tgpro.free_per_day()):
            bot.handle(msg(CA))
        self.assertIn("HIGH RISK", self.sent[0][1])
        self.assertIn("free check(s) left", self.sent[0][1])
        bot.handle(msg(CA))
        self.assertIn("free checks today", self.sent[-1][1])          # the quota message
        bot.handle(msg("/pro"))
        self.assertEqual(self.calls[-1][0], "sendInvoice")
        self.assertEqual(self.calls[-1][1]["currency"], "XTR")
        bot.handle({"pre_checkout_query": {"id": "q1"}})
        self.assertEqual(self.calls[-1], ("answerPreCheckoutQuery", {"pre_checkout_query_id": "q1", "ok": True}))
        bot.handle(msg("", successful_payment={"telegram_payment_charge_id": "c1", "total_amount": 500}))
        self.assertTrue(tgpro.is_pro(7))
        self.assertGreater(tgpro.pro_until(7), time.time() + 29 * 86400)
        n = len(self.sent)
        bot.handle(msg(CA))
        self.assertIn("HIGH RISK", self.sent[n][1])
        self.assertNotIn("left", self.sent[n][1])

    def test_french_user_gets_french(self):
        bot.handle(msg(CA, user=8, lang="fr"))
        self.assertIn("RISQUE ÉLEVÉ", self.sent[0][1])

    def test_a_second_pass_extends_from_the_end_of_the_first(self):
        a = tgpro.grant(9, "c1", 500)
        b = tgpro.grant(9, "c2", 500)
        self.assertAlmostEqual(b - a, tgpro.days() * 86400, delta=5)

    def test_owner_pairs_with_the_printed_code_and_gets_stats(self):
        bot.handle(msg("/owner 000000", user=5))
        self.assertIsNone(bot.owner())
        bot.handle(msg(f"/owner {bot.owner_code()}", user=5))
        self.assertEqual(bot.owner(), "5")
        bot.handle(msg("/stats", user=5))
        self.assertIn("Pro actifs", self.sent[-1][1])


class Posts(unittest.TestCase):
    def test_drafts_come_from_the_audit_file_with_their_denominators(self):
        import config
        now = time.strftime("%Y-%m-%d %H:%M")
        with open(config.AUDIT, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["time", "mint", "symbol", "stage", "verdict", "reason", "price0", "price_after", "change_pct", "hours"])
            w.writerow([now, "a", "AAA", "facts", "SKIP", "dev_holds", 1, 0.02, -98, 6])
            w.writerow([now, "b", "BBB", "facts", "SKIP", "copycat", 1, 1, 0, 6])          # dead: not counted as moved
            w.writerow([now, "c", "CCC", "facts", "SKIP", "lp_unlocked", 1, 1.2, 20, 6])
        d = posts.drafts(24)
        self.assertIn("flagged 3 tokens", d["en"][0])
        self.assertIn("Of the 2 still trading, 1 lost 50%+", d["en"][0])
        self.assertIn("$AAA -98%", d["en"][0])
        self.assertIn("a signalé 3 tokens", d["fr"][0])


if __name__ == "__main__":
    unittest.main()
