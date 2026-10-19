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
INBOX = os.path.join(DATA, "inbox.txt")      # CAs pasted in the dashboard, checked by GARDE
from events import emit, set_agent, agents as agent_state
from notify import post
import book, watch, scan, check, audit, report, pending, exitlab, ruggers, health, facts, smart, sources


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


_vigie_last = {"t": 0.0}


def vigie():
    _vigie_last["t"] = time.time()
    exits, marks = watch.watch()
    for e in exits:
        if e["kind"] == "error":
            emit("VIGIE", "error", e["text"])
            continue
        emit("VIGIE", "sell", e["text"], symbol=e["symbol"], mint=e["mint"], pnl=round(e["pnl"], 2),
             pct=round(e["pct"], 1), reason=e["reason"], closed=e.get("closed"))
        if e["reason"] in ("liquidity_pulled", "pool_gone", "x_scam"):   # x_skip is a doubt, not a rug
            n = smart.learn(e["mint"], -100)       # its holders now count one rug each, at once, not in 6 h
            if n:
                emit("VIGIE", "kill", f"${e['symbol']}: {n} holder wallets remembered as rug holders", symbol=e["symbol"])
        if e["reason"] in ("liquidity_pulled", "pool_gone") and (f := ruggers.funder_rugged(e["mint"], e["symbol"])):
            emit("VIGIE", "kill", f"${e['symbol']}: its holders' funder {f[:6]}… blacklisted, GARDE kills any "
                                  "token whose holders it funded", symbol=e["symbol"])
        if e["reason"] in ("liquidity_pulled", "pool_gone") and ruggers.add(
                ruggers.dev_of(e["mint"]), e["mint"], e["symbol"], e["reason"]):
            emit("VIGIE", "kill", f"${e['symbol']}: creator blacklisted ({e['reason']}), "
                                  "GARDE will kill every token it launches", symbol=e["symbol"])
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
    if scan.grad_error and "grads" not in down:
        emit("SCOUT", "error", scan.grad_error)
        down.add("grads")
    elif not scan.grad_error:
        down.discard("grads")
    if scan.gt_error and "gt" not in down:
        emit("SCOUT", "error", scan.gt_error)
        down.add("gt")
    elif not scan.gt_error:
        down.discard("gt")
    emit("SCOUT", "scan", f"{len(leads)} token(s) handed to GARDE: {scan.last_lanes['early']} launch(es), "
                          f"{scan.last_lanes['momentum']} in momentum ({len(scan.grads.recent())} graduates watched)")
    for mint in leads:
        garde(mint)
        # one process runs every agent: a batch of deep reads can take minutes, and open positions must
        # not go unwatched meanwhile. VIGIE gets its turn between two leads
        if time.time() - _vigie_last["t"] >= SCHEDULE["vigie_every_s"]:
            try:
                vigie()
            except Exception as e:
                emit("VIGIE", "error", f"between leads: {e}")
    return f"{len(leads)} lead(s) envoyé(s) à GARDE"


def garde(mint: str):
    """The 13 checks on one token, whoever found it: SCOUT, or you through the dashboard."""
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
        if reason == "no_holders" and facts.chain_holders_error and "holders" not in down:
            emit("GARDE", "error", "holders unreadable on chain, every such token is killed: "
                                   f"{facts.chain_holders_error} (is SOLANA_RPC set to Helius in .env?)")
            down.add("holders")
        elif reason == "no_holders" and not facts.chain_holders_error:
            down.discard("holders")
        verb = "skipped (limits)" if v["stage"] == "limits" else "killed"
        emit("GARDE", "kill", f"${sym} {verb}: {reason}", symbol=sym, mint=mint, reason=reason,
             stage=v["stage"])
    else:
        flags = v.get("flags") or ""
        emit("GARDE", "pass", f"${sym} passed every check, score {v.get('score')}" + (f" ({flags})" if flags else ""),
             symbol=sym, mint=mint, url=v.get("url"), x_ca=v.get("x_ca"), score=v.get("score"))
        action = v.get("action", "")
        if action.startswith("PAPER BUY"):
            usd = v.get("ticket") or TICKET_USD
            emit("GARDE", "buy", f"BUY ${usd:.0f} ({v.get('tier', 'base')}) ${sym} @ {v['price']:.8g}"
                                 + (f" — {', '.join(v['signals'])}" if v.get("signals") else ""), symbol=sym, mint=mint,
                 price=v["price"])
        elif action.startswith("waiting"):
            emit("ECHO", "x", f"${sym} queued for the X read (score {v.get('score')})", symbol=sym, mint=mint)
        elif action.startswith("not bought"):
            emit("GARDE", "kill", f"${sym} {action}", symbol=sym, mint=mint, reason="low_score")
        post(f"{v['verdict']} {sym} {v.get('url', '')}\nX by CA: {v.get('x_ca')}\n"
             f"X by ticker: {v.get('x_ticker')}\n{v.get('action', '')}")
    set_agent("GARDE", status="idle", msg=f"${sym}: {v['verdict']} {reason[:60]}",
              runs=(load_runs("GARDE") + 1))
    return v


def inbox():
    """CAs you pasted in the dashboard. Taken in one atomic move so none is checked twice."""
    if not os.path.exists(INBOX) or os.path.getsize(INBOX) == 0:
        return
    work = INBOX + ".work"
    os.replace(INBOX, work)
    with open(work) as f:
        mints = list(dict.fromkeys(line.strip() for line in f if line.strip()))
    os.remove(work)
    for mint in mints[:10]:
        emit("GARDE", "scan", f"check requested from the dashboard: {mint[:6]}…{mint[-4:]}", mint=mint)
        garde(mint)


