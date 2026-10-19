# report.py
# the evening report. everything in it comes from checks.csv and trades.csv, nothing from memory.
import csv, json, os, time
from collections import Counter
from config import LOG, PAPER, JUDGE
import book, audit, edge


def report() -> str:
    day = time.strftime("%Y-%m-%d")
    checks = []
    if os.path.exists(LOG):
        with open(LOG, newline="") as f:
            checks = [r for r in csv.DictReader(f) if r["time"].startswith(day)]
    done = [t for t in book.trades() if t["time"].startswith(day) and t["action"] != "open"]

    by_stage = Counter(r["stage"] for r in checks if r["verdict"] == "SKIP")
    passed = [r for r in checks if r["verdict"] in ("BUY", "PASS")]
    wins = [t for t in done if float(t["pnl"]) > 0]
    reasons = Counter(r["reason"] for r in checks if r["stage"] in ("facts", "pool"))

    e = edge.stats()
    lines = [f"EVENING REPORT {day} {'(PAPER)' if PAPER else '(LIVE)'} judge={JUDGE}",
             f"READY FOR REAL MONEY: {dict(yes='YES', no='NO', wait='NOT YET')[e['verdict']]} - {e['why']}",
             f"checked: {len(checks)}",
             f"killed by rug filter: {by_stage['facts']} | by pool: {by_stage['pool']} | "
             f"by judge: {by_stage['judge']} | by limits: {by_stage['limits']}",
             f"passed: {len(passed)} | open now: {len(book.load())}",
             f"realized pnl today: ${book.today_pnl():+.2f}"]
    if done:
        lines.append(f"green exits: {len(wins)}/{len(done)}")
        best = max(done, key=lambda t: float(t["pnl"]))
        worst = min(done, key=lambda t: float(t["pnl"]))
        lines.append(f"best: {best['symbol']} ${float(best['pnl']):+.2f} | "
                     f"worst: {worst['symbol']} ${float(worst['pnl']):+.2f}")
    for reason, n in reasons.most_common(3):
        lines.append(f"kill reason: {reason} ({n}x)")
    # the article's two closing lines: one thing that worked, one number to question. from data, not taste
    stats = audit.by_reason()
    if stats:
        best = max(stats, key=lambda o: o["crashed"] / o["n"])
        lines.append(f"worked: '{best['reason']}' killed {best['n']} audited tokens, "
                     f"{best['crashed']} of them crashed below {audit.CRASH_PCT}% within hours")
        worst = max(stats, key=lambda o: o["ran"] / o["n"])
        if worst["ran"] / worst["n"] >= 0.3:
            lines.append(f"question: {audit.KNOB.get(worst['reason'], worst['reason'])} in config.py: "
                         f"'{worst['reason']}' killed {worst['n']} tokens and {worst['ran']} still did +100%. "
                         f"look at them before you move it, and write down why")
    lab = {}
    lab_path = os.path.join(os.path.dirname(LOG), "exitlab.json")
    if os.path.exists(lab_path):
        with open(lab_path) as f:
            lab = json.load(f)
    if lab.get("trades"):
        top = lab["results"][0]
        act = next(r for r in lab["results"] if r["name"] == "actif")
        lines.append(f"exit lab on {lab['trades']} trades: best '{top['name']}' {top['pnl']:+.2f}$, "
                     f"active profile '{lab['active']}' {act['pnl']:+.2f}$")
        if lab.get("speed"):
            lines.append("speed test (active profile): " + ", ".join(
                f"every {r['every_s']}s {r['pnl']:+.2f}$" for r in lab["speed"]))
    bd = audit.breakdown()
    for kind, label in (("hour", "entry hour"), ("age", "token age at entry"), ("tier", "ticket tier")):
        rows = [b for b in bd[kind] if b["n"]]
        if rows:
            worst = min(rows, key=lambda b: b["pnl"])
            lines.append(f"by {label}: " + ", ".join(f"{b['bucket']} {b['pnl']:+.2f}$ ({b['n']})" for b in rows)
                         + f" -> worst: {worst['bucket']}")
    a = audit.summary()
    up, down = a["regime"]["SOL up"], a["regime"]["SOL down"]
    if up["n"] or down["n"]:
        lines.append(f"regime: passes crashed {up['crashed']}/{up['n']} with SOL up over 24h, "
                     f"{down['crashed']}/{down['n']} with SOL down")
    xb, xs = a["x"]["BUY"], a["x"]["SKIP"]
    if xb["n"] or xs["n"]:
        lines.append(f"ECHO: {xs['crashed']}/{xs['n']} tokens it skipped crashed later, "
                     f"{xb['crashed']}/{xb['n']} it approved crashed later")
    k, p = a["killed"], a["passed"]
    if k["n"] or p["n"]:
        lines.append(f"audit: {k['crashed']}/{k['n']} killed tokens crashed later, "
                     f"{p['crashed']}/{p['n']} passed tokens crashed later")
    return "\n".join(lines)


