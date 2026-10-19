# agents.py
# the desk as a team. each agent has one job, its own clock, and its own status on the dashboard.
#   VIGIE  every 20 s   prices every open position, fires exits, logs the balance
#   SCOUT  every 10 min pulls fresh leads and hands each one to GARDE
#   GARDE  per lead     limits, pool and contract checks: the 13 ways a token dies
#   AUDIT  every 30 min re-prices old verdicts: did the filter kill crashers or winners?
#   PLUME  daily        the evening report
#   ECHO   outside      the Claude-in-Chrome X reader (its own session); the dashboard tracks it
# one process, so no two agents ever write the same file at the same time.
import json, os, time, traceback
from config import SCHEDULE, PAPER, JUDGE, DATA, EQUITY, PAPER_BANKROLL_USD, TICKET_USD

MARKS = os.path.join(DATA, "marks.json")
from events import emit, set_agent, agents as agent_state
from notify import post
import book, watch, scan, check, audit, report


def beat():
    """dashboard.py reads this to show whether the desk is alive."""
    os.makedirs(DATA, exist_ok=True)
    tmp = os.path.join(DATA, "heartbeat.json.tmp")
    with open(tmp, "w") as f:
        json.dump({"time": time.time(), "paper": PAPER, "judge": JUDGE}, f)
    os.replace(tmp, os.path.join(DATA, "heartbeat.json"))


def log_equity(marks: dict):
    """One balance point per VIGIE tick: this is what makes the dashboard chart move."""
    b = book.load()
    unrealized = sum(p["qty"] * (marks.get(m, p["entry"]) - p["entry"]) for m, p in b.items())
    realized = book.realized()
    new = not os.path.exists(EQUITY)
    with open(EQUITY, "a") as f:
        if new:
            f.write("t,balance,realized,unrealized,open\n")
        f.write(f"{time.time():.0f},{PAPER_BANKROLL_USD + realized + unrealized:.4f},"
                f"{realized:.4f},{unrealized:.4f},{len(b)}\n")


def vigie():
    exits, marks = watch.watch()
    for e in exits:
        if e["kind"] == "error":
            emit("VIGIE", "error", e["text"])
            continue
        emit("VIGIE", "sell", e["text"], symbol=e["symbol"], mint=e["mint"], pnl=round(e["pnl"], 2),
             pct=round(e["pct"], 1), reason=e["reason"])
        post(e["text"])
    log_equity(marks)
    tmp = MARKS + ".tmp"        # live prices for the dashboard, so it never calls an API itself
    with open(tmp, "w") as f:
        json.dump({"t": time.time(), "marks": marks}, f)
    os.replace(tmp, MARKS)
    n = len(book.load())
    return f"{n} position(s) surveillée(s)" + (f", {len(exits)} sortie(s)" if exits else "")


down = set()        # sources already reported down, so each outage is said once


def scout():
    try:
        leads = scan.leads()
        down.discard("leads")
    except Exception as e:
        if "leads" not in down:
            emit("SCOUT", "error", f"DexScreener leads down: {e}")
            down.add("leads")
        raise
    emit("SCOUT", "scan", f"{len(leads)} token(s) with a real pool handed to GARDE")
    for mint in leads:
        set_agent("GARDE", status="work", msg=f"vérifie {mint[:6]}…")
        v = check.run(mint)
        sym, reason = v.get("symbol") or mint[:6], v.get("reason") or ""
        src = next((s for s in ("facts", "dexscreener", "grok") if reason.startswith(f"{s} failed")), None)
        if src:
            if src not in down:
                emit("GARDE", "error", f"{src} down, its tokens are skipped: {reason[:160]}")
                down.add(src)
        elif v["verdict"] == "SKIP":
            down.discard("facts"); down.discard("dexscreener")
            emit("GARDE", "kill", f"${sym} killed: {reason}", symbol=sym, mint=mint, reason=reason,
                 stage=v["stage"])
        else:
            emit("GARDE", "pass", f"${sym} passed every code check", symbol=sym, mint=mint,
                 url=v.get("url"), x_ca=v.get("x_ca"))
            if v.get("action", "").startswith("PAPER BUY"):
                emit("GARDE", "buy", f"BUY ${TICKET_USD} ${sym} @ {v['price']:.8g}", symbol=sym, mint=mint,
                     price=v["price"])
            post(f"{v['verdict']} {sym} {v.get('url', '')}\nX by CA: {v.get('x_ca')}\n"
                 f"X by ticker: {v.get('x_ticker')}\n{v.get('action', '')}")
        set_agent("GARDE", status="idle", msg=f"${sym}: {v['verdict']} {reason[:60]}",
                  runs=(load_runs("GARDE") + 1))
    return f"{len(leads)} lead(s) envoyé(s) à GARDE"


