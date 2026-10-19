# check.py
# one contract address in, one verdict out. limits, pool, facts, judge, in that order.
# the first one that says no ends it.
import csv, json, os, sys, time
from config import FACTS
from config import (DATA, LOG, JUDGE, MIN_CONFIDENCE, PAPER, PAPER_BUY_ON_PASS, TICKET_USD,
                    ECHO_MODE, MIN_SCORE)
from score import score
import pending, smart, size, jup, cluster, stracker, ruggers
from config import DEEP
from facts import report, fact_kill
import facts
from market import pool, market_kill
import market
import book

# price and liq_usd at verdict time let AUDIT check later whether a kill or a pass was right
FIELDS = ["time", "mint", "symbol", "stage", "verdict", "confidence", "reason", "price", "liq_usd",
          "score", "flags", "sol_1h", "sol_24h", "age_min", "dev", "ticket", "tier",
          "organic", "organic_vol", "dev_mints", "cluster_pct", "fresh_pct", "bundlers_pct", "insiders_pct",
          "snipers_pct", "factory_wallets", "lane"]


def _migrate():
    """An older checks.csv has fewer columns: rewrite it once with the new header."""
    with open(LOG, newline="") as f:
        r = csv.DictReader(f)
        if r.fieldnames == FIELDS:
            return
        rows = list(r)
    with open(LOG, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k) for k in FIELDS})


def log(row: dict):
    os.makedirs(DATA, exist_ok=True)
    new = not os.path.exists(LOG)
    if not new:
        _migrate()
    with open(LOG, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k) for k in FIELDS})


def judge(token: dict, m: dict) -> dict:
    if JUDGE == "none":       # free desk: no X read. a PASS means "survived 13 checks", nothing more
        return {"stage": "judge", "verdict": "PASS",
                "reason": "passed every code check, no X read (JUDGE=none)"}
    from grok import ask      # imported here so the free desk never needs a key
    from prompts import JUDGE_PROMPT
    try:
        ans = ask(JUDGE_PROMPT, {"token": token, "pool": m}, read_x=True)   # the only paid step
    except Exception as e:
        return {"stage": "judge", "verdict": "SKIP", "reason": f"grok failed: {e}"}
    verdict, conf = ans.get("verdict"), ans.get("confidence") or 0
    if verdict not in ("BUY", "SKIP"):
        verdict = "SKIP"
    if verdict == "BUY" and conf < MIN_CONFIDENCE:
        verdict, ans["why"] = "SKIP", f"low confidence {conf}"
    return {**ans, "stage": "judge", "verdict": verdict, "reason": ans.get("why")}


def check(mint: str) -> dict:
    import shadow
    waived = shadow.waived()             # soft kills the shadow book showed cost money: passed over
    if (g := book.guard(mint)):                                  # limits, free
        return {"stage": "limits", "verdict": "SKIP", "reason": g}

    # pool first: same checks as the article, but most leads die here (thin or fresh pools)
    # in one fast call, so the slower fact sources only see tokens worth a report
    try:
        m = pool(mint)                                           # pool, free
    except Exception as e:
        return {"stage": "pool", "verdict": "SKIP", "reason": f"dexscreener failed: {e}"}
    seen = {"price": (m or {}).get("price"), "liq_usd": (m or {}).get("liq_usd"), "age_min": (m or {}).get("age_min"),
            "lane": market.lane(m) if m else None}
    if (k := market_kill(m)):
        return {"stage": "pool", "verdict": "SKIP", "reason": k, "symbol": (m or {}).get("symbol"), **seen}
    if market.lane(m) == "early":                                # still under its graduation price: the
        import grads                                             # first-hour dump has not been absorbed
        p0 = grads.birth_price(mint)
        if p0 and m.get("price_native") and m["price_native"] < FACTS["min_vs_graduation"] * p0:
            return {"stage": "pool", "verdict": "SKIP", "reason": "below_graduation", "symbol": m.get("symbol"), **seen}
    if (k := market.copycat(m, mint)) and k not in waived:       # a rug factory's name, or a bigger owner
        return {"stage": "pool", "verdict": "SKIP", "reason": k, "symbol": m.get("symbol"), **seen}

    # the pool as it is on chain right now. DexScreener can lag a pool by minutes: a token already dumped
    # can still show its old liquidity there, and get bought at a price that no longer exists
    if m.get("dex") == "pumpswap":
        try:
            vaults = facts.pool_vaults(m["pair"])
            res = facts.reserves(vaults) if vaults else None
        except Exception:
            vaults, res = None, None
        if res and None not in res:
            if m.get("liq_quote") and res[1] < 0.7 * m["liq_quote"]:
                return {"stage": "pool", "verdict": "SKIP", "reason": "stale_data", "symbol": m.get("symbol"), **seen}
            seen.update(vaults=vaults, sol0=res[1])        # VIGIE watches these vaults once bought

    try:
        token = report(mint, m)                                  # rug filter, free
    except Exception as e:
        return {"stage": "facts", "verdict": "SKIP", "reason": f"facts failed: {e}",
                "symbol": m["symbol"], **seen}
    seen["dev"] = token.get("dev")
    smart.snapshot(mint, token.get("all_owners") or token.get("wallets"))
    if (k := fact_kill(token, market.lane(m), waived)):
        return {"stage": "facts", "verdict": "SKIP", "reason": k,
                "symbol": m["symbol"] or token["symbol"], **seen}

    v = judge(token, m)
    sym = m["symbol"] or token["symbol"]
    sc = score(m, token)
    if sc["score"] >= MIN_SCORE:            # the deep read costs calls: only for tokens that could be bought
        deep = deep_read(mint, token, skip=waived)
        seen.update(deep["logged"])
        if deep["kill"]:
            return {"stage": "deep", "verdict": "SKIP", "reason": deep["kill"], "symbol": sym, **seen,
                    "score": sc["score"]}
    usd, tier, sig = size.ticket({"score": sc["score"]}, m, token)
    return {**v, **seen, "ticket": usd, "tier": tier, "signals": sig, "symbol": sym, "price": m["price"], "liq_usd": m["liq_usd"], "url": m["url"],
            "score": sc["score"], "flags": " ".join(sc["flags"]),
            # the free check 14: two links you open yourself. latest posts, not "top"
            "x_ca": f"https://x.com/search?q={mint}&f=live",
            "x_ticker": f"https://x.com/search?q=%24{sym}&f=live"}


