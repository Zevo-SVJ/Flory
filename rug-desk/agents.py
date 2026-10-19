# agents.py
# the desk as a team. a job is an agent only when it needs its own clock, its own failure domain or its
# own tools; everything else is a function. five agents pass that bar:
#   VIGIE  own thread, 20 s   the only latency-critical job: prices positions on chain, fires exits.
#                              it never waits for the others, and it watches the main loop
#   SCOUT  every 3 min        cheap and broad: every source, the funnel's first cut
#   GARDE  per lead           expensive and deep: the checks, the deep read, the buy (cost asymmetry
#                              with SCOUT is why they are two). also settles ECHO's reads every 30 s
#   ECHO   own Claude session the only job that needs a model and a browser (X)
#   (GARDE also answers on Telegram, tgbot.py, read-only, when TELEGRAM_BOT_TOKEN is in .env)
#   AUDIT  every 30 min       the slow loop: re-prices verdicts, learns wallets, writes the reports, and
#                              every 6 h starts the cumulative backtest in a child process
# one writer at a time on the book (book.LOCK) and on the event log (events._LOCK).
import atomic
import json, os, threading, time, traceback
from config import SCHEDULE, PAPER, JUDGE, DATA, EQUITY, PAPER_BANKROLL_USD, TICKET_USD, FACTS

MARKS = os.path.join(DATA, "marks.json")
INBOX = os.path.join(DATA, "inbox.txt")      # CAs pasted in the dashboard, checked by GARDE
from events import emit, set_agent, agents as agent_state
from notify import post
import book, watch, scan, check, audit, report, pending, exitlab, ruggers, health, facts, smart, sources, market


def beat():
    """dashboard.py reads this to show whether the desk is alive."""
    os.makedirs(DATA, exist_ok=True)
    tmp = atomic.tmp(os.path.join(DATA, "heartbeat.json"))
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
        if e["reason"] in RUG_EXITS:
            on_rug(e["mint"], e["symbol"], e["reason"])
        post(e["text"])
    log_equity(marks)
    tmp = atomic.tmp(MARKS)        # live prices for the dashboard, so it never calls an API itself
    with open(tmp, "w") as f:
        json.dump({"t": time.time(), "marks": marks}, f)
    os.replace(tmp, MARKS)
    n = len(book.load())
    return f"{n} position(s) surveillée(s)" + (f", {len(exits)} sortie(s)" if exits else "")


RUG_EXITS = ("liquidity_pulled", "pool_gone", "x_scam")     # x_skip is a doubt, not a rug
CONTAGION_SHARED = 5          # open positions sharing this many holder wallets with a rug are sold


