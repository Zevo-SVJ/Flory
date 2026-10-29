# check.py
# one contract address in, one verdict out. limits, pool, facts, judge, in that order.
# the first one that says no ends it.
import csv, json, os, sys, time
from config import FACTS
from config import (DATA, LOG, JUDGE, MIN_CONFIDENCE, PAPER, PAPER_BUY_ON_PASS, TICKET_USD,
                    ECHO_MODE, MIN_SCORE, SIZING, PAPER_BANKROLL_USD)
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
          "snipers_pct", "factory_wallets", "lane",
          # what learn.py learns from: the token as GARDE saw it at the verdict
          "chain", "vol_liq", "avg_trade", "chg_1h", "chg_5m", "buy_ratio", "mcap_liq", "socials",
          "top10", "max_wallet", "holders", "expected", "override", "dial",
          "rc_score", "rc_danger", "rc_lp_locked"]


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


def chains_split(mint: str) -> str:
    import chains
    return chains.split(mint)[0]


def _expected(seen: dict, reason: str) -> float | None:
    """learn.py's predicted net % per trade for this token, None until the model is trusted."""
    import learn, majors
    try:
        return learn.expected({**seen, **(market.sol_regime() or {}), "dial": majors.dial_value(), "reason": reason})
    except Exception:
        return None


def _trusted() -> bool:
    import learn
    return bool(learn.load().get("trusted"))


# pool-stage soft kills the trusted model may overrule. it needs the whole token to judge (holders, score,
# RugCheck), so the kill is held while the other checks run, and applied at the end unless the model
# expects a profit. serial_farm (a rug factory) and every hard kill are never held
DEFERRABLE = ("below_graduation", "copycat")


def _model_override(reason: str, seen: dict) -> bool:
    """A soft kill the trusted model expects to be wrong. hard kills never reach the model."""
    import learn
    if reason not in learn.SOFT:
        return False
    exp = _expected(seen, reason)
    return exp is not None and exp >= learn.OVERRIDE_PCT


