# posts.py
# drafts for X, from what the desk's anti-rug engine really did: every token it flagged is re-priced 6 h later
# (rug-desk/data/audit.csv). nothing is posted: you read, pick, post yourself. numbers are what the file says,
# with their denominators, and the examples are real tokens with the reason they were flagged.
#   python3 posts.py          last 24 h        python3 posts.py 168      last 7 days
import csv, os, sys, time
import local                                    # ../rug-desk on the path
import texts

def rows(hours: float) -> list[dict]:
    import config
    try:
        with open(config.AUDIT, newline="") as f:
            rs = list(csv.DictReader(f))
    except OSError:
        return []
    cut = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - hours * 3600))
    return [r for r in rs if r["time"] >= cut]


# reasons a reader feels at once, shown first in the examples: a trap, a dev or a bundle, not "unverified"
STRONG = ["danger:honeypot", "nobody_can_sell", "danger:high_tax", "danger:cannot_sell_all", "dev_rugged_before",
          "serial_farm", "factory_wallets", "rug_funder", "bundle_same_sol", "bundle_ladder", "holder_farm",
          "dev_holds", "mint_open", "freeze_open", "lp_unlocked", "whale", "top10_heavy", "copycat", "fake_cap"]


SHORT = {"danger:honeypot": "honeypot", "nobody_can_sell": "nobody can sell", "danger:high_tax": "hidden sell tax",
         "danger:cannot_sell_all": "can't sell it all", "dev_rugged_before": "dev rugged before",
         "serial_farm": "rug factory name", "factory_wallets": "rug factory wallets", "rug_funder": "funded by a rugger",
         "bundle_same_sol": "bundled wallets", "bundle_ladder": "bundled wallets", "holder_farm": "wallet farm",
         "dev_holds": "dev holds the supply", "mint_open": "dev can print tokens", "freeze_open": "dev can freeze you",
         "lp_unlocked": "liquidity can be pulled", "whale": "one whale", "top10_heavy": "top 10 hold it all",
         "copycat": "copy of a bigger coin", "fake_cap": "fake market cap", "danger:closed_source": "hidden contract code",
         "lp_unverified": "unverifiable liquidity", "dev_unknown": "unknown dev", "micro_trades": "bot volume"}


def short(reason: str) -> str:
    return SHORT.get(reason) or reason.replace("danger:", "")


def link() -> str:
    """t.me/<the bot>, from Telegram (getMe) with the bot's token, or ANTIRUG_BOT_LINK in .env."""
    if local.get("ANTIRUG_BOT_LINK"):
        return local.get("ANTIRUG_BOT_LINK")
    tok = local.get("ANTIRUG_BOT_TOKEN")
    if tok:
        try:
            import requests
            u = requests.get(f"https://api.telegram.org/bot{tok}/getMe", timeout=10).json()["result"]["username"]
            return f"t.me/{u}"
        except Exception:
            pass
    return ""


def label(reason: str, lang: str) -> str:
    import tgbot
    return (tgbot.LABELS if lang == "fr" else texts.EN).get(reason) or reason


def culprit(reason: str) -> str:
    """The line after the verdict, for what the bot actually caught."""
    if reason.startswith("danger:") or reason in ("nobody_can_sell", "mint_open", "freeze_open"):
        return "it looked like any other coin. the contract didn't."
    if reason in ("dev_rugged_before", "dev_holds", "serial_dev"):
        return "it looked like any other coin. the dev didn't."
    if reason in ("lp_unlocked", "lp_unverified", "fake_cap"):
        return "it looked like any other coin. the liquidity didn't."
    return "it looked like any other coin. the wallets didn't."


def bare(key: str) -> str:
    """The address to paste in the bot: no "bsc:" in front."""
    return key.split(":", 1)[1] if ":" in key else key


def _clock(ts: str) -> str:
    """'2026-11-02 20:47' -> '8:47pm', the way the posts that work on X tell time."""
    t = time.strptime(ts, "%Y-%m-%d %H:%M")
    return time.strftime("%I:%M%p", t).lstrip("0").lower()