if __name__ == "__main__":
    print(report())


def morning(hours: float = 10) -> str:
    """What happened while you slept: the last N hours, from the same files, nothing from memory."""
    since = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - hours * 3600))
    trades = [t for t in book.trades() if t["time"] >= since]
    exits = [t for t in trades if t["action"] != "open"]
    buys = [t for t in trades if t["action"] == "open"]
    checks = []
    if os.path.exists(LOG):
        with open(LOG, newline="") as f:
            checks = [r for r in csv.DictReader(f) if r["time"] >= since]
    kills = Counter(r["reason"] for r in checks if r["verdict"] == "SKIP")
    pnl = sum(float(t["pnl"]) for t in exits)
    lines = [f"MORNING BRIEF, last {hours:.0f} h {'(PAPER)' if PAPER else '(LIVE)'}",
             f"realized: ${pnl:+.2f} on {len(exits)} sale(s) | bought: {len(buys)} | open now: {len(book.load())}",
             f"tokens checked: {len(checks)}, passed: {sum(1 for r in checks if r['verdict'] in ('PASS', 'BUY'))}"]
    if exits:
        best = max(exits, key=lambda t: float(t["pnl"]))
        worst = min(exits, key=lambda t: float(t["pnl"]))
        lines.append(f"best: {best['symbol']} ${float(best['pnl']):+.2f} ({best['reason']}) | "
                     f"worst: {worst['symbol']} ${float(worst['pnl']):+.2f} ({worst['reason']})")
    if kills:
        lines.append("top kills: " + ", ".join(f"{k} {n}x" for k, n in kills.most_common(3)))
    xr = {}
    x_path = os.path.join(os.path.dirname(LOG), "x_reads.csv")
    if os.path.exists(x_path):
        with open(x_path, newline="") as f:
            xr = [r for r in csv.DictReader(f) if r["time"] >= since]
        no_x = sum(1 for r in xr if r["verdict"] == "NO_X")
        lines.append(f"ECHO: {sum(1 for r in xr if r['verdict'] in ('BUY', 'SKIP'))} X read(s)"
                     + (f", {no_x} bought without X (ECHO was silent: check its session)" if no_x else ""))
    import health
    lines.append("desk: " + (health.summary(hours) or "no pause, it ran the whole night"))
    return "\n".join(lines)


def status(hours: float = 1) -> str:
    """The chief of staff's answer to "what is happening": five lines, every agent, the last hour.
    asked with /etat in the paired Telegram chat. built from the desk's files, nothing from memory."""
    from config import EVENTS, TRADES, PAPER_BANKROLL_USD
    since = time.time() - hours * 3600
    cut = time.strftime("%Y-%m-%d %H:%M", time.localtime(since))
    ev = []
    try:
        with open(EVENTS) as f:
            for line in f:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if e.get("t", 0) >= since:
                    ev.append(e)
    except OSError:
        pass
    scans = [e for e in ev if e.get("agent") == "SCOUT" and e.get("kind") == "scan"]
    handed = sum(int(e["text"].split(" token")[0]) for e in scans if e["text"][:1].isdigit())
    checks = []
    if os.path.exists(LOG):
        with open(LOG, newline="") as f:
            checks = [r for r in csv.DictReader(f) if r["time"] >= cut]
    kills = Counter(r["reason"] for r in checks if r["verdict"] == "SKIP")
    passes = sum(1 for r in checks if r["verdict"] in ("PASS", "BUY"))
    trades = []
    if os.path.exists(TRADES):
        with open(TRADES, newline="") as f:
            trades = [t for t in csv.DictReader(f) if t["time"] >= cut]
    buys = [t for t in trades if t["action"] == "open"]
    sold = sum(float(t["pnl"]) for t in trades if t["action"] != "open")
    pos = book.load()
    import shadow
    sh = shadow.results()
    lifted = sorted(shadow.waived())
    span = "Dernière heure" if hours == 1 else f"Dernières {hours:.0f} h" if hours > 1 else f"Dernières {hours * 60:.0f} min"
    top = ", ".join(f"{k} {n}" for k, n in kills.most_common(3)) or "aucune"
    lines = [
        f"{span} : SCOUT {len(scans)} passages, {handed} token(s) à GARDE · GARDE {len(checks)} verdicts, "
        f"{passes} PASS · éliminations : {top}",
        f"Achats : {len(buys)}" + (f" ({', '.join(t['symbol'] for t in buys[:5])})" if buys else "")
        + f" · ventes : {sold:+.2f} $ · {len(pos)} position(s) ouverte(s)",
        f"Solde {PAPER_BANKROLL_USD + book.realized():.2f} $ (réalisé) · aujourd'hui {book.today_pnl():+.2f} $",
        f"Fantômes : {sh['waiting']} suivis" + (f" · écartés {sh['all']['mean']:+.1f} %/trade sur {sh['all']['n']}"
                                                if sh.get("all") else " · premiers résultats 6 h après")
        + (f" · règles levées : {', '.join(lifted)}" if lifted else ""),
    ]
    try:
        import backtest
        r = (backtest.scorecard().get("rules") or {}).get("early: desk now (60 min + graduation)")
        if r:
            lines.append(f"Backtest règle actuelle : {r['mean']:+.1f} %/trade sur {r['n']} trades · {r['why']}")
    except Exception:
        pass
    return "\n".join(lines[:5])