def on_rug(mint: str, symbol: str, reason: str):
    """Everything the team does when a position rugs, whoever saw it (VIGIE on chain, ECHO on X):
    remember its holders, blacklist its creator and its cluster funder, and sell any other open position
    the same hands are in. a factory runs several tokens at once with one wallet pool (Oct 19)."""
    n = smart.learn(mint, -100)                # its holders count one rug each, at once, not in 6 h
    if n:
        emit("VIGIE", "kill", f"${symbol}: {n} holder wallets remembered as rug holders", symbol=symbol)
    funder = ruggers.funder_of(mint)
    if reason != "x_scam" and ruggers.funder_rugged(mint, symbol):
        emit("VIGIE", "kill", f"${symbol}: its holders' funder {funder[:6]}… blacklisted, GARDE kills any "
                              "token whose holders it funded", symbol=symbol)
    if reason != "x_scam" and ruggers.add(ruggers.dev_of(mint), mint, symbol, reason):
        emit("VIGIE", "kill", f"${symbol}: creator blacklisted ({reason}), GARDE will kill every token it launches",
             symbol=symbol)
    rug_holders = set(smart.holders(mint))
    for other, pos in book.load().items():
        if other == mint:
            continue
        shared = len(rug_holders & set(smart.holders(other)))
        same_funder = bool(funder) and ruggers.funder_of(other) == funder
        if shared < CONTAGION_SHARED and not same_funder:
            continue
        m = market.pool(other)
        price = (m or {}).get("price") or 0
        if not price:
            continue
        pnl = book.sell(other, 1.0, price, "contagion", (m or {}).get("liq_usd"))
        why = f"{shared} holders en commun" if shared >= CONTAGION_SHARED else "même financeur"
        emit("VIGIE", "sell", f"{pos['symbol']}: sold on contagion from ${symbol} ({why}), pnl ${pnl:+.2f}",
             symbol=pos["symbol"], mint=other, pnl=round(pnl, 2), pct=round((price / pos["entry"] - 1) * 100, 1),
             reason="contagion", closed=True)
        import dossier
        dossier.add(other, "VIGIE", "vente", reason="contagion", source=f"${symbol} ({why})", pnl=round(pnl, 2))


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
    born = scan.grads.load()["mints"].values()
    young = sum(1 for t in born if time.time() - t < FACTS["min_age_min"] * 60)
    import chains
    per = {}
    for m in leads:
        per[chains.split(m)[0]] = per.get(chains.split(m)[0], 0) + 1
    where = (" [" + ", ".join(f"{c} {n}" for c, n in sorted(per.items(), key=lambda kv: -kv[1])) + "]") if per else ""
    if evmnew_err := __import__("evmnew").error:
        if "evmnew" not in down:
            emit("SCOUT", "error", evmnew_err)
            down.add("evmnew")
    else:
        down.discard("evmnew")
    emit("SCOUT", "scan", f"{len(leads)} token(s) handed to GARDE{where}: {scan.last_lanes['early']} launch(es), "
                          f"{scan.last_lanes['momentum']} in momentum ({len(born)} graduates watched, "
                          f"{young} still in their first {FACTS['min_age_min']} min)")
    set_agent("SCOUT", funnel=scan.last_funnel)
    for mint in leads:
        garde(mint)
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
        import shadow                   # bought in shadow: VIGIE follows it 6 h, AUDIT scores the kill
        followed = shadow.note(mint, v)
        emit("GARDE", "kill", f"${sym} {verb}: {reason}" + (" · suivi 6 h en fantôme" if followed else ""),
             symbol=sym, mint=mint, reason=reason, stage=v["stage"])
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
            import shadow
            followed = shadow.note(mint, v)
            emit("GARDE", "kill", f"${sym} {action}" + (" · suivi 6 h en fantôme" if followed else ""),
                 symbol=sym, mint=mint, reason="low_score")
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
        if mint.lower().startswith("0x") and ":" not in mint:      # an EVM address: find its chain first
            found = market.locate(mint)
            if not found:
                emit("GARDE", "kill", f"{mint[:8]}…: aucun pool sur une chaîne suivie", mint=mint, reason="no_pool")
                continue
            mint = found
        emit("GARDE", "scan", f"check requested from the dashboard: {mint[:14]}…{mint[-4:]}", mint=mint)
        garde(mint)


def load_runs(name: str) -> int:
    return agent_state().get(name, {}).get("runs", 0)


def gate():
    """GARDE's second job: settle the PASSes waiting for ECHO. Buys only after an X BUY."""
    events = pending.decide()
    for e in events:
        agent = {"buy": "GARDE", "sell": "VIGIE"}.get(e["kind"], "ECHO")
        emit(agent, e["kind"], e["text"], **{k: v for k, v in e.items() if k not in ("kind", "text")})
        if e["kind"] == "sell" and e.get("reason") in RUG_EXITS:
            on_rug(e["mint"], e["symbol"], e["reason"])
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
    import shadow                         # a soft kill the shadow book proved costly is lifted, said once
    shadow._waived["t"] = 0
    now_waived = shadow.waived()
    for reason in sorted(now_waived ^ _lifted):
        d = next((x for x in (shadow.results()["reasons"]) if x["reason"] == reason), {})
        emit("AUDIT", "info", (f"GARDE n'applique plus « {reason} » : ses éliminations auraient rapporté "
                               f"{d.get('mean', 0):+.1f} % par trade sur {d.get('n', 0)} trades fantômes")
             if reason in now_waived else f"GARDE applique de nouveau « {reason} »")
    _lifted.clear(); _lifted.update(now_waived)
    bt = backtest_kick()
    return (f"{s['killed']['crashed']}/{s['killed']['n']} éliminés ont chuté · labo : {lab['trades']} trade(s) rejoué(s), "
            f"profil « {lab['active']} »" + (f" · {bt}" if bt else ""))