def load_runs(name: str) -> int:
    return agent_state().get(name, {}).get("runs", 0)


def auditor():
    rows = audit.audit()
    for r in rows:
        verdict = "good kill" if r["verdict"] == "SKIP" and r["change_pct"] <= audit.CRASH_PCT else \
                  "missed winner" if r["verdict"] == "SKIP" and r["change_pct"] >= 100 else "noted"
        emit("AUDIT", "audit", f"${r['symbol']} {r['verdict']} ({r['reason']}) -> "
                               f"{r['change_pct']:+.0f}% after {r['hours']:.0f}h: {verdict}",
             symbol=r["symbol"], pct=r["change_pct"])
    s = audit.summary()
    return f"{s['killed']['crashed']}/{s['killed']['n']} éliminés ont chuté, {len(rows)} nouveau(x)"


def plume():
    text = report.report()
    emit("PLUME", "report", text)
    post(text)
    return "rapport du soir publié"


def main():
    now = time.time()
    plan = {   # name: (job, seconds between runs or None for daily, next run)
        "VIGIE": [vigie, SCHEDULE["vigie_every_s"], now],
        "SCOUT": [scout, SCHEDULE["scout_every_min"] * 60, now + 5],
        "AUDIT": [auditor, SCHEDULE["audit_every_min"] * 60, now + 60],
    }
    reported_on = time.strftime("%Y-%m-%d") if time.strftime("%H:%M") >= SCHEDULE["report_at"] else None
    set_agent("GARDE", status="idle", msg="attend les leads de SCOUT")
    set_agent("PLUME", status="idle", msg=f"rapport à {SCHEDULE['report_at']}")
    emit("DESK", "info", f"Claude Bot up. {'PAPER' if PAPER else 'LIVE'} mode, bankroll ${PAPER_BANKROLL_USD}")
    post(f"CLAUDE BOT up. {'PAPER' if PAPER else 'LIVE'} mode, judge={JUDGE}, bankroll ${PAPER_BANKROLL_USD}. "
         f"VIGIE {SCHEDULE['vigie_every_s']}s, SCOUT {SCHEDULE['scout_every_min']}m, "
         f"AUDIT {SCHEDULE['audit_every_min']}m, report {SCHEDULE['report_at']}.")
    jobs = list(plan.items())
    while True:
        due = [(name, p) for name, p in jobs if time.time() >= p[2]]
        if time.strftime("%H:%M") >= SCHEDULE["report_at"] and reported_on != time.strftime("%Y-%m-%d"):
            reported_on = time.strftime("%Y-%m-%d")
            due.append(("PLUME", [plume, None, 0]))
        for name, p in due:
            job, every = p[0], p[1]
            set_agent(name, status="work", msg="au travail…")
            try:
                msg = job()
                set_agent(name, status="idle", msg=msg, runs=load_runs(name) + 1,
                          next=time.time() + every if every else None)
            except Exception as e:
                set_agent(name, status="error", msg=str(e)[:160],
                          errors=agent_state().get(name, {}).get("errors", 0) + 1,
                          next=time.time() + every if every else None)
                if name != "SCOUT":     # SCOUT already said which source is down
                    emit(name, "error", traceback.format_exc(limit=2)[-300:])
            if every:
                p[2] = time.time() + every
        beat()
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        emit("DESK", "info", "Claude Bot stopped")
        post("CLAUDE BOT stopped.")