def weekly(save: bool = True) -> str:
    """The real-money review (BILAN_ON, Oct 26). Everything the decision needs, on the current rules only,
    and the verdict of the criteria fixed on Oct 19, applied mechanically: no reading between the lines."""
    import chains, shadow
    from config import RULES_SINCE, DATA
    st = edge.stats()
    rule = edge.judge(st["n"], st.get("mean_pct"), st.get("ci_low_pct"))
    tier_of = {}
    if os.path.exists(LOG):
        with open(LOG, newline="") as f:
            for r in csv.DictReader(f):
                if r.get("tier"):
                    tier_of[r["mint"]] = r["tier"]
    by_chain = edge.split(lambda t: chains.split(t["mint"])[0])
    by_tier = edge.split(lambda t: tier_of.get(t["mint"], "base"))
    sh = shadow.results()
    try:
        import backtest
        card = backtest.scorecard()
    except Exception:
        card = {"rules": {}}
    a = audit.summary()
    bil = edge.bilan(card)
    go = rule["verdict"] == "edge" and st.get("max_drawdown", 1e9) <= edge.MAX_DRAWDOWN_SHARE * edge.PAPER_BANKROLL_USD
    L = [f"RAPPORT DE DÉCISION — argent réel ? ({time.strftime('%Y-%m-%d')})",
         f"Règles jugées : celles en place depuis le {RULES_SINCE}. Critères fixés le 19 octobre, avant les données.",
         "",
         f"DÉCISION : {'OUI, à petite taille (quart de Kelly, 5 % max par trade)' if go else 'NON'} — {rule['why']}",
         "",
         f"PAPIER : {st['n']} trades clôturés · rendement moyen {st.get('mean_pct', 0):+.1f} % par trade"
         + (f" (IC 95 % {st['ci_low_pct']:+.1f} à {st['ci_high_pct']:+.1f})" if st.get('ci_low_pct') is not None else "")
         + (f" · gagnants {st['win_rate']:.0%} · pire drawdown {st['max_drawdown']:.0f} $" if st["n"] else ""),
         "par chaîne : " + (" · ".join(f"{g['group']} {g['n']} trades {g['mean_pct']:+.1f} % ({g['total']:+.2f} $)" for g in by_chain) or "aucun trade"),
         "par mise : " + (" · ".join(f"{g['group']} {g['n']} trades {g['mean_pct']:+.1f} %" for g in by_tier) or "aucun trade"),
         "",
         "BACKTEST (Solana, graduations rejouées) : " + (" · ".join(
             f"{k} n={v['n']} {v['mean']:+.1f} % [{v['ci95'][0]:+.0f}, {v['ci95'][1]:+.0f}] {v.get('why', '')}"
             for k, v in (card.get("rules") or {}).items()) or "pas encore de données"),
         f"BILAN papier contre backtest : {bil['why']}",
         "",
         "LE FILTRE (6 h après chaque verdict) : "
         f"éliminés qui ont chuté {a['killed']['crashed']}/{a['killed']['n']} · PASS qui ont chuté {a['passed']['crashed']}/{a['passed']['n']}",
         "FANTÔMES (si on avait acheté les écartés) : "
         + (f"{sh['all']['n']} trades, {sh['all']['mean']:+.1f} % par trade" if sh.get("all") else "pas encore de résultats")
         + (" · " + " · ".join(f"{d['reason']} {d['n']}×{d['mean']:+.1f} %" for d in sh["reasons"][:6]) if sh.get("reasons") else "")
         + (f" · règles levées : {', '.join(sorted(shadow.waived()))}" if shadow.waived() else ""),
         "",
         "Règle de décision : OUI seulement avec 200 trades ou plus, un rendement moyen d'au moins +3 % par trade, "
         "l'intervalle à 95 % entièrement au-dessus de 0, et un drawdown sous 30 % de la banque. Sinon NON, "
         "et le papier continue. Avec 300 trades et une moyenne ≤ 0 : on arrête l'idée d'en vivre du trading."]
    text = "\n".join(L)
    if save:
        with open(os.path.join(DATA, f"rapport_decision_{time.strftime('%Y-%m-%d')}.txt"), "w") as f:
            f.write(text + "\n")
    return text