_bt = {"proc": None}
_lifted = set()          # soft kills currently lifted by the shadow book, to say each change once


def backtest_kick() -> str | None:
    """The cumulative backtest, run by AUDIT every SCHEDULE['backtest_every_h'] in a child process: a replay
    reads the chain for minutes and must never hold up the agents. says once when a batch has finished."""
    import subprocess, sys, backtest
    st = {}
    try:
        with open(backtest.STATE) as f:
            st = json.load(f)
    except (OSError, ValueError):
        pass
    # said once per finished run, even one started before a restart (the mark is kept in the state file)
    if st.get("finished", 0) > st.get("announced", 0):
        st["announced"] = st["finished"]
        tmp = atomic.tmp(backtest.STATE)
        with open(tmp, "w") as f:
            json.dump(st, f)
        os.replace(tmp, backtest.STATE)
        rules = (st.get("card") or {}).get("rules") or {}
        parts = [f"{k} n={v['n']} {v['mean']:+.1f} % [{v['ci95'][0]:+.0f}, {v['ci95'][1]:+.0f}]" for k, v in rules.items()]
        emit("AUDIT", "info", f"backtest : +{st.get('early_added', 0)} graduation(s), +{st.get('momentum_added', 0)} "
                              f"momentum · " + " · ".join(parts)
             + (f" · {st['early_error']}" if st.get("early_error") else ""))
    if _bt["proc"] is not None and _bt["proc"].poll() is None:
        return "backtest en cours"
    if backtest.alive(st):
        return "backtest en cours"
    # a run killed before it finished (the desk was restarted) is started again, not waited 6 h for
    finished_last = st.get("finished", 0) >= st.get("started", 0)
    if finished_last and time.time() - st.get("started", 0) < SCHEDULE["backtest_every_h"] * 3600:
        return None
    if not finished_last and time.time() - st.get("started", 0) < 600:
        return None             # just launched: its child may not have written its pid yet
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(DATA, "backtest.log"), "a") as log:
        _bt["proc"] = subprocess.Popen([sys.executable, os.path.join(here, "backtest.py"), "--accumulate"],
                                       cwd=here, stdout=log, stderr=subprocess.STDOUT)
    tmp = atomic.tmp(backtest.STATE)
    with open(tmp, "w") as f:     # started now: a restart does not launch it twice
        json.dump({**st, "started": time.time()}, f)
    os.replace(tmp, backtest.STATE)
    emit("AUDIT", "info", "backtest lancé en arrière-plan : nouvelles graduations et momentum rejoués")
    return "backtest lancé"


def plume():
    """The evening report. AUDIT writes it: a scheduled summary is a job, not an agent of its own.
    on the review day (edge.BILAN_ON) and once after it if the desk was off that evening, the decision
    report too, saved in data/ and sent to Telegram."""
    text = report.report()
    emit("AUDIT", "report", text)
    post(text)
    import edge, glob
    done = [f for f in glob.glob(os.path.join(DATA, "rapport_decision_*.txt")) if f[-14:-4] >= edge.BILAN_ON]
    if time.strftime("%Y-%m-%d") >= edge.BILAN_ON and not done:
        big = report.weekly()
        emit("AUDIT", "report", big)
        post(big)
        return "rapport du soir et rapport de décision publiés"
    return "rapport du soir publié"


