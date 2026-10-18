# check.py
# one contract address in, one verdict out. limits, pool, facts, judge, in that order.
# the first one that says no ends it.
import csv, json, os, sys, time
from config import (DATA, LOG, JUDGE, MIN_CONFIDENCE, PAPER, PAPER_BUY_ON_PASS, TICKET_USD)
from rugcheck import report, fact_kill
from market import pool, market_kill
import book

FIELDS = ["time", "mint", "symbol", "stage", "verdict", "confidence", "reason"]


def log(row: dict):
    os.makedirs(DATA, exist_ok=True)
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k) for k in FIELDS})


def judge(token: dict, m: dict) -> dict:
    if JUDGE == "none":       # free desk: no X read. a PASS means "survived 13 checks", nothing more
        return {"stage": "judge", "verdict": "PASS",
                "reason": "passed 13 code checks, no X read (JUDGE=none)"}
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
    # in one fast call, so Rugcheck and its rate limit only see tokens worth a report
    try:
        m = pool(mint)                                           # pool, free
    except Exception as e:
        return {"stage": "pool", "verdict": "SKIP", "reason": f"dexscreener failed: {e}"}
    if (k := market_kill(m)):
        return {"stage": "pool", "verdict": "SKIP", "reason": k, "symbol": (m or {}).get("symbol")}

    try:
        token = report(mint)                                     # rug filter, free
    except Exception as e:
        return {"stage": "facts", "verdict": "SKIP", "reason": f"rugcheck failed: {e}",
                "symbol": m["symbol"]}
    if (k := fact_kill(token)):
        return {"stage": "facts", "verdict": "SKIP", "reason": k, "symbol": m["symbol"] or token["symbol"]}

    v = judge(token, m)
    sym = m["symbol"] or token["symbol"]
    return {**v, "symbol": sym, "price": m["price"], "liq_usd": m["liq_usd"], "url": m["url"],
            # the free check 14: two links you open yourself. latest posts, not "top"
            "x_ca": f"https://x.com/search?q={mint}&f=live",
            "x_ticker": f"https://x.com/search?q=%24{sym}&f=live"}


def run(mint: str) -> dict:
    v = check(mint)
    log({"time": time.strftime("%Y-%m-%d %H:%M"), "mint": mint, **v})
    enter = v["verdict"] == "BUY" or (v["verdict"] == "PASS" and PAPER and PAPER_BUY_ON_PASS)
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