def drafts(hours: float = 24) -> dict[str, list[dict]]:
    """{"en": [{"post", "reply", "note"}]}: the post, the first reply that carries the link (X cuts the reach of
    a post with a link in it), and what to do with it. same style as the memecoin posts that work: a caps hook
    with an exact number, short lines, arrows, times, a question, the link below. every number is from the file."""
    rs = rows(hours)
    killed = []
    for r in rs:
        try:
            ch = float(r["change_pct"])
        except (TypeError, ValueError):
            continue
        if r["verdict"] == "SKIP" and " failed" not in (r["reason"] or "") and r["reason"] in texts.EN:
            killed.append((ch, r))
    seen = set()                                                    # one line per token: its latest verdict
    killed = [(ch, r) for ch, r in sorted(killed, key=lambda x: x[1]["time"], reverse=True)
              if not (r["mint"] in seen or seen.add(r["mint"]))]
    moved = [(ch, r) for ch, r in killed if abs(ch) >= 1]           # still traded: a price that moved
    rank = lambda r: STRONG.index(r["reason"]) if r["reason"] in STRONG else len(STRONG)
    crashed = sorted([(ch, r) for ch, r in moved if ch <= -50], key=lambda x: (rank(x[1]), x[0]))
    out = {"en": []}
    if not moved:
        return out
    # examples: tickers an English reader can read first, one per reason, strongest reasons first
    latin = lambda s: s.isascii() and any(c.isalpha() for c in s)
    ex, syms, why = [], set(), set()
    for ch, r in sorted(crashed, key=lambda x: (not latin(x[1]["symbol"]), rank(x[1]), x[0])):
        if r["symbol"] not in syms and r["reason"] not in why:
            ex.append((ch, r))
            syms.add(r["symbol"])
            why.add(r["reason"])
        if len(ex) == 3:
            break
    url = link()
    reply = f"the bot: {url}\nfree, 3 checks a day. paste a CA, get the answer." if url else "the bot: (your t.me link)"
    span = "IN 24 HOURS" if hours <= 24 else f"IN {hours / 24:.0f} DAYS"
    lab = lambda r: label(r["reason"], "en")
    # 1. the shock number
    out["en"].append({"post": (
        f"MY BOT FLAGGED {len(killed):,} MEMECOINS {span}.\n\n"
        f"{len(crashed):,} of them lost 50%+ within 6 hours.\n\n"
        "i didn't buy a single one.\n\n"
        "here's what it checks in 5 seconds, every time:\n"
        "→ can the dev pull the liquidity\n"
        "→ is it a honeypot (buy yes, sell no)\n"
        "→ bundled wallets holding the supply\n"
        "→ devs who already rugged before\n"
        "→ wallets from known rug factories\n\n"
        "you paste a CA. it answers. that's it.\n\n"
        f"be honest, how many of those {len(crashed):,} would you have aped?\n\n"
        "bot in the reply ↓"), "reply": reply,
        "note": f"denominator if asked: {len(moved):,} of the {len(killed):,} flagged had a price that moved in the 6 h "
                f"(a drained pool counts as -100%)",
        "card": {"title": f"FLAGGED {len(killed):,} MEMECOINS\n{span.lower()}", "big": f"{len(crashed):,}",
                 "big_note": "lost 50%+ within 6 hours",
                 "rows": [(f"${r['symbol']} {ch:+.0f}%", short(r["reason"])) for ch, r in ex]}})
    # 2. the story with times, on the strongest real example
    if ex:
        ch, r = ex[0]
        # audit.csv's time is the re-pricing, hours after the flag: the flag came `hours` before it
        t1 = time.mktime(time.strptime(r["time"], "%Y-%m-%d %H:%M"))
        flagged = time.strftime("%Y-%m-%d %H:%M", time.localtime(t1 - float(r.get("hours") or 6) * 3600))
        later = _clock(r["time"])
        out["en"].append({"post": (
            f"{_clock(flagged)}: ${r['symbol']} is moving. people are aping.\n\n"
            f"my bot looks at it for 5 seconds.\n🔴 HIGH RISK: {lab(r)}.\n\n"
            f"{later}: ${r['symbol']} {ch:+.0f}%.\n\n"
            f"{culprit(r['reason'])}\n\n"
            "check before you buy, not after ↓"), "reply": reply,
            "note": "add a screenshot of the bot's answer on this CA: " + bare(r["mint"]),
            "card": {"title": f"${r['symbol']}\nHIGH RISK", "big": f"{ch:+.0f}%", "big_note": "6 hours later",
                     "rows": [("flagged:", short(r["reason"]))]}})
    # 3. receipts, three tokens
    if len(ex) >= 2:
        lines = "\n".join(f"→ ${r['symbol']} {ch:+.0f}% · {lab(r)}" for ch, r in ex)
        out["en"].append({"post": (
            f"{len(ex)} COINS MY BOT FLAGGED {span}. 6 HOURS LATER:\n\n{lines}\n\n"
            "every one of them had a chart that looked tradeable.\n\n"
            "bookmark this before you ape your next coin.\n\nbot below ↓"), "reply": reply,
            "note": "post with screenshots of the bot's answers on these CAs: " + " · ".join(bare(r["mint"]) for _, r in ex),
            "card": {"title": f"{len(ex)} COINS MY BOT FLAGGED\n6 hours later", "big": "",
                     "rows": [(f"${r['symbol']} {ch:+.0f}%", short(r["reason"])) for ch, r in ex]}})
    # 4. the video
    if ex:
        ch, r = ex[0]
        out["en"].append({"post": (
            "5 seconds.\n\nthat's how long it takes to know if the coin you're about to ape is a rug.\n\n"
            "free, 3 checks a day. link below ↓"), "reply": reply,
            "note": f"film your screen: paste {bare(r['mint'])} (${r['symbol']}) in the bot, the answer comes back. "
                    "attach the video (native, under 2:20)"})
    return out


