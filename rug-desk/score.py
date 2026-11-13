# score.py
# a PASS only means "no obvious rug". the score ranks survivors the way a careful human would:
# many holders, no big wallet, a dev who holds little, two-way trading, real activity, sane age.
# every point lost comes with a flag, so a low score always says why. no model, plain arithmetic.
import math
from config import FACTS
import smart

FLAGS = {
    "few_holders": "peu de holders",
    "bot_volume": "volume de bots ?",
    "quiet": "presque plus d'activité",
    "very_young": "très jeune (< 3 h)",
    "late": "vieux (> 48 h), la hausse est peut-être faite",
    "liq_edge": "liquidité juste au-dessus du minimum",
    "one_sided": "achats et ventes déséquilibrés",
    "concentrated": "top 10 un peu lourd",
    "smart_money": "wallets gagnants déjà vus",
    "no_socials": "ni X ni Telegram ni site",
}


def score(m: dict, t: dict) -> dict:
    """m = market.pool(), t = facts.report(). Returns {"score": 0-100, "flags": [codes]}."""
    pts, flags = 0.0, []
    holders = int(t.get("holders") or 0)
    vol = float(m.get("vol_1h") or 0)
    buys, sells = m.get("buys_1h") or 0, m.get("sells_1h") or 0
    age_h = (m.get("age_min") or 0) / 60

    # holders: 25 pts, log scale, full at 3000+
    pts += 25 * min(1, math.log10(max(holders, 1)) / math.log10(3000))
    if holders < 800:
        flags.append("few_holders")
    # distribution: 20 pts, lighter top 10 and biggest wallet score higher
    top10, maxw = t.get("top10_pct") or 100, t.get("max_wallet_pct") or 100
    pts += 12 * max(0, 1 - top10 / FACTS["max_top10_pct"]) + 8 * max(0, 1 - maxw / FACTS["max_wallet_pct"])
    if top10 > 22:
        flags.append("concentrated")
    # dev: 10 pts
    pts += 10 * max(0, 1 - (t.get("dev_pct") or 0) / FACTS["max_dev_pct"])
    # two-way trading: 15 pts at a 1:1 buy/sell ratio, nothing past 3:1 either way
    if buys + sells:
        ratio = max(buys, sells) / max(1, min(buys, sells))
        pts += 15 * max(0, 1 - (ratio - 1) / 2)
        if ratio > 2:
            flags.append("one_sided")
    # activity: 10 pts, full at $20k an hour
    pts += 10 * min(1, vol / 20000)
    if vol < 5000:
        flags.append("quiet")
    # volume per holder: a few hundred holders moving six figures an hour is bots trading with bots
    per_holder = vol / max(holders, 1)
    if per_holder > 150:
        flags.append("bot_volume")
        pts -= min(25, per_holder / 20)
    # age: 10 pts in the 3-36 h sweet spot
    if age_h < 3:
        flags.append("very_young"); pts += 4
    elif age_h > 48:
        flags.append("late"); pts += 3
    else:
        pts += 10
    # liquidity margin: 10 pts, full at 2x the minimum
    margin = (m.get("liq_usd") or 0) / FACTS["min_liquidity_usd"]
    pts += 10 * min(1, max(0, margin - 1))
    if margin < 1.3:
        flags.append("liq_edge")
    # the team's channels: a Telegram is one of the strongest launch-success predictors on record
    socials = set(m.get("socials") or [])
    pts += 3 * ("telegram" in socials) + 2 * ("twitter" in socials)
    if not socials:
        flags.append("no_socials"); pts -= 5
    # wallets the desk has seen early in several tokens that ran: 5 points each, 10 at most
    n_smart = smart.count(t.get("wallets"))
    if n_smart:
        flags.append("smart_money"); pts += min(10, 5 * n_smart)
    total = max(0, min(100, round(pts)))
    if "bot_volume" in flags:     # the one flag a nice distribution can't buy back
        total = min(total, 40)
    return {"score": total, "flags": flags}
