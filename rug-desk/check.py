# check.py
# one contract address in, one verdict out. limits, pool, facts, judge, in that order.
# the first one that says no ends it.
import csv, json, os, sys, time
from config import (DATA, LOG, JUDGE, MIN_CONFIDENCE, PAPER, PAPER_BUY_ON_PASS, TICKET_USD,
                    ECHO_MODE, MIN_SCORE)
from score import score
import pending
from facts import report, fact_kill
from market import pool, market_kill
import market
import book

# price and liq_usd at verdict time let AUDIT check later whether a kill or a pass was right
FIELDS = ["time", "mint", "symbol", "stage", "verdict", "confidence", "reason", "price", "liq_usd",
          "score", "flags", "sol_1h", "sol_24h", "age_min", "dev"]


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
    if (g := book.guard(mint)):                                  # limits, free
        return {"stage": "limits", "verdict": "SKIP", "reason": g}

    # pool first: same checks as the article, but most leads die here (thin or fresh pools)
    # in one fast call, so the slower fact sources only see tokens worth a report
    try:
        m = pool(mint)                                           # pool, free
    except Exception as e:
        return {"stage": "pool", "verdict": "SKIP", "reason": f"dexscreener failed: {e}"}
    seen = {"price": (m or {}).get("price"), "liq_usd": (m or {}).get("liq_usd"), "age_min": (m or {}).get("age_min")}
    if (k := market_kill(m)):
        return {"stage": "pool", "verdict": "SKIP", "reason": k, "symbol": (m or {}).get("symbol"), **seen}
    if market.copycat(m, mint):                                  # a bigger token owns this ticker
        return {"stage": "pool", "verdict": "SKIP", "reason": "copycat", "symbol": m.get("symbol"), **seen}

    try:
        token = report(mint, m)                                  # rug filter, free
    except Exception as e:
        return {"stage": "facts", "verdict": "SKIP", "reason": f"facts failed: {e}",
                "symbol": m["symbol"], **seen}
    seen["dev"] = token.get("dev")
    if (k := fact_kill(token)):
        return {"stage": "facts", "verdict": "SKIP", "reason": k,
                "symbol": m["symbol"] or token["symbol"], **seen}

    v = judge(token, m)
    sym = m["symbol"] or token["symbol"]
    sc = score(m, token)
    return {**v, **seen, "symbol": sym, "price": m["price"], "liq_usd": m["liq_usd"], "url": m["url"],
            "score": sc["score"], "flags": " ".join(sc["flags"]),
            # the free check 14: two links you open yourself. latest posts, not "top"
            "x_ca": f"https://x.com/search?q={mint}&f=live",
            "x_ticker": f"https://x.com/search?q=%24{sym}&f=live"}


def run(mint: str) -> dict:
    v = check(mint)
    v.update(market.sol_regime() or {})
    log({"time": time.strftime("%Y-%m-%d %H:%M"), "mint": mint, **v})
    enter = v["verdict"] == "BUY" or (v["verdict"] == "PASS" and PAPER and PAPER_BUY_ON_PASS)
    if enter and (v.get("score") or 0) < MIN_SCORE:
        v["action"] = f"not bought: score {v['score']} < {MIN_SCORE} ({v.get('flags') or 'no flag'})"
        return v
    if enter and PAPER and v["verdict"] == "PASS" and ECHO_MODE == "gate":
        pending.add(mint, {**v, "flags": (v.get("flags") or "").split()})
        v["action"] = f"waiting for ECHO's X read (score {v['score']})"
        return v
    if enter and PAPER:
        book.open_position(mint, v["symbol"], v["price"], v["liq_usd"])
        v["action"] = f"PAPER BUY ${TICKET_USD} at {v['price']}"
    elif v["verdict"] in ("BUY", "PASS") and not PAPER:
        pre = "" if v["verdict"] == "BUY" else "no X read: search the ticker and CA on X yourself first. "
        v["action"] = (f"APPROVAL NEEDED: {pre}buy ${TICKET_USD} of {v['symbol']} in your own wallet, "
                       f"then run: python book.py add {mint} {TICKET_USD} <fill price> {v['liq_usd']}")
    return v


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1].strip()), indent=2))
