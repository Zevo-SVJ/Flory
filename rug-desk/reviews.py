# reviews.py
# each agent's self-review, every 6 h (AUDIT runs them): what it did, where it was wrong, and the one
# change the data supports. the lessons are the shadow book: every token GARDE judged, followed 6 h and
# replayed with the desk's exits and costs (shadow.py). proposals go through coach.py's guards.
#   VIGIE   replays every exit profile on the same tokens (paired: the noise of the token cancels out)
#   GARDE   which kills saved money and which cost winners; its soft rules lift themselves (shadow.waived),
#           its model learns (learn.py); this review reports both
#   SCOUT   which sources bring the tokens that pay; the best ones get looked at first (never one dropped)
#   ECHO    do its SKIPs foresee the drops? if clearly yes, a SKIP sells again; if not, it stays a note
#   TREND   its own book (majors.py) and its backtest verdicts; and do memecoins bought in a red regime
#           (dial < 0.5) lose? if clearly yes, the meme desk stands down below 0.5 (coach "meme_dial_gate")
#   AUDIT   the referee: re-tests past changes on new data, undoes the bad ones, trips the breaker
import csv, math, os, statistics, time
from config import EXIT
import coach

HOLD_S = 6 * 3600


def lessons(reasons: tuple | None = None) -> list[dict]:
    """Shadows whose 6 h are over, oldest first, with their path loaded once: {row, path, y}."""
    import shadow
    out = []
    for r in sorted(shadow._rows(), key=lambda r: float(r["t"])):
        if time.time() < float(r["t"]) + HOLD_S or (reasons and r["reason"] not in reasons):
            continue
        p = shadow.path(r)
        if not p:
            continue
        y = shadow.replay(r, p=p)
        if y is not None:
            out.append({"row": r, "path": p, "y": max(-100.0, min(200.0, y))})
    return out


def profiles() -> dict:
    import exitlab
    return {"config": dict(EXIT), **{n: {**EXIT, **o} for n, o in exitlab.PROFILES.items()}}


def _net(path, params) -> float | None:
    import exitlab
    g = exitlab.simulate(path[0], params)
    return None if g is None else max(-100.0, min(200.0, g / exitlab.TICKET_USD * 100 - path[1]))


# ---------------------------------------------------------------- VIGIE
def vigie(balance: float | None) -> dict:
    data = lessons(("pass",))                 # the tokens the desk buys: its exits are judged on those
    cands = profiles()
    active = coach.get("exit_profile", "config")
    act = cands.get(active, cands["config"])
    base = [_net(d["path"], act) for d in data]
    best, best_res, best_mean = None, None, None
    for name, params in cands.items():
        if name == active:
            continue
        diffs = [n - b for n, b in ((_net(d["path"], params), b) for d, b in zip(data, base)) if n is not None and b is not None]
        res = coach.paired(diffs, k=len(cands) - 1)
        if res.get("mean") is not None and (best_mean is None or res["mean"] > best_mean):
            best, best_res, best_mean = name, res, res["mean"]
    did = [f"{len(data)} tokens achetables suivis jusqu'au bout, rejoués avec mon profil « {active} »"
           + (f" : {statistics.mean([b for b in base if b is not None]):+.1f} % par trade en moyenne" if data else "")]
    gaps = []
    if data and best:
        bp = cands[best]
        for d, b in zip(data, base):
            o = _net(d["path"], bp)
            if b is not None and o is not None and o - b >= 30:
                gaps.append((o - b, d["row"]["symbol"], b, o))
    mistakes = [f"{len(gaps)} sorties à plus de 30 points de ce que « {best} » aurait fait"
                + (" : " + ", ".join(f"${s} {b:+.0f} % au lieu de {o:+.0f} %" for _, s, b, o in sorted(gaps, reverse=True)[:3]) if gaps else "")] if best else []
    change = f"pas encore assez de tokens suivis pour comparer mes {len(cands)} profils (il en faut {coach.MIN_N})"
    if best_res:
        e = coach.apply("VIGIE", "exit_profile", best, best_res, balance) if best_res["ok"] else None
        change = (f"je passe au profil « {best} » : {best_res['why']}" if e else
                  f"meilleure alternative « {best} » : {best_res['why']} → je garde « {active} »")
    return {"did": did, "mistakes": mistakes, "change": change}


