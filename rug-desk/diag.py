# diag.py
# why did the desk buy nothing? every stage of the last hours, from the desk's own files, in one page.
#   python3 diag.py        (last 6 h)      python3 diag.py 24      (last 24 h)
# reads only: no network call, nothing written.
import csv, json, os, statistics, sys, time
from collections import Counter
from config import LOG, TRADES, EVENTS, DATA, MIN_SCORE, DAILY_LOSS_HALT_USD, FACTS, AUDIT
import book

def rows(path):
    try:
        with open(path, newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


if "--trades" in sys.argv:
    # every trade since the start, one line each, for an outside review: when, where, why it was bought,
    # how it ended. reads trades.csv and checks.csv only
    import chains
    from config import RULES_SINCE
    info = {}
    with open(LOG, newline="") as f:
        for r in csv.DictReader(f):
            if r["verdict"] in ("PASS", "BUY"):
                info[r["mint"]] = r
    opened, lines = {}, []
    with open(TRADES, newline="") as f:
        for t in csv.DictReader(f):
            if t["action"] == "open":
                opened[t["mint"]] = {"t": t["time"], "usd": float(t["usd"] or 0), "pnl": 0.0, "exits": []}
            elif t["mint"] in opened:
                o = opened[t["mint"]]
                o["pnl"] += float(t["pnl"])
                o["exits"].append(t["reason"])
                if t["action"] == "close":
                    i = info.get(t["mint"], {})
                    h = (time.mktime(time.strptime(t["time"], "%Y-%m-%d %H:%M"))
                         - time.mktime(time.strptime(o["t"], "%Y-%m-%d %H:%M"))) / 60
                    lines.append(f"{o['t']} | {chains.split(t['mint'])[0]:9} | ${t['symbol'][:12]:12} | mise {o['usd']:6.2f} $ | "
                                 f"{o['pnl'] / max(o['usd'], 1e-9) * 100:+6.1f} % ({o['pnl']:+6.2f} $) | {h:4.0f} min | "
                                 f"sortie {'+'.join(o['exits'])} | palier {i.get('tier') or '?'} | note {i.get('score') or '?'} | "
                                 f"âge entrée {i.get('age_min') or '?'} min | pool {i.get('liq_usd') or '?'} $ | "
                                 f"{'règles actuelles' if o['t'] >= RULES_SINCE else 'anciennes règles'}")
                    opened.pop(t["mint"])
    print(f"== {len(lines)} trades clôturés (date | chaîne | token | mise | résultat | durée | sortie | palier | note | âge | pool)")
    print("\n".join(lines))
    for m, o in opened.items():
        print(f"ouvert : {o['t']} {m[:20]} mise {o['usd']:.2f} $")
    sys.exit(0)

if "--pourquoi" in sys.argv:
    # where the money went, trade by trade, under the rules in force: chain, exit, how high each trade went
    # before it closed (a loser that was up 30%+ is an exit problem, one never up 10% an entry problem), and
    # what the exit engine replayed on the same recorded path would have made: real vs replay is the
    # execution gap (fills, stale prices, sales VIGIE made that the engine would not).
    #   python3 diag.py --pourquoi
    import chains, exits, exitlab, paths
    from config import RULES_SINCE, EXIT
    B_SINCE = "2026-10-26 05:03"          # the "regles B" exits took over
    ts = lambda s: time.mktime(time.strptime(s, "%Y-%m-%d %H:%M"))
    opened, done = {}, []
    for t in book.trades():
        if t["action"] == "open":
            opened[t["mint"]] = {"t": t["time"], "usd": float(t["usd"] or 0), "pnl": 0.0, "why": [], "sym": t["symbol"]}
        elif t["mint"] in opened:
            o = opened[t["mint"]]
            o["pnl"] += float(t["pnl"])
            o["why"].append(t["reason"].split(" ")[0][:18])
            if t["action"] == "close":
                o["closed"] = t["time"]
                done.append((t["mint"], opened.pop(t["mint"])))
    done = [(m, o) for m, o in done if o["t"] >= RULES_SINCE]
    print(f"== {len(done)} trades clôturés depuis {RULES_SINCE} (règles actuelles)")
    print("ouvert           chaîne     token        mise   réel %   haut %   bas %  durée  rejoué actif % / config %  sortie")
    agg, rr = {}, []
    for m, o in done:
        chain = chains.split(m)[0]
        t0, t1 = ts(o["t"]), ts(o["closed"])
        path = paths.load(m, since=t0 - 60)
        inside = [p for p in path if p["t"] <= t1 + 60]
        real = 100 * o["pnl"] / max(o["usd"], 1e-9)
        hi = lo = rep_a = rep_c = None
        if len(inside) >= 2 and inside[0]["price"] > 0:
            e = inside[0]["price"]
            hi = 100 * (max(p["price"] for p in inside) / e - 1)
            lo = 100 * (min(p["price"] for p in inside) / e - 1)
        if len(path) >= 10:
            c = chains.costs(m)
            cost = 2 * (c["fee_pct"] + c.get("mev_pct", 0)) + 2 * c["tx_usd"] / max(o["usd"], 1) * 100
            f = exits.features(path)
            ga, gc = exitlab.simulate(f, exits.for_mint(m)), exitlab.simulate(f, dict(EXIT))
            rep_a = ga / exitlab.TICKET_USD * 100 - cost if ga is not None else None
            rep_c = gc / exitlab.TICKET_USD * 100 - cost if gc is not None else None
            if rep_a is not None:
                rr.append((real, rep_a))
        fmt = lambda x: f"{x:+7.0f}" if x is not None else "      -"
        print(f"{o['t']} {chain:9s} ${o['sym'][:11]:11s} {o['usd']:6.1f} {real:+7.1f} {fmt(hi)} {fmt(lo)} {(t1 - t0) / 3600:5.1f}h "
              f"{fmt(rep_a)} / {fmt(rep_c)}  {'+'.join(o['why'])}")
        tag = "gagnant" if o["pnl"] > 0 else ("perdant, était à +30 % ou plus" if hi is not None and hi >= 30
                                              else "perdant, jamais au-dessus de +10 %" if hi is not None and hi < 10
                                              else "perdant, entre +10 et +30 %")
        for k in (f"chaîne {chain}", f"période {'avant' if o['t'] < B_SINCE else 'après'} le 26/10 05:03 (sorties B)",
                  f"sortie {o['why'][-1]}", f"type : {tag}", f"mois/jour {o['t'][:10]}"):
            a = agg.setdefault(k, [0, 0.0, 0])
            a[0] += 1; a[1] += o["pnl"]; a[2] += o["pnl"] > 0
    print("\n== où va l'argent : n · PnL $ · gagnants")
    for k, (n, pnl, w) in sorted(agg.items()):
        print(f"  {k:52s} {n:3d} {pnl:+9.2f} {w:3d}")
    if rr:
        gap = [a - b for a, b in rr]
        print(f"\n== réel contre rejoué (même trajet, même profil, coûts compris), {len(rr)} trades : "
              f"réel {statistics.mean(a for a, _ in rr):+.1f} % · rejoué {statistics.mean(b for _, b in rr):+.1f} % · "
              f"écart moyen {statistics.mean(gap):+.1f} pts (négatif = le desk exécute moins bien que son propre moteur)")
    sys.exit(0)

if "--entonnoir" in sys.argv:
    # where the tokens die, from the first source to the buy, and what each kill rule is worth in shadow.
    #   python3 diag.py --entonnoir        (last 24 h)      python3 diag.py --entonnoir 48
    import shadow
    nums = [a for a in sys.argv[1:] if a.replace(".", "").isdigit()]
    H = float(nums[0]) if nums else 24
    since = time.time() - H * 3600
    runs = []
    try:
        with open(os.path.join(DATA, "funnel.jsonl")) as f:
            runs = [r for r in (json.loads(x) for x in f if x.strip()) if r.get("t", 0) >= since]
    except (OSError, ValueError):
        pass
    print(f"== entonnoir, {H:.0f} dernières heures")
    if runs:
        n = len(runs)
        avg = lambda k: sum(r.get(k) or 0 for r in runs) / n
        print(f"SCOUT : {n} passages · par passage : {avg('leads'):.0f} pistes ({avg('graduates'):.0f} graduations, "
              f"{avg('evm_new'):.0f} nouveaux pools EVM, {avg('trending'):.0f} tendance, {avg('jupiter_top'):.0f} Jupiter, "
              f"{avg('feeds_and_search'):.0f} listes/recherche) · {sum(r.get('shadowed') or 0 for r in runs)} suivis en fantôme")
        for lane in ("early", "momentum"):
            tot = Counter()
            for r in runs:
                tot.update(r.get(lane) or {})
            print(f"  {lane} : " + " · ".join(f"{k} {v / n:.1f}" for k, v in tot.most_common(12)) + "  (moyenne par passage)")
    else:
        print("SCOUT : pas encore de funnel.jsonl (le desk doit tourner avec ce code)")
    cut = time.strftime("%Y-%m-%d %H:%M", time.localtime(since))
    ch = [r for r in rows(LOG) if r["time"] >= cut and r["stage"] != "limits"]
    print(f"GARDE : {len(ch)} verdicts · {sum(r['verdict'] in ('PASS', 'BUY') for r in ch)} PASS")
    by = Counter((r.get("lane") or "?", r["stage"], r["reason"][:40]) for r in ch if r["verdict"] == "SKIP")
    for (lane, stage, reason), k in by.most_common(15):
        print(f"  {k:3d} x {lane:8s} {stage:6s} {reason}")
    tr = [t for t in rows(TRADES) if t["time"] >= cut and t["action"] == "open"]
    print(f"ACHATS : {len(tr)}")
    r = shadow.results()
    w = shadow.waived()
    print(f"FANTÔME (6 h rejouées, sorties et coûts du desk) : {r['waiting']} en cours · tous {r['all']}")
    print("  raison · n · moyenne nette % · gagnants · 1re moitié · 2e moitié · borne basse · état")
    for d in r["reasons"]:
        state = ("LEVÉE" if d["reason"] in w else "dure (jamais levée)" if d["reason"] in shadow.HARD
                 else f"levée à n {shadow.WAIVE_MIN_N}, moy. ≥ {shadow.WAIVE_MIN_MEAN}, 2 moitiés et borne > 0")
        print(f"  {d['reason'][:22]:22s} {d['n']:4d} {d['mean']:+7.1f} {d['win']:5.0%} {d['half1'] or 0:+7.1f} "
              f"{d['half2'] or 0:+7.1f} {d['low'] if d['low'] is not None else '-':>7} · {state}")
    # the same, per chain, for the rules worth a closer look: a rule can protect on one chain and cost on another
    import chains, statistics as st
    per = {}
    for row in shadow._rows():
        if time.time() < float(row["t"]) + shadow.HOURS * 3600:
            continue
        x = shadow.replay(row)
        if x is not None:
            per.setdefault((row["reason"], chains.split(row["mint"])[0]), []).append(min(x, shadow.CAP_PCT))
    print("PAR CHAÎNE (n ≥ 10) : raison · chaîne · n · moyenne · médiane · gagnants · 1re / 2e moitié")
    for (reason, chain), xs in sorted(per.items(), key=lambda kv: -len(kv[1])):
        if len(xs) >= 10:
            h = len(xs) // 2
            print(f"  {reason[:22]:22s} {chain:9s} {len(xs):4d} {st.mean(xs):+7.1f} {st.median(xs):+7.1f} "
                  f"{sum(x > 0 for x in xs) / len(xs):5.0%} {st.mean(xs[:h]):+7.1f} / {st.mean(xs[h:]):+7.1f}")
    sys.exit(0)

if "--pos" in sys.argv:
    # every open position as VIGIE sees it now: why it is still open. reads the book and the price paths
    import exits, paths
    prof = exits.active()
    print(f"profil de sortie : stop {prof['stop_pct']} % · stop de temps {prof['time_stop_hours']} h sous +{prof['time_stop_min_pct']} %")
    for m, pos in book.load().items():
        hist = paths.load(m, since=time.time() - 3600)
        last = hist[-1] if hist else None
        print(f"{pos['symbol']} {m}")
        print(f"  ouvert il y a {(time.time() - pos['opened']) / 3600:.1f} h · entrée {pos['entry']:.8g} · plus haut {pos['peak']:.8g}")
        if not last:
            print("  AUCUN PRIX enregistré dans la dernière heure : VIGIE ne lit pas ce token")
            continue
        print(f"  dernier prix il y a {(time.time() - last['t']) / 60:.0f} min : {last['price']:.8g} "
              f"({(last['price'] / pos['entry'] - 1) * 100:+.1f} %) · pool {last.get('liq')}")
        print(f"  décision de VIGIE maintenant : {exits.decide(pos, exits.features(hist)[-1], prof) or 'garder'}")
    sys.exit(0)

H = float(sys.argv[1]) if len(sys.argv) > 1 else 6
since = time.time() - H * 3600
cut = time.strftime("%Y-%m-%d %H:%M", time.localtime(since))


print(f"== les {H:.0f} dernières heures (depuis {cut})")

# SCOUT: how many leads reached GARDE, run by run
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
print(f"SCOUT : {len(scans)} passages, {handed} token(s) envoyés à GARDE")
errs = Counter(e["text"][:90] for e in ev if e.get("kind") == "error")
for t, n in errs.most_common(5):
    print(f"  erreur x{n} : {t}")

# GARDE: every verdict, by stage and reason
ch = [r for r in rows(LOG) if r["time"] >= cut]
print(f"GARDE : {len(ch)} verdict(s)")
for (stage, reason), n in Counter((r["stage"], r["reason"]) for r in ch if r["verdict"] == "SKIP").most_common(15):
    print(f"  {n:3d} x {stage:7s} {reason}")
passes = [r for r in ch if r["verdict"] in ("PASS", "BUY")]
low = [r for r in passes if r.get("score") and int(float(r["score"])) < MIN_SCORE]
print(f"  PASS : {len(passes)}, dont {len(low)} sous la note minimale {MIN_SCORE} (non achetés)")
for r in passes:
    print(f"     {r['time']} ${r['symbol']} note {r.get('score')} {r.get('flags') or ''}")

# holders: where they were read from (no_holders was the big killer)
nh = sum(1 for r in ch if r["reason"] == "no_holders")
print(f"  holders illisibles : {nh}/{len(ch)}")
try:
    src = json.load(open(os.path.join(DATA, "sources.json")))
    for k in ("helius_das", "goplus", "jupiter", "stracker"):
        if k in src:
            s = src[k]
            print(f"  source {k}: {'OK' if s.get('ok') else 'EN PANNE'} il y a {(time.time() - s['t']) / 60:.0f} min · {s.get('detail', '')[:70]}")
except (OSError, ValueError):
    pass
import facts
print(f"  RPC : {'Helius' if 'helius' in facts.RPC_URL else 'PUBLIC (pas de Helius dans .env)'}")

# the book's limits: one of them blocks every buy when it trips
b = book.load()
print(f"LIMITES : perte du jour {book.today_pnl():+.2f} $ (arrêt à -{DAILY_LOSS_HALT_USD}) · "
      f"{len(b)} position(s) ouverte(s) · cash {book.cash(b):.0f} $")
tr = [t for t in rows(TRADES) if t["time"] >= cut]
print(f"ACHATS : {sum(1 for t in tr if t['action'] == 'open')} · ventes : {sum(1 for t in tr if t['action'] != 'open')}")
print(f"RÈGLES D'ENTRÉE : âge min {FACTS['min_age_min']} min, pool min {FACTS['min_liquidity_usd']} $, "
      f"top 10 max {FACTS['max_top10_pct']} %, prix >= {FACTS.get('min_vs_graduation')} x graduation")

# was each kind of verdict right? AUDIT's 6 h re-price of every verdict, the whole history
score = {r["mint"]: r.get("score") for r in rows(LOG)}
groups = {}
for a in rows(AUDIT):
    try:
        ch_pct = float(a["change_pct"])
    except (TypeError, ValueError):
        continue
    if a["verdict"] in ("PASS", "BUY"):
        sc = score.get(a["mint"])
        key = "PASS note < %d (pas acheté)" % MIN_SCORE if sc and int(float(sc)) < MIN_SCORE else "PASS acheté"
    else:
        key = a["reason"] or "?"
    groups.setdefault(key, []).append(ch_pct)
print("6 H APRÈS LE VERDICT (tout l'historique d'AUDIT) : n · médiane · chute ≤ -50 % · hausse ≥ +100 %")
for key, xs in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:20]:
    xs.sort()
    med = xs[len(xs) // 2]
    print(f"  {len(xs):3d} · {med:+7.0f} % · {sum(x <= -50 for x in xs) / len(xs):4.0%} · "
          f"{sum(x >= 100 for x in xs) / len(xs):4.0%} · {key}")
