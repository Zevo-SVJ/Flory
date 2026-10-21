# export.py
# everything the desk knows, in one text file, for a review: every trade under the current rules with
# what each agent saw, the shadow book per kill reason, the model, the exit lab, the self-reviews, the
# incidents, ECHO's reads, the backtest, TENDANCE. reads files only: no network, nothing written but the
# report itself.
#   python3 export.py > ~/Desktop/rug-desk-export.txt
import csv, json, os, statistics, sys, time
from collections import Counter
from config import DATA, LOG, TRADES, RULES_SINCE, PAPER_BANKROLL_USD


def section(title):
    print(f"\n===== {title} =====")


def safe(fn):
    try:
        fn()
    except Exception as e:
        print(f"(indisponible : {type(e).__name__}: {str(e)[:150]})")


def rows(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def jread(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def header():
    import book
    print(f"RUG DESK EXPORT · {time.strftime('%Y-%m-%d %H:%M')} · règles actuelles depuis {RULES_SINCE}")
    r = book.reset_info()
    print(f"reset du solde : {r.get('time', 'aucun')} · réalisé depuis : {book.realized():+.2f} $ · "
          f"positions ouvertes : {len(book.load())} · cash {book.cash():.2f} $")


def trades():
    """One line per trade opened under the current rules, with what every agent saw."""
    import dossier, paths, chains
    checks = {}
    for r in rows(LOG):
        if r["verdict"] in ("PASS", "BUY"):
            checks[r["mint"]] = r
    reads = {r["mint"]: r for r in rows(os.path.join(DATA, "x_reads.csv")) if r.get("mint")}
    opened = {}
    out = []
    for t in rows(TRADES):
        if t["action"] == "open":
            if t["time"] >= RULES_SINCE:
                opened[t["mint"]] = {"t": t["time"], "usd": float(t["usd"] or 0), "pnl": 0.0, "exits": [], "sym": t["symbol"]}
        elif t["mint"] in opened:
            o = opened[t["mint"]]
            o["pnl"] += float(t["pnl"])
            o["exits"].append(t["reason"])
            if t["action"] == "close":
                o["closed"] = t["time"]
                out.append((t["mint"], opened.pop(t["mint"])))
    out += [(m, o) for m, o in opened.items()]
    print("ouvert | fermé | chaîne | token | voie | source | note | signaux | rugcheck | cadran | âge min | pool $ | "
          "mise | pnl $ | pnl % | plus haut % | sorties | ECHO")
    pcts = []
    for m, o in out:
        c = checks.get(m, {})
        d = dossier.load(m)["entries"]
        src = next((e.get("source") for e in d if e.get("agent") == "SCOUT" and e.get("source")), "?")
        buy = next((e for e in d if e.get("what") == "achat"), {})
        entry = buy.get("price") or (float(c["price"]) if c.get("price") else None)
        peak = None
        if entry:
            t0 = time.mktime(time.strptime(o["t"], "%Y-%m-%d %H:%M"))
            t1 = time.mktime(time.strptime(o["closed"], "%Y-%m-%d %H:%M")) + 60 if o.get("closed") else time.time()
            ps = [p["price"] for p in paths.load(m, since=t0, until=t1) if p["price"] > 0]
            peak = (max(ps) / entry - 1) * 100 if ps else None
        x = reads.get(m, {})
        pct = o["pnl"] / o["usd"] * 100 if o["usd"] else 0
        if o.get("closed"):
            pcts.append(pct)
        print(" | ".join(str(v) for v in [
            o["t"][5:], o["closed"][5:] if o.get("closed") else "OUVERT", chains.split(m)[0], "$" + o["sym"][:12], c.get("lane") or "?",
            src, c.get("score") or "?", c.get("flags") or "-", c.get("rc_score") or "-", c.get("dial") or "-",
            c.get("age_min") or "?", c.get("liq_usd", "?")[:8] if c.get("liq_usd") else "?", f"{o['usd']:.2f}",
            f"{o['pnl']:+.2f}", f"{pct:+.1f}", f"{peak:+.0f}" if peak is not None else "?", "+".join(o["exits"]) or "-",
            (x.get("verdict", "-") + " " + (x.get("raison") or "")[:60]).strip()]))
    if pcts:
        m = statistics.mean(pcts)
        sd = statistics.stdev(pcts) if len(pcts) > 1 else 0
        print(f"-> {len(pcts)} clôturés · moyenne {m:+.1f} % · médiane {statistics.median(pcts):+.1f} % · écart-type {sd:.1f} · "
              f"gagnants {sum(p > 0 for p in pcts)}/{len(pcts)} · moyenne sans les 2 meilleurs "
              f"{statistics.mean(sorted(pcts)[:-2]):+.1f} %" if len(pcts) > 2 else "")


def by_chain():
    import edge
    for row in edge.split(lambda t: __import__("chains").split(t["mint"])[0]):
        print("  ", row)


def shadow_book():
    import shadow
    r = shadow.results()
    print(f"en cours : {r['waiting']} · tous : {r['all']} · règles levées : {sorted(shadow.waived())}")
    for d in r["reasons"]:
        print(f"  {d['reason']}: n={d['n']} moyenne {d['mean']} % · gagnants {d['win']} · moitiés {d['half1']} / {d['half2']} · borne basse {d['low']}")


def model():
    m = jread(os.path.join(DATA, "model.json"), {}) or {}
    print({k: m.get(k) for k in ("n", "trusted", "why", "test_n", "test_avg", "picks", "pick_avg", "pick_low")})
    for l in m.get("lessons", []):
        print("  ", l)


def lab():
    l = jread(os.path.join(DATA, "exitlab.json"), {}) or {}
    print(f"trades rejoués : {l.get('trades')} · profil actif : {l.get('active')}")
    for r in l.get("results", []):
        print("  ", {k: r.get(k) for k in ("name", "n", "pnl", "win", "half1", "half2")})
    for s in l.get("speed", []) or []:
        print("   vitesse", s)


def reviews():
    import coach
    rv = coach.reviews()
    for a, r in rv.items():
        if isinstance(r, dict):
            print(f"[{a}] fait : {r.get('did')} · erreurs : {r.get('mistakes')} · change : {r.get('change')}")
    for e in coach.journal():
        print("  journal :", {k: e.get(k) for k in ("agent", "key", "old", "new", "why", "status", "undone_why")})


def incidents():
    import incidents as inc
    st = inc.status()
    print(f"prudence : {st.get('prudent')} · facteur {st.get('factor')} · pause {st.get('paused_s')} s · motifs : {st.get('patterns')}")
    print("lecture :", (st.get("reading") or {}).get("text"))
    for r in inc.recent(0):
        print(f"  {r['time']} {r['level']} -{r['drop']} $ · {r['cause']} · {r['detail'][:160]}")


def echo():
    xs = rows(os.path.join(DATA, "x_reads.csv"))
    print(f"lectures : {len(xs)} · verdicts : {dict(Counter(x['verdict'].upper() for x in xs))}")
    ts = sorted(time.mktime(time.strptime(x["time"], "%Y-%m-%d %H:%M")) for x in xs if x.get("time", "")[:4].isdigit())
    gaps = sorted(((b - a) / 60, time.strftime("%m-%d %H:%M", time.localtime(a))) for a, b in zip(ts, ts[1:]))[-5:]
    print("plus longs silences (min, depuis) :", [(round(g), s) for g, s in gaps])
    for x in xs[-15:]:
        print(f"  {x['time']} ${x['symbol'][:12]} {x['verdict']} · {x.get('raison', '')[:90]}")
    if os.path.exists(os.path.join(DATA, "narratives.txt")):
        print("narratives :", open(os.path.join(DATA, "narratives.txt")).read().split())


def kills():
    ch = [r for r in rows(LOG) if r["time"] >= RULES_SINCE]
    print(f"verdicts depuis les règles actuelles : {len(ch)} · PASS {sum(r['verdict'] in ('PASS', 'BUY') for r in ch)}")
    for k, n in Counter(r["reason"] for r in ch if r["verdict"] == "SKIP").most_common(15):
        print(f"  {k}: {n}")
    print("PASS par chaîne :", dict(Counter((r.get("chain") or "solana") for r in ch if r["verdict"] in ("PASS", "BUY"))))


def backtest_card():
    import backtest
    c = backtest.scorecard()
    for k, v in (c.get("rules") or {}).items():
        print(f"  {k}: {v}")


def edge_stats():
    import edge
    print(edge.stats())


def trend():
    import majors
    s = majors.summary()
    print(f"TENDANCE {s.get('equity')} · ordres {s.get('n_fills')} · cadran {s.get('dial')}")
    for r in (s.get("bt") or {}).get("runs", []):
        print(f"  {r['name']}: {r['verdict']} · règle {r['trend']} · garder {r['hold']}")


def health():
    import health as h
    print("pauses 48 h :", [(time.strftime("%m-%d %H:%M", time.localtime(a)), round((b - a) / 60), k) for a, b, k in h.gaps(48)])
    src = jread(os.path.join(DATA, "sources.json"), {}) or {}
    for k, v in src.items():
        if isinstance(v, dict):
            print(f"  source {k}: {'OK' if v.get('ok') else 'EN PANNE'} · {str(v.get('detail'))[:80]}")


if __name__ == "__main__":
    for title, fn in (("ÉTAT", header), ("TRADES DEPUIS LES RÈGLES ACTUELLES", trades), ("PAR CHAÎNE", by_chain),
                      ("STATISTIQUES DE DÉCISION", edge_stats), ("TOKENS ÉCARTÉS SUIVIS EN FANTÔME", shadow_book),
                      ("ÉLIMINATIONS", kills), ("MODÈLE", model), ("LABO DE SORTIE", lab),
                      ("AUTO-CRITIQUES ET JOURNAL", reviews), ("BAISSES ET INCIDENTS", incidents), ("ECHO", echo),
                      ("BACKTEST", backtest_card), ("TENDANCE", trend), ("SANTÉ", health)):
        section(title)
        safe(fn)