def plume_morning():
    text = report.morning()
    emit("AUDIT", "report", text)
    post(text)
    return "brief du matin publié"


def run_job(name: str, job, every: float | None):
    """One turn of one agent: its status before and after, its errors counted, never fatal."""
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


def vigie_loop(stop: threading.Event):
    """VIGIE on its own clock. Every other agent waits on the network (a deep read can take a minute);
    an open position must be re-priced every 20 s whatever they do. It also watches the main loop."""
    every = SCHEDULE["vigie_every_s"]
    warned = False
    while not stop.is_set():
        t0 = time.time()
        run_job("VIGIE", vigie, every)
        hb = _main_beat["t"]
        if hb and time.time() - hb > 300 and not warned:   # the main loop has not turned in 5 min
            emit("DESK", "error", "la boucle principale (SCOUT, GARDE, AUDIT) est bloquée depuis 5 min : "
                                  "VIGIE continue de surveiller les positions")
            warned = True
        elif hb and time.time() - hb < 60:
            warned = False
        stop.wait(max(1.0, every - (time.time() - t0)))


_main_beat = {"t": 0.0}


def start_vigie(stop: threading.Event) -> threading.Thread:
    th = threading.Thread(target=vigie_loop, args=(stop,), name="VIGIE", daemon=True)
    th.start()
    return th


def main():
    now = time.time()
    plan = {   # name: (job, seconds between runs or None for daily, next run). VIGIE has its own thread
        "SCOUT": [scout, SCHEDULE["scout_every_min"] * 60, now + 5],
        "AUDIT": [auditor, SCHEDULE["audit_every_min"] * 60, now + 60],
        "GARDE": [gate, 30, now + 10],
    }
    reported_on = time.strftime("%Y-%m-%d") if time.strftime("%H:%M") >= SCHEDULE["report_at"] else None
    # started after 08:00: today's brief is not owed (it would describe the hours before the desk ran)
    briefed_on = time.strftime("%Y-%m-%d") if time.strftime("%H:%M") >= SCHEDULE["morning_at"] else None
    set_agent("GARDE", status="idle", msg="attend les leads de SCOUT")
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
    stop = threading.Event()
    vigie_thread = start_vigie(stop)
    import tgbot                            # GARDE as a product, when a bot token is in .env
    if tgbot.start(stop):
        emit("DESK", "info", "bot Telegram anti-rug actif : il répond à tout CA qu'on lui envoie")
    last = time.time()
    while True:
        _main_beat["t"] = time.time()
        if not vigie_thread.is_alive():         # VIGIE must never stay down: restart it, say it once
            emit("VIGIE", "error", "le fil de VIGIE s'était arrêté : relancé")
            vigie_thread = start_vigie(stop)
        if time.time() - last > health.GAP_S:   # the loop sleeps 1 s: a long hole means the Mac slept
            health.record(last, time.time(), "sleep")
            fmt = lambda t: time.strftime("%H:%M", time.localtime(t))
            emit("DESK", "error", f"desk en pause {fmt(last)}→{fmt(time.time())} "
                                  f"({(time.time() - last) / 60:.0f} min) : le Mac a dormi ? lance health.py")
        last = time.time()
        due = [(name, p) for name, p in jobs if time.time() >= p[2]]
        if time.strftime("%H:%M") >= SCHEDULE["report_at"] and reported_on != time.strftime("%Y-%m-%d"):
            reported_on = time.strftime("%Y-%m-%d")
            due.append(("AUDIT", [plume, None, 0]))
        if (SCHEDULE["morning_at"] <= time.strftime("%H:%M") < SCHEDULE["report_at"]
                and briefed_on != time.strftime("%Y-%m-%d")):
            briefed_on = time.strftime("%Y-%m-%d")
            due.append(("AUDIT", [plume_morning, None, 0]))
        for name, p in due:
            job, every = p[0], p[1]
            run_job(name, job, every)
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