def deep_read(mint: str, token: dict, desk: bool = True, skip: frozenset | set = frozenset()) -> dict:
    """Three outside reads, cheapest first, each one optional: a source that fails is unknown, not a kill.
    Jupiter (free) -> who funded the top holders (RPC) -> Solana Tracker (key, 2,500 free requests).
    desk=False (the Telegram bot): reads only, no memory written and Solana Tracker's daily cap kept for the desk."""
    logged, kill = {}, None
    # wallets that held earlier rugs and no winner: a factory reuses its wallet pool (the FOMO and Gemini
    # dump sellers had thousands of transactions each, active since Oct 10)
    n_toxic = smart.toxic(token.get("all_owners") or token.get("wallets") or [])
    logged["factory_wallets"] = n_toxic
    if n_toxic >= DEEP["max_factory_wallets"]:
        return {"kill": "factory_wallets", "logged": logged}
    try:
        j = jup.fetch(mint)
    except Exception:
        j = None
    if j:
        logged.update(organic=j["organic"], organic_vol=j["organic_vol_share"], dev_mints=j["dev_mints"])
        kill = jup.kill(j, DEEP)
        kill = None if kill in skip else kill
    if not kill:
        try:
            c = cluster.analyze(token.get("holder_pcts") or [])
        except Exception:
            c = None
        if c:
            logged.update(cluster_pct=c["cluster_pct"], fresh_pct=c["fresh_pct"])
            if desk:
                ruggers.note_funder(mint, c["cluster_funder"])
            kill = cluster.kill(c, DEEP, ruggers.funders())
            kill = None if kill in skip else kill
    if not kill and desk:
        try:
            s = stracker.fetch(mint)
        except Exception:
            s = None
        if s:
            logged.update(bundlers_pct=s["bundlers_pct"], insiders_pct=s["insiders_pct"], snipers_pct=s["snipers_pct"])
            kill = stracker.kill(s, DEEP)
            kill = None if kill in skip else kill
    return {"kill": kill, "logged": logged}


def run(mint: str) -> dict:
    v = check(mint)
    v.update(market.sol_regime() or {})
    log({"time": time.strftime("%Y-%m-%d %H:%M"), "mint": mint, **v})
    import dossier
    dossier.add(mint, "GARDE", v["verdict"], **{k: v.get(k) for k in (
        "stage", "reason", "symbol", "lane", "score", "flags", "tier", "signals", "ticket", "price", "liq_usd",
        "organic", "organic_vol", "dev_mints", "cluster_pct", "fresh_pct", "bundlers_pct", "insiders_pct",
        "snipers_pct", "factory_wallets")})
    enter = v["verdict"] == "BUY" or (v["verdict"] == "PASS" and PAPER and PAPER_BUY_ON_PASS)
    import shadow
    if enter and (v.get("score") or 0) < MIN_SCORE and "low_score" not in shadow.waived():
        v["action"] = f"not bought: score {v['score']} < {MIN_SCORE} ({v.get('flags') or 'no flag'})"
        return v
    if enter and PAPER and v["verdict"] == "PASS" and ECHO_MODE == "gate":
        pending.add(mint, {**v, "flags": (v.get("flags") or "").split()})
        v["action"] = f"waiting for ECHO's X read (score {v['score']})"
        return v
    if enter and PAPER:
        book.open_position(mint, v["symbol"], v["price"], v["liq_usd"], usd=v.get("ticket") or TICKET_USD,
                           vaults=v.get("vaults"), sol0=v.get("sol0"))
        dossier.add(mint, "GARDE", "achat", usd=v.get("ticket") or TICKET_USD, tier=v.get("tier"), price=v["price"])
        v["action"] = (f"PAPER BUY ${v.get('ticket') or TICKET_USD:.0f} ({v.get('tier', 'base')}"
                       + (f": {', '.join(v['signals'])}" if v.get("signals") else "") + f") at {v['price']}")
        if v["verdict"] == "PASS" and ECHO_MODE == "observe":   # ECHO still reads it, after the buy
            pending.add(mint, {**v, "flags": (v.get("flags") or "").split(), "shadow": True})
    elif v["verdict"] in ("BUY", "PASS") and not PAPER:
        pre = "" if v["verdict"] == "BUY" else "no X read: search the ticker and CA on X yourself first. "
        v["action"] = (f"APPROVAL NEEDED: {pre}buy ${TICKET_USD} of {v['symbol']} in your own wallet, "
                       f"then run: python book.py add {mint} {TICKET_USD} <fill price> {v['liq_usd']}")
    return v


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1].strip()), indent=2))