def _test_exit(entry) -> dict:
    cands = profiles()
    new, old = cands.get(entry["new"]), cands.get(entry["old"] or "config", cands["config"])
    data = [d for d in lessons(("pass",)) if float(d["row"]["t"]) > entry["t"]]
    diffs = [a - b for a, b in ((_net(d["path"], new), _net(d["path"], old)) for d in data) if a is not None and b is not None]
    return coach.paired(diffs)


# ---------------------------------------------------------------- GARDE
def garde(balance: float | None) -> dict:
    import shadow, learn
    res = shadow.results()
    data = lessons()
    killed = [d for d in data if d["row"]["reason"] not in ("pass", "low_score", "model_veto")]
    passed = [d for d in data if d["row"]["reason"] == "pass"]
    missed = [d for d in killed if d["y"] >= 100]
    crashed = [d for d in passed if d["y"] <= -50]
    did = [f"{len(data)} verdicts suivis 6 h : {len(passed)} PASS, {len(killed)} éliminés"]
    by = {}
    for d in missed:
        by[d["row"]["reason"]] = by.get(d["row"]["reason"], 0) + 1
    mistakes = []
    if missed:
        mistakes.append(f"{len(missed)} gagnants éliminés (+100 % ou plus) : "
                        + ", ".join(f"{k} {n}" for k, n in sorted(by.items(), key=lambda kv: -kv[1])[:4]))
    if crashed:
        mistakes.append(f"{len(crashed)} PASS qui ont perdu 50 % ou plus : "
                        + ", ".join("$" + d["row"]["symbol"] for d in crashed[:5]))
    rules = [f"{d['reason']} {d['mean']:+.0f} % (n={d['n']})" for d in res.get("reasons", [])
             if d["reason"] not in ("pass", "low_score", "model_veto") and d["n"] >= 10][:6]
    if rules:
        did.append("si on avait acheté ce que j'ai écarté : " + " · ".join(rules))
    L = learn.load()
    lifted = sorted(shadow.waived())
    change = ("règles levées par les données : " + ", ".join(lifted) if lifted else "aucune règle levée : "
              "aucune n'a encore prouvé qu'elle coûte de l'argent (20 cas, +5 %, deux moitiés, au-delà du bruit)")
    change += f" · modèle : {L.get('why') or 'pas encore entraîné'}" + (" (il décide)" if L.get("trusted") else "")
    return {"did": did, "mistakes": mistakes, "change": change}


# ---------------------------------------------------------------- SCOUT
def _source_of(mint: str) -> str | None:
    import dossier
    e = dossier.last(mint, "SCOUT")
    return (e or {}).get("source")


def _gap_test(a: list[float], b: list[float], k: int) -> dict:
    """Unpaired: does group a beat group b by more than the noise? and on both time halves?"""
    out = {"n": min(len(a), len(b)), "ok": False}
    if len(a) < 2 or len(b) < 2:
        return {**out, "why": "pas assez de cas"}
    d = statistics.mean(a) - statistics.mean(b)
    se = math.sqrt(statistics.variance(a) / len(a) + statistics.variance(b) / len(b))
    ha, hb = len(a) // 2, len(b) // 2
    h1 = statistics.mean(a[:ha] or a) - statistics.mean(b[:hb] or b)
    h2 = statistics.mean(a[ha:]) - statistics.mean(b[hb:])
    low = d - coach.z_for(k) * se
    out.update(mean=round(d, 2), low=round(low, 2), half1=round(h1, 2), half2=round(h2, 2))
    if out["n"] < coach.MIN_N:
        out["why"] = f"{out['n']} cas : il en faut {coach.MIN_N}"
    elif low <= 0:
        out["why"] = f"écart {d:+.1f} pts mais dans le bruit (borne basse {low:+.1f})"
    elif h1 <= 0 or h2 <= 0:
        out["why"] = f"écart sur une seule moitié ({h1:+.1f} / {h2:+.1f})"
    else:
        out.update(ok=True, why=f"écart {d:+.1f} pts, borne basse {low:+.1f}, les deux moitiés")
    return out