def load_runs(name: str) -> int:
    return agent_state().get(name, {}).get("runs", 0)


def gate():
    """GARDE's second job: settle the PASSes waiting for ECHO. Buys only after an X BUY."""
    events = pending.decide()
    for e in events:
        agent = {"buy": "GARDE", "sell": "VIGIE"}.get(e["kind"], "ECHO")
        emit(agent, e["kind"], e["text"], **{k: v for k, v in e.items() if k not in ("kind", "text")})
        if e["kind"] == "buy":
            post(e["text"])
    n = len(pending.load())
    return f"{n} PASS en attente de X" if n else "attend les leads de SCOUT"


def auditor():
    rows = audit.audit()
    for r in rows:
        verdict = "good kill" if r["verdict"] == "SKIP" and r["change_pct"] <= audit.CRASH_PCT else \
                  "missed winner" if r["verdict"] == "SKIP" and r["change_pct"] >= 100 else "noted"
        emit("AUDIT", "audit", f"${r['symbol']} {r['verdict']} ({r['reason']}) -> "
                               f"{r['change_pct']:+.0f}% after {r['hours']:.0f}h: {verdict}",
             symbol=r["symbol"], pct=r["change_pct"])
    s = audit.summary()
    # the exit lab: replay every exit profile on every closed trade's real price path
    lab = exitlab.run()
    with open(os.path.join(DATA, "exitlab.json"), "w") as f:
        json.dump({**lab, "t": time.time()}, f)
    if lab["switched"]:
        best = next(r for r in lab["results"] if r["name"] == lab["switched"])
        emit("AUDIT", "info", f"exit profile switched to '{lab['switched']}': "
                              f"{best['pnl']:+.2f}$ on {best['n']} replayed trades, better on both halves")
    return (f"{s['killed']['crashed']}/{s['killed']['n']} éliminés ont chuté · labo : {lab['trades']} trade(s) rejoué(s), "
            f"profil « {lab['active']} »")


def plume():
    text = report.report()
    emit("PLUME", "report", text)
    post(text)
    return "rapport du soir publié"


def plume_morning():
    text = report.morning()
    emit("PLUME", "report", text)
    post(text)
    return "brief du matin publié"


def main():
    now = time.time()
    plan = {   # name: (job, seconds between runs or None for daily, next run)
        "VIGIE": [vigie, SCHEDULE["vigie_every_s"], now],
        "SCOUT": [scout, SCHEDULE["scout_every_min"] * 60, now + 5],
        "AUDIT": [auditor, SCHEDULE["audit_every_min"] * 60, now + 60],
        "GARDE": [gate, 30, now + 10],
    }
    reported_on = time.strftime("%Y-%m-%d") if time.strftime("%H:%M") >= SCHEDULE["report_at"] else None
    # started after 08:00: today's brief is not owed (it would describe the hours before the desk ran)
    briefed_on = time.strftime("%Y-%m-%d") if time.strftime("%H:%M") >= SCHEDULE["morning_at"] else None
    set_agent("GARDE", status="idle", msg="attend les leads de SCOUT")
    set_agent("PLUME", status="idle", msg=f"rapport à {SCHEDULE['report_at']}")
    emit("DESK", "info", f"Claude Bot up. {'PAPER' if PAPER else 'LIVE'} mode, bankroll ${PAPER_BANKROLL_USD}")
    post(f"CLAUDE BOT up. {'PAPER' if PAPER else 'LIVE'} mode, judge={JUDGE}, bankroll ${PAPER_BANKROLL_USD}. "
         f"VIGIE {SCHEDULE['vigie_every_s']}s, SCOUT {SCHEDULE['scout_every_min']}m, "
         f"AUDIT {SCHEDULE['audit_every_min']}m, report {SCHEDULE['report_at']}.")
    for problem in sources.probe():         # every outside source answers once, now
        emit("GARDE", "error", f"source en panne au démarrage : {problem[:160]}")
    if (t := health.since_last_run()):
        health.record(t, time.time(), "stopped")
    if (h := health.summary()):            # what the last 24 h looked like, said once at start
        emit("DESK", "error", "dernières 24 h : " + h)
    jobs = list(plan.items())
    last = time.time()
    while True:
        if time.time() - last > health.GAP_S:   # the loop sleeps 1 s: a long hole means the Mac slept
            health.record(last, time.time(), "sleep")
            fmt = lambda t: time.strftime("%H:%M", time.localtime(t))
            emit("DESK", "error", f"desk en pause {fmt(last)}→{fmt(time.time())} "
                                  f"({(time.time() - last) / 60:.0f} min) : le Mac a dormi ? lance health.py")
        last = time.time()
        due = [(name, p) for name, p in jobs if time.time() >= p[2]]
        if time.strftime("%H:%M") >= SCHEDULE["report_at"] and reported_on != time.strftime("%Y-%m-%d"):
            reported_on = time.strftime("%Y-%m-%d")
            due.append(("PLUME", [plume, None, 0]))
        if (SCHEDULE["morning_at"] <= time.strftime("%H:%M") < SCHEDULE["report_at"]
                and briefed_on != time.strftime("%Y-%m-%d")):
            briefed_on = time.strftime("%Y-%m-%d")
            due.append(("PLUME", [plume_morning, None, 0]))
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
        try:
            inbox()
        except Exception as e:
            emit("GARDE", "error", f"dashboard check failed: {e}")
        beat()
        last = time.time()
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        emit("DESK", "info", "Claude Bot stopped")
        post("CLAUDE BOT stopped.")
