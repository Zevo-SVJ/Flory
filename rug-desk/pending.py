# pending.py
# the waiting room between GARDE and the book. in ECHO_MODE = "gate", a PASS waits here until ECHO
# has read X: BUY -> the desk re-checks the pool and buys, SKIP -> dropped, no read in time -> dropped.
# data/x_queue.csv is the list ECHO works from; data/x_reads.csv is what ECHO writes back.
import atomic
import csv, json, os, time
from config import DATA, ECHO_TIMEOUT_MIN, TICKET_USD, PAPER, ECHO_SILENT_MIN, ECHO_FALLBACK_SCORE
from market import pool, market_kill
import book, dossier

MOMENTUM_DROP_PCT = 25     # down this much between the PASS and ECHO's BUY -> not bought

PENDING = os.path.join(DATA, "pending.json")
X_QUEUE = os.path.join(DATA, "x_queue.csv")
X_READS = os.path.join(DATA, "x_reads.csv")
X_WATCH = os.path.join(DATA, "x_watch.csv")
RECHECK_MIN = 15           # an open position is read again on X every 15 min: news, accusations, attention fading
SILENT_ALARM_MIN = 30      # positions open and no X read for this long: ECHO's loop is down, the desk says so


def load() -> dict:
    if not os.path.exists(PENDING):
        return {}
    with open(PENDING) as f:
        return json.load(f)


def save(p: dict):
    os.makedirs(DATA, exist_ok=True)
    tmp = atomic.tmp(PENDING)
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
    tmp = atomic.tmp(X_QUEUE)
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mint", "symbol", "score", "flags", "waiting_min", "x_by_ca", "x_by_ticker", "contexte"])
        for m, v in rows:
            w.writerow([m, v["symbol"], v.get("score"), " ".join(v.get("flags") or []),
                        round((time.time() - v["since"]) / 60), f"https://x.com/search?q={m}&f=live",
                        f"https://x.com/search?q=%24{v['symbol']}&f=live", dossier.brief(m)])
    os.replace(tmp, X_QUEUE)


def last_read_min(mint: str, done: dict) -> float | None:
    x = done.get(mint)
    if not x or not x.get("time"):
        return None
    try:
        return (time.time() - time.mktime(time.strptime(x["time"], "%Y-%m-%d %H:%M"))) / 60
    except ValueError:
        return None


def write_watch(done: dict):
    """ECHO's standing watch: every open position, with how long since X was last read for it.
    due = never read, or read more than RECHECK_MIN ago. ECHO re-reads those first (ECHO.md)."""
    import chains
    try:
        with open(os.path.join(DATA, "marks.json")) as f:
            marks = json.load(f).get("marks", {})
    except (OSError, ValueError):
        marks = {}
    import incidents
    u = incidents.urgent()
    since_urgent = (time.time() - u["t"]) / 60 if u.get("t") else None
    rows = []
    for m, pos in book.load().items():
        last = last_read_min(m, done)
        if since_urgent is not None and m in u.get("mints", []) and last is not None and last > since_urgent:
            last = None                        # read before the incident: due now
        px = marks.get(m)
        chain, addr = chains.split(m)
        rows.append([m, pos["symbol"], chain, round((time.time() - pos["opened"]) / 60),
                     f"{(px / pos['entry'] - 1) * 100:+.0f}" if px else "",
                     "" if last is None else round(last), "oui" if last is None or last >= RECHECK_MIN else "non",
                     (done.get(m) or {}).get("verdict", ""),
                     f"https://x.com/search?q={addr}&f=live", f"https://x.com/search?q=%24{pos['symbol']}&f=live",
                     chains.link(m), dossier.brief(m)])
    rows.sort(key=lambda r: (r[6] != "oui", -(r[5] if r[5] != "" else 10**6)))
    os.makedirs(DATA, exist_ok=True)
    tmp = atomic.tmp(X_WATCH)
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mint", "symbol", "chain", "held_min", "pct", "last_x_min", "due", "last_verdict",
                    "x_by_ca", "x_by_ticker", "chart", "contexte"])
        w.writerows(rows)
    os.replace(tmp, X_WATCH)


def echo_gap_min(done: dict | None = None) -> float | None:
    """Minutes since ECHO last wrote anything, None if it never did."""
    done = reads() if done is None else done
    ages = [a for a in (last_read_min(m, done) for m in done) if a is not None]
    return min(ages) if ages else None


SELL_ON = ("SCAM",)       # ECHO verdicts that close an open position. SKIP is recorded and measured only,
                          # unless ECHO's self-review proves its SKIPs foresee drops (coach echo_skip_sells)


def sell_on() -> tuple:
    import coach
    return ("SCAM", "SKIP") if coach.get("echo_skip_sells") else SELL_ON


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
                    dossier.add(mint, "ECHO", x["verdict"].upper(), raison=x.get("raison"))
                if x:
                    out.append({"kind": "info", "symbol": sym, "mint": mint,
                                "text": f"${sym} X read after the buy: {x['verdict'].upper()} ({x.get('raison', '')[:70]})"})
                if x and x["verdict"].upper() in sell_on() and mint in book.load():
                    # only a SCAM closes the position (concrete evidence: a named rug accusation, a bundle).
                    # a SKIP did too until Oct 19 evening: ECHO said SKIP to nearly everything and BUY to none,
                    # so every buy was sold 1-12 min later and paid the round trip (8 of 8 trades, -9.3% each)
                    m = pool(mint)
                    price = (m or {}).get("price") or 0
                    why = "x_" + x["verdict"].lower()
                    pnl = book.sell(mint, 1.0, price, why, (m or {}).get("liq_usd"))
                    out.append({"kind": "sell", "symbol": sym, "mint": mint, "pnl": pnl, "reason": why,
                                "pct": (price / v["price"] - 1) * 100 if price and v.get("price") else -100,
                                "closed": True, "text": f"{sym}: sold the rest on ECHO's {x['verdict'].upper()} read, pnl ${pnl:+.2f}"})
            continue
        if (not x and PAPER and silent and waited > ECHO_SILENT_MIN * 60
                and (v.get("score") or 0) >= ECHO_FALLBACK_SCORE):
            x = {"verdict": "BUY", "raison": "NO X, ECHO silent, score " + str(v.get("score"))}
            mark_no_x(mint, sym)
        if x and x["verdict"].upper() in ("BUY", "SKIP", "SCAM") and not x.get("raison", "").startswith("NO X"):
            dossier.add(mint, "ECHO", x["verdict"].upper(), raison=x.get("raison"))
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
    write_watch(done)
    # any open position ECHO read as SCAM, whenever that read came: out at the pool's price of this moment
    for mint, pos in book.load().items():
        x = done.get(mint)
        if not x or x["verdict"].upper() not in sell_on() or mint in p:
            continue
        m = pool(mint)
        price = (m or {}).get("price") or 0
        if not price:
            continue                          # no price now: VIGIE's chain read decides, not a blind sale at 0
        why = "x_" + x["verdict"].lower()
        pnl = book.sell(mint, 1.0, price, why, (m or {}).get("liq_usd"))
        dossier.add(mint, "VIGIE", "vente", reason=why, pct=round((price / pos["entry"] - 1) * 100, 1), pnl=round(pnl, 2))
        out.append({"kind": "sell", "symbol": pos["symbol"], "mint": mint, "pnl": pnl, "reason": why, "closed": True,
                    "pct": (price / pos["entry"] - 1) * 100,
                    "text": f"{pos['symbol']}: sold on ECHO's {x['verdict'].upper()} read, pnl ${pnl:+.2f}"})
    return out
