# pending.py
# the waiting room between GARDE and the book. in ECHO_MODE = "gate", a PASS waits here until ECHO
# has read X: BUY -> the desk re-checks the pool and buys, SKIP -> dropped, no read in time -> dropped.
# data/x_queue.csv is the list ECHO works from; data/x_reads.csv is what ECHO writes back.
import csv, json, os, time
from config import DATA, ECHO_TIMEOUT_MIN, TICKET_USD, PAPER, ECHO_SILENT_MIN, ECHO_FALLBACK_SCORE
from market import pool, market_kill
import book

MOMENTUM_DROP_PCT = 25     # down this much between the PASS and ECHO's BUY -> not bought

PENDING = os.path.join(DATA, "pending.json")
X_QUEUE = os.path.join(DATA, "x_queue.csv")
X_READS = os.path.join(DATA, "x_reads.csv")


def load() -> dict:
    if not os.path.exists(PENDING):
        return {}
    with open(PENDING) as f:
        return json.load(f)


def save(p: dict):
    os.makedirs(DATA, exist_ok=True)
    tmp = PENDING + ".tmp"
    with open(tmp, "w") as f:
        json.dump(p, f, indent=2)
    os.replace(tmp, PENDING)


def add(mint: str, v: dict):
    p = load()
    p[mint] = {"symbol": v.get("symbol"), "since": time.time(), "score": v.get("score"),
               "flags": v.get("flags") or [], "price": v.get("price"), "url": v.get("url"),
               "shadow": bool(v.get("shadow"))}     # observe mode: already bought, the read is only recorded
    save(p)


def reads() -> dict:
    """ECHO's latest verdict per mint."""
    if not os.path.exists(X_READS):
        return {}
    with open(X_READS, newline="") as f:
        return {r["mint"]: r for r in csv.DictReader(f) if r.get("mint")}


def write_queue(p: dict, done: dict):
    """What ECHO still has to read, best score first."""
    rows = sorted(((m, v) for m, v in p.items() if m not in done), key=lambda kv: -(kv[1].get("score") or 0))
    os.makedirs(DATA, exist_ok=True)
    tmp = X_QUEUE + ".tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mint", "symbol", "score", "flags", "waiting_min", "x_by_ca", "x_by_ticker"])
        for m, v in rows:
            w.writerow([m, v["symbol"], v.get("score"), " ".join(v.get("flags") or []),
                        round((time.time() - v["since"]) / 60), f"https://x.com/search?q={m}&f=live",
                        f"https://x.com/search?q=%24{v['symbol']}&f=live"])
    os.replace(tmp, X_QUEUE)


def echo_silent(done: dict) -> bool:
    """ECHO wrote nothing for ECHO_SILENT_MIN minutes: its session is closed, asleep or out of usage."""
    last = max((r["time"] for r in done.values() if r.get("time")), default=None)
    if not last:
        return True
    return time.time() - time.mktime(time.strptime(last, "%Y-%m-%d %H:%M")) > ECHO_SILENT_MIN * 60


def mark_no_x(mint: str, sym: str):
    """Record in x_reads.csv that this one was bought on its score alone, so AUDIT keeps it apart."""
    new = not os.path.exists(X_READS)
    with open(X_READS, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "mint", "symbol", "verdict", "raison"])
        w.writerow([time.strftime("%Y-%m-%d %H:%M"), mint, sym, "NO_X", "ECHO silencieux : acheté sur la note seule"])


def decide() -> list[dict]:
    """Settle every pending PASS that ECHO has read, or that waited too long. Returns events."""
    p, done, out = load(), reads(), []
    silent = echo_silent(done)
    for mint, v in list(p.items()):
        x = done.get(mint)
        sym = v["symbol"]
        waited = time.time() - v["since"]
        if v.get("shadow"):
            if x or waited > ECHO_TIMEOUT_MIN * 60:
                del p[mint]
                if x:
                    out.append({"kind": "info", "symbol": sym, "mint": mint,
                                "text": f"${sym} X read after the buy: {x['verdict'].upper()} ({x.get('raison', '')[:70]})"})
                if x and x["verdict"].upper() == "SCAM" and mint in book.load():
                    # concrete scam evidence on X: out now, at the pool's price of this moment
                    m = pool(mint)
                    price = (m or {}).get("price") or 0
                    pnl = book.sell(mint, 1.0, price, "x_scam", (m or {}).get("liq_usd"))
                    out.append({"kind": "sell", "symbol": sym, "mint": mint, "pnl": pnl, "reason": "x_scam",
                                "pct": (price / v["price"] - 1) * 100 if price and v.get("price") else -100,
                                "closed": True, "text": f"{sym}: sold the rest on ECHO's SCAM read, pnl ${pnl:+.2f}"})
            continue
        if (not x and PAPER and silent and waited > ECHO_SILENT_MIN * 60
                and (v.get("score") or 0) >= ECHO_FALLBACK_SCORE):
            x = {"verdict": "BUY", "raison": "NO X, ECHO silent, score " + str(v.get("score"))}
            mark_no_x(mint, sym)
        if x and x["verdict"].upper() == "BUY":
            del p[mint]
            if (g := book.guard(mint)):
                out.append({"kind": "kill", "text": f"${sym} X said BUY but skipped (limits): {g}", "symbol": sym})
                continue
            m = pool(mint)                     # the price moved while ECHO read: buy at today's pool, not the PASS one
            if (k := market_kill(m)):
                out.append({"kind": "kill", "text": f"${sym} X said BUY but the pool changed: {k}", "symbol": sym})
                continue
            # momentum check: the wait for ECHO can be long. a token that fell hard or turned to
            # sellers in the meantime is no longer the token that passed
            p0 = v.get("price") or 0
            if p0 and m["price"] < p0 * (1 - MOMENTUM_DROP_PCT / 100):
                out.append({"kind": "kill", "text": f"${sym} X said BUY but price fell "
                                                    f"{(1 - m['price'] / p0) * 100:.0f}% since the PASS", "symbol": sym,
                            "reason": "momentum_lost"})
                continue
            if (m.get("sells_5m") or 0) > 2 * max(1, m.get("buys_5m") or 0) and m["price"] < p0:
                out.append({"kind": "kill", "text": f"${sym} X said BUY but sellers took over (5 min)",
                            "symbol": sym, "reason": "momentum_lost"})
                continue
            import size
            usd, tier, _ = size.ticket(v, m)
            book.open_position(mint, sym, m["price"], m["liq_usd"], usd=usd)
            out.append({"kind": "buy", "text": f"BUY ${usd:.0f} ({tier}) ${sym} @ {m['price']:.8g} "
                                               f"(score {v.get('score')}, X: {x.get('raison', '')[:60]})",
                        "symbol": sym, "mint": mint, "price": m["price"]})
        elif x:                                # SKIP or SCAM: not bought
            del p[mint]
            out.append({"kind": "kill", "text": f"${sym} dropped, X read: {x.get('raison', 'SKIP')[:90]}",
                        "symbol": sym, "mint": mint, "reason": "x_skip"})
        elif time.time() - v["since"] > ECHO_TIMEOUT_MIN * 60:
            del p[mint]
            out.append({"kind": "kill", "text": f"${sym} dropped: no X read within {ECHO_TIMEOUT_MIN} min "
                                                "(is the ECHO session open?)", "symbol": sym, "mint": mint,
                        "reason": "x_timeout"})
    save(p)
    write_queue(p, done)
    return out