def scout(balance: float | None) -> dict:
    data = lessons()
    by = {}
    for d in data:
        by.setdefault(_source_of(d["row"]["mint"]) or "inconnue", []).append(d["y"])
    stats = sorted(((s, len(v), statistics.mean(v)) for s, v in by.items()), key=lambda x: -x[2])
    did = ["mes sources, rendement moyen des tokens qu'elles amènent : "
           + " · ".join(f"{s} {m:+.0f} % (n={n})" for s, n, m in stats)] if stats else ["pas encore de leçons"]
    mistakes = [f"« {s} » amène des tokens à {m:+.0f} % en moyenne" for s, n, m in stats if n >= 10 and m < -20][:3]
    ranked = [s for s, n, m in stats if n >= coach.MIN_N and s != "inconnue"]
    change = "ordre des sources inchangé : pas assez de cas par source"
    if len(ranked) >= 2:
        top, bottom = ranked[0], ranked[-1]
        res = _gap_test(by[top], by[bottom], k=len(ranked))
        if res["ok"]:
            e = coach.apply("SCOUT", "source_rank", ranked, res, balance)
            change = f"je regarde d'abord : {' > '.join(ranked)} ({res['why']})" if e else \
                f"ordre confirmé par les données, déjà appliqué ou changement récent : {' > '.join(ranked)}"
        else:
            change = f"« {top} » contre « {bottom} » : {res['why']} → ordre inchangé"
    return {"did": did, "mistakes": mistakes, "change": change}


# ---------------------------------------------------------------- ECHO
def _echo_groups(after: float = 0) -> tuple[list[float], list[float]]:
    import pending
    reads = pending.reads()
    skip, other = [], []
    for d in lessons(("pass",)):
        if float(d["row"]["t"]) <= after:
            continue
        v = (reads.get(d["row"]["mint"]) or {}).get("verdict", "").upper()
        (skip if v == "SKIP" else other).append(d["y"])
    return skip, other


def echo(balance: float | None) -> dict:
    skip, other = _echo_groups()
    did = [f"{len(skip)} tokens lus SKIP, {len(other)} autres, suivis 6 h"]
    mistakes = []
    if skip and other:
        did.append(f"mes SKIP : {statistics.mean(skip):+.0f} % · les autres : {statistics.mean(other):+.0f} %")
        if statistics.mean(skip) >= statistics.mean(other):
            mistakes.append("mes SKIP n'ont pas fait pire que les autres : ils ne prévoient pas les baisses")
    res = _gap_test(other, skip, k=1)
    sells = bool(coach.get("echo_skip_sells", False))
    if res["ok"] and not sells:
        e = coach.apply("ECHO", "echo_skip_sells", True, res, balance)
        change = f"un SKIP fait de nouveau vendre : {res['why']}" if e else "un SKIP devrait faire vendre (changement récent, j'attends)"
    else:
        change = ("un SKIP fait vendre" if sells else "un SKIP ne fait pas vendre") + f" · {res['why']}"
    return {"did": did, "mistakes": mistakes, "change": change}


def _test_echo(entry) -> dict:
    skip, other = _echo_groups(after=entry["t"])
    if len(skip) < 2 or len(other) < 2:
        return {"n": 0}
    return {"n": min(len(skip), len(other)), "mean": statistics.mean(other) - statistics.mean(skip)}


# ---------------------------------------------------------------- TREND
GATE = 0.5


def _dials() -> dict:
    """mint -> the regime dial when GARDE passed it (checks.csv, logged since Oct 20)."""
    from config import LOG
    out = {}
    if os.path.exists(LOG):
        with open(LOG, newline="") as f:
            for r in csv.DictReader(f):
                if r.get("verdict") in ("PASS", "BUY") and r.get("dial") not in (None, "") and r["mint"] not in out:
                    out[r["mint"]] = float(r["dial"])
    return out


def _dial_groups(after: float = 0) -> tuple[list[float], list[float]]:
    """Passes followed 6 h, split by the dial at the verdict: (red, under GATE) and (green)."""
    dials = _dials()
    red, green = [], []
    for d in lessons(("pass",)):
        x = dials.get(d["row"]["mint"])
        if float(d["row"]["t"]) <= after or x is None:
            continue
        (red if x < GATE else green).append(d["y"])
    return red, green