# when the day's post goes out: 9:30am New York, Tuesday-Thursday mornings lead every study (Buffer, 8.7M posts;
# Sprout Social; SocialChamp), 9:30 ET is the crypto slot (US market open), Saturday is the weakest day.
# antirug-bot/.env: ANTIRUG_POST_NY=09:30   ANTIRUG_SKIP_DAYS=Sat   (New York time, handles US daylight saving)
WINDOW_MIN = 60             # POSTER.md runs every hour: the first run inside this window posts


def post_time() -> tuple[bool, str]:
    """(is it time to post, the next slot in Paris time)."""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    ny, paris = ZoneInfo("America/New_York"), ZoneInfo("Europe/Paris")
    hh, mm = (int(x) for x in (local.get("ANTIRUG_POST_NY") or "09:30").split(":"))
    skip = {d.strip()[:3].lower() for d in (local.get("ANTIRUG_SKIP_DAYS") or "Sat").split(",") if d.strip()}
    now = datetime.now(ny)
    for day in range(0, 8):
        slot = (now + timedelta(days=day)).replace(hour=hh, minute=mm, second=0, microsecond=0)
        if slot.strftime("%a").lower() in skip:
            continue
        if slot <= now < slot + timedelta(minutes=WINDOW_MIN):
            return True, slot.astimezone(paris).strftime("%a %d %H:%M")
        if slot > now:
            return False, slot.astimezone(paris).strftime("%a %d %H:%M")
    return False, "?"


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    h = float(args[0]) if args else 24
    d = drafts(h)
    if "--today" in sys.argv:                            # POSTER.md: the one post of the day, nothing else
        due, slot = post_time()
        if not due and "--now" not in sys.argv:
            print(f"WAIT · next post {slot} Paris time (9:30am New York)")
            sys.exit(0)
        if not d["en"]:
            print("NOTHING TO POST")
            sys.exit(0)
        x = d["en"][int(time.strftime("%j")) % len(d["en"])]     # a different format each day
        attach = x["note"]
        if x.get("card"):                                   # the picture of the day, from the same numbers
            import card
            url = link()
            path = card.render({**x["card"], "footer": f"Anti-Rug Scanner · {url}" if url else "Anti-Rug Scanner"},
                               os.path.join(local.HERE, f"card-{time.strftime('%Y-%m-%d')}.png"))
            if path:
                attach = f"IMAGE {path}"
        print(f"=== POST\n{x['post']}\n=== REPLY\n{x['reply']}\n=== ATTACH\n{attach}")
        sys.exit(0)
    if not d["en"]:
        print("pas encore de données sur cette période (rug-desk/data/audit.csv)")
    for i, x in enumerate(d["en"], 1):                  # English only: X's memecoin crowd reads English
        print(f"===== POST {i} ({len(x['post'])} characters)\n{x['post']}\n")
        print(f"----- first reply (the link goes here, never in the post)\n{x['reply']}\n")
        print(f"----- to do: {x['note']}\n")
    if d["en"]:
        print("rules: link in the first reply · post 3-7pm or 10pm-midnight Paris time · answer every reply in the "
              "first hour · a native video beats text · never post a number you can't prove")
