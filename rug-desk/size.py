# size.py
# how much to put on a PASS. paper training: the size grows with the setup, as a share of the balance,
# so a good week compounds and a bad one shrinks the next tickets by itself.
#   base    a PASS, nothing more
#   strong  2-3 signals out of 6
#   max     4+ signals: the "real opportunity" case
# the six signals are things the desk measures, never a name: celebrity and brand names are where the
# fakes concentrate (on Oct 19, the $100M+ "caps" among graduates were all Tesla / US-fund / oil clones).
# whether the bigger tickets earn more is itself measured: each trade logs its tier, the evening report
# splits the P&L by tier. live sizing is edge.py's quarter Kelly, never this.
from config import SIZING, FACTS, PAPER_BANKROLL_USD, TICKET_USD
import book, smart


def signals(v: dict, m: dict, t: dict | None) -> list[str]:
    out = []
    sc = v.get("score") or 0
    if sc >= SIZING["score_strong"]:
        out.append(f"score {sc}")
    if sc >= SIZING["score_max"]:
        out.append("top score")
    liq, vol = m.get("liq_usd") or 0, m.get("vol_1h") or 0
    if liq and vol / liq >= SIZING["turnover_hot"]:          # the pool traded its own size in an hour
        out.append(f"turnover x{vol / liq:.1f}")
    b, s = m.get("buys_5m") or 0, m.get("sells_5m") or 0
    if b >= 10 and b >= 1.3 * s:                             # buyers in charge right now
        out.append("buyers 5m")
    if t and smart.count(t.get("wallets") or []):            # wallets that were early on past runners
        out.append("smart wallets")
    import scan                                              # late: scan imports check imports this
    words = scan.narratives()                                # ECHO's X narrative scan
    sym = (m.get("symbol") or "").lower()
    if sym and any(w in sym or sym in w for w in words if len(w) >= 3):
        out.append("X narrative")
    return out


def ticket(v: dict, m: dict, t: dict | None = None) -> tuple[float, str, list[str]]:
    """(usd, tier, signals). Never more than the pool can take, never more than the free cash."""
    sig = signals(v, m, t)
    tier = "max" if len(sig) >= 4 else "strong" if len(sig) >= 2 else "base"
    equity = PAPER_BANKROLL_USD + book.realized()
    usd = equity * SIZING[tier] / 100
    usd = min(usd, (m.get("liq_usd") or 0) * FACTS["max_ticket_share"], book.cash())
    return round(max(usd, min(TICKET_USD, book.cash())), 2), tier, sig