def check(mint: str) -> dict:
    import shadow
    waived = shadow.waived()             # soft kills the shadow book showed cost money: passed over
    x = pending.reads().get(mint)                                # ECHO already found a scam on X: never again
    if x and (x.get("verdict") or "").upper() == "SCAM":
        return {"stage": "limits", "verdict": "SKIP", "reason": "x_scam_before", "symbol": x.get("symbol")}
    if (g := book.guard(mint)):                                  # limits, free
        return {"stage": "limits", "verdict": "SKIP", "reason": g}

    # pool first: same checks as the article, but most leads die here (thin or fresh pools)
    # in one fast call, so the slower fact sources only see tokens worth a report
    try:
        m = pool(mint)                                           # pool, free
    except Exception as e:
        return {"stage": "pool", "verdict": "SKIP", "reason": f"dexscreener failed: {e}"}
    mm = m or {}
    held = None                                                  # a pool soft kill waiting for the model
    liq = mm.get("liq_usd") or 0
    seen = {"chain": chains_split(mint), "vol_liq": round((mm.get("vol_1h") or 0) / liq, 3) if liq else None,
            "avg_trade": round(mm.get("avg_trade_1h") or 0, 1) if m else None,
            "chg_1h": mm.get("chg_1h"), "chg_5m": mm.get("chg_5m"),
            "buy_ratio": round((mm.get("buys_1h") or 0) / max(1, (mm.get("buys_1h") or 0) + (mm.get("sells_1h") or 0)), 3) if m else None,
            "mcap_liq": round((mm.get("mcap") or 0) / liq, 2) if liq else None,
            "socials": len(mm.get("socials") or []) if m else None}
    seen.update({"price": (m or {}).get("price"), "liq_usd": (m or {}).get("liq_usd"), "age_min": (m or {}).get("age_min"),
            "lane": market.lane(m) if m else None})
    if (k := market_kill(m, waived)):
        return {"stage": "pool", "verdict": "SKIP", "reason": k, "symbol": (m or {}).get("symbol"), **seen}
    import chains
    evm = chains.is_evm(mint)
    if market.lane(m) == "early" and not evm:                    # still under its graduation price: the
        import grads                                             # first-hour dump has not been absorbed
        p0 = grads.birth_price(mint)
        if p0 and m.get("price_native") and m["price_native"] < FACTS["min_vs_graduation"] * p0:
            if not _trusted():
                return {"stage": "pool", "verdict": "SKIP", "reason": "below_graduation", "symbol": m.get("symbol"), **seen}
            held = "below_graduation"
    if (k := market.copycat(m, mint)) and k not in waived:       # a rug factory's name, or a bigger owner
        if k not in DEFERRABLE or not _trusted():
            return {"stage": "pool", "verdict": "SKIP", "reason": k, "symbol": m.get("symbol"), **seen}
        held = held or k

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

    try:                                                         # rug filter, free
        if evm:
            import facts_evm                                     # GoPlus: honeypot, taxes, mint, pause, LP lock
            token = facts_evm.report(mint, m)
        else:
            token = report(mint, m)
    except Exception as e:
        return {"stage": "facts", "verdict": "SKIP", "reason": f"facts failed: {e}",
                "symbol": m["symbol"], **seen}
    seen["dev"] = token.get("dev")
    if not evm:                          # RugCheck's view, logged for learn.py, never a kill by itself
        import rugcheck
        seen.update(rugcheck.fetch(mint) or {})
        # the chain read only knows PumpSwap pools: on Raydium, Meteora or a LaunchLab pool the LP stayed
        # "unverified" and the token was killed for it, whatever its pool really was. 4 of the 5 winners the
        # filter missed by Oct 28 died that way (Mimi +31,812%, STREAM, MUNK, Monaka). RugCheck reads those
        # pools: its locked share now stands in, and an unlocked pool is still a hard kill (lp_unlocked)
        lp_from_rugcheck(token, seen)
    seen.update(top10=token.get("top10_pct"), max_wallet=token.get("max_wallet_pct"), holders=token.get("holders"))
    try:                                 # the score of every token that got this far, killed or not: learn.py compares all
        sc0 = score(m, token)
        seen.update(score=sc0["score"], flags=" ".join(sc0["flags"]))
    except Exception:
        pass
    smart.snapshot(mint, token.get("all_owners") or token.get("wallets"))
    if (k := fact_kill(token, market.lane(m), waived)) and not _model_override(k, seen):
        return {"stage": "facts", "verdict": "SKIP", "reason": k,
                "symbol": m["symbol"] or token["symbol"], **seen}
    if k:
        seen["override"] = k                   # learn.py expects a profit despite this soft rule

    v = judge(token, m)
    sym = m["symbol"] or token["symbol"]
    sc = score(m, token)
    if sc["score"] >= MIN_SCORE and not evm:   # the deep read costs calls, and its sources are Solana's
        deep = deep_read(mint, token, skip=waived)
        seen.update(deep["logged"])
        if deep["kill"] and not _model_override(deep["kill"], seen):
            return {"stage": "deep", "verdict": "SKIP", "reason": deep["kill"], "symbol": sym, **seen,
                    "score": sc["score"]}
    usd, tier, sig = size.ticket({"score": sc["score"]}, m, token)
    if held:                                   # the pool soft kill held above: applied unless the model expects a profit
        exp = _expected(seen, held)
        if exp is None or exp < __import__("learn").OVERRIDE_PCT:
            return {"stage": "pool", "verdict": "SKIP", "reason": held, "symbol": sym, **seen,
                    **({"expected": round(exp, 1)} if exp is not None else {})}
        seen["override"] = held
    exp = _expected(seen, held or "")          # learn.py's view of a full pass: a loss expected -> not bought
    if exp is not None:
        seen["expected"] = round(exp, 1)
    return {**v, **seen, "ticket": usd, "tier": tier, "signals": sig, "symbol": sym, "price": m["price"], "liq_usd": m["liq_usd"], "url": m["url"],
            "score": sc["score"], "flags": " ".join(sc["flags"]),
            # the free check 14: two links you open yourself. latest posts, not "top"
            "x_ca": f"https://x.com/search?q={chains.split(mint)[1]}&f=live",
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


def lp_from_rugcheck(token: dict, seen: dict) -> bool:
    """RugCheck's locked LP share where the chain read could not see the pool (anything but PumpSwap)."""
    if token.get("lp_burned_pct") is not None or seen.get("rc_lp_locked") is None:
        return False
    try:
        token["lp_burned_pct"] = float(seen["rc_lp_locked"])
    except (TypeError, ValueError):
        return False
    seen["lp_source"] = "rugcheck"
    return True


def hot_skip(v: dict) -> str | None:
    """A pass whose ticket came out "strong" or "max" (2+ heat signals: high score, turnover, buyers ahead,
    smart wallets, X narrative) is not bought: those tickets lost money in every sample (config SIZING)."""
    if SIZING.get("skip_hot") and v.get("tier") in ("strong", "max"):
        return f"not bought: hot signals, already at the top of its hype ({', '.join(v.get('signals') or [])})"
    return None


def run(mint: str) -> dict:
    v = check(mint)
    v.update(market.sol_regime() or {})
    try:
        import majors                    # BTC, ETH, SOL against their averages: the market's regime
        v["dial"] = majors.dial_value()
    except Exception:
        v["dial"] = None
    log({"time": time.strftime("%Y-%m-%d %H:%M"), "mint": mint, **v})
    import dossier
    dossier.add(mint, "GARDE", v["verdict"], **{k: v.get(k) for k in (
        "stage", "reason", "symbol", "lane", "score", "flags", "tier", "signals", "ticket", "price", "liq_usd",
        "organic", "organic_vol", "dev_mints", "cluster_pct", "fresh_pct", "bundlers_pct", "insiders_pct",
        "snipers_pct", "factory_wallets")})
    enter = v["verdict"] == "BUY" or (v["verdict"] == "PASS" and PAPER and PAPER_BUY_ON_PASS)
    if enter and v.get("expected") is not None and v["expected"] < 0:
        v["action"] = f"not bought: the model expects {v['expected']:+.1f}% per trade"
        return v
    import coach                         # set only by TREND's self-review, when red regimes clearly lose
    gate = coach.get("meme_dial_gate")
    if enter and gate is not None and v.get("dial") is not None and v["dial"] < gate:
        v["action"] = f"not bought: regime dial {v['dial']:.2f} < {gate} (memecoins stand down)"
        return v
    import incidents                     # prudent after a slide: only the better setups (incidents.py)
    bar = incidents.strict_score()
    if enter and bar and (v.get("score") or 0) < bar:
        v["action"] = f"not bought: prudence after a drawdown, score {v.get('score')} < {bar}"
        return v
    import shadow
    if enter and (v.get("score") or 0) < MIN_SCORE and "low_score" not in shadow.waived() \
            and not (v.get("expected") is not None and v["expected"] >= __import__("learn").OVERRIDE_PCT):
        if PAPER and (v.get("score") or 0) >= SIZING["explore_min_score"]:
            equity = PAPER_BANKROLL_USD + book.realized()      # the explore tier: small, and logged apart
            usd = min(equity * SIZING["explore"] / 100, (v.get("liq_usd") or 0) * FACTS["max_ticket_share"], book.cash())
            v.update(ticket=round(max(usd, min(TICKET_USD, book.cash())), 2), tier="explore", signals=[])
        else:
            v["action"] = f"not bought: score {v['score']} < {MIN_SCORE} ({v.get('flags') or 'no flag'})"
            return v
    if enter and (why := hot_skip(v)):
        v["action"] = why
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