def _whipsaws(fills: list[dict]) -> list[str]:
    """Sales under the price of the buy before them: the rule's known cost, a trend that was not one."""
    last_buy, out = {}, []
    for f in fills:
        if f["side"] == "achat":
            last_buy[f["asset"]] = float(f["price"])
        elif f["asset"] in last_buy and float(f["price"]) < last_buy[f["asset"]]:
            out.append(f"{f['asset']} {(float(f['price']) / last_buy.pop(f['asset']) - 1) * 100:+.1f} %")
    return out


def trend(balance: float | None) -> dict:
    import majors
    s = majors.summary()
    did = []
    if s["equity"] is not None:
        held = [a["asset"] for a in s["assets"] if a["usd"]]
        did.append(f"TENDANCE {s['equity']:.2f} $ ({(s['equity'] / s['bankroll'] - 1) * 100:+.1f} %), {s['n_fills']} ordres, "
                   f"en position : {', '.join(held) or 'rien'}")
    for r in (s["bt"].get("runs") or [])[:6]:
        did.append(f"backtest {r['name']} ({r['from'][:7]} → {r['to'][:7]}) : {r['verdict']} · {r['why']}")
    mistakes = []
    if (w := _whipsaws(majors.fills())):
        mistakes.append(f"{len(w)} aller-retour(s) perdant(s), le coût connu de la règle : " + ", ".join(w[-4:]))
    red, green = _dial_groups()
    mean = lambda xs: f"{statistics.mean(xs):+.1f} %" if xs else "—"
    did.append(f"memecoins PASS suivis 6 h : cadran rouge (< {GATE}) {mean(red)} sur {len(red)}, vert {mean(green)} sur {len(green)}")
    res = _gap_test(green, red, k=1)
    gate = coach.get("meme_dial_gate")
    if gate is None and res["ok"] and statistics.mean(red) < 0:
        e = coach.apply("TREND", "meme_dial_gate", GATE, res, balance)
        change = (f"les memecoins se mettent en retrait sous un cadran de {GATE} : {res['why']}" if e else
                  "le retrait des memecoins en régime rouge est justifié (changement récent, j'attends)")
    else:
        change = (f"memecoins en retrait sous un cadran de {gate}" if gate is not None else
                  "les memecoins tradent quel que soit le cadran") + f" · rouge contre vert : {res['why']}"
    return {"did": did, "mistakes": mistakes, "change": change}


def _test_gate(entry) -> dict:
    """After the gate: the red-regime passes it kept the desk out of must have lost money."""
    red, _ = _dial_groups(after=entry["t"])
    if len(red) < 2:
        return {"n": 0}
    return {"n": len(red), "mean": -statistics.mean(red)}


# ---------------------------------------------------------------- AUDIT
def run_all(balance: float | None) -> dict:
    """Every self-review, then the referee: re-test past changes, then the circuit breaker."""
    out = {}
    for name, fn in (("VIGIE", vigie), ("GARDE", garde), ("SCOUT", scout), ("ECHO", echo), ("TREND", trend)):
        try:
            out[name] = fn(balance)
        except Exception as e:
            out[name] = {"did": [], "mistakes": [], "change": f"revue impossible : {str(e)[:120]}"}
    judged = coach.evaluate({"exit_profile": _test_exit, "echo_skip_sells": _test_echo, "meme_dial_gate": _test_gate})
    tripped = coach.circuit(balance) if balance is not None else []
    out["AUDIT"] = {"did": [f"{len(coach.journal())} changements au journal, "
                            f"{sum(1 for e in coach.journal() if e['status'] == 'active')} en test"],
                    "mistakes": [f"annulé : {e['agent']} « {e['key']} » ({e.get('undone_why') or 'disjoncteur'})"
                                 for e in judged + tripped if e["status"] == "rolled_back" or e in tripped],
                    "change": "; ".join(f"confirmé : {e['agent']} « {e['key']} » → {e['new']}"
                                        for e in judged if e["status"] == "confirmed") or "rien à juger pour l'instant"}
    coach.save_reviews(out)
    return out
