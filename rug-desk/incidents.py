# incidents.py
# when the balance falls, AUDIT finds out why, and the desk answers in proportion. most falls are noise:
# five memecoins held at once move the balance by several dollars an hour with nothing wrong. reacting to
# noise is how a desk ends up revenge trading (bigger, faster, worse trades to win a loss back). so:
#
#   1. measure the noise   the balance's own 10-min moves over the last day, and what the open positions
#                          should move in an hour given their own volatility (VIGIE's price paths)
#   2. grade the fall      a NOTE: past 2x the noise and $5 in 10 min. explained in one line, nothing changes
#                          an INCIDENT: past 3x the noise and 3% of the bankroll in an hour, or a rug exit
#                          (pool pulled, ECHO's SCAM, contagion), or a whole ticket lost
#   3. find the cause      a rug (GARDE let it through), the market (most positions down with SOL/the dial),
#                          one position (normal for a memecoin), or several together (look at what they share)
#   4. answer              on an INCIDENT only: no new entry for 30 min (the cooling-off), ECHO re-reads every
#                          open position on X at once, VIGIE sells what shares wallets or a funder with a rug
#                          (agents.on_rug), the lesson is written. never a bigger ticket, never a looser rule
#   5. size by drawdown    the Turtle rule: every 10% of the bankroll lost from the peak cuts the tickets by
#                          20%, three steps at most, and they grow back as the balance does. the way back up
#                          is the same edge with less at risk, never a bet to win the loss back
#   6. learn               every incident is kept (data/incidents.jsonl). a cause that comes back (3 rugs in
#                          7 days sharing a trait the other buys rarely have) is reported, and the guarded
#                          learners (learn.py, shadow.py, coach.py) are the ones that change rules, on evidence
import csv, json, math, os, statistics, time
from config import DATA, EQUITY, PAPER_BANKROLL_USD
import atomic

LOG = os.path.join(DATA, "incidents.jsonl")
STATE = os.path.join(DATA, "incident_state.json")
URGENT = os.path.join(DATA, "x_urgent.json")
NOTE_SIGMA, NOTE_FLOOR_USD = 2.0, 5.0
INCIDENT_SIGMA, INCIDENT_PCT = 3.0, 3.0
TICKET_LOST_PCT = -40.0                  # a close this bad is an incident whatever the balance does
PAUSE_MIN = 30
NOTE_EVERY_S = 30 * 60
RUG_EXITS = ("liquidity_pulled", "pool_gone", "x_scam", "contagion")
DD_STEP_PCT, DD_CUT, DD_STEPS = 10.0, 0.8, 3
PATTERN_N, PATTERN_DAYS = 3, 7


def _read(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write(path, obj):
    os.makedirs(DATA, exist_ok=True)
    tmp = atomic.tmp(path)
    with open(tmp, "w") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def points(since: float) -> list[tuple[float, float]]:
    """(t, balance) from VIGIE's balance log, since the balance restart at the earliest."""
    import book
    since = max(since, book.reset_info().get("t", 0))
    out = []
    try:
        with open(EQUITY) as f:
            next(f, None)
            for line in f:
                parts = line.split(",")
                try:
                    t, b = float(parts[0]), float(parts[1])
                except (ValueError, IndexError):
                    continue
                if t >= since:
                    out.append((t, b))
    except OSError:
        pass
    return out


def noise(pts: list[tuple[float, float]]) -> float:
    """The usual size of a 10-min move of the balance (std of 10-min changes). $5 until there is a day of it."""
    bins = {}
    for t, b in pts:
        bins[int(t // 600)] = b
    keys = sorted(bins)
    diffs = [bins[b] - bins[a] for a, b in zip(keys, keys[1:]) if b == a + 1]
    if len(diffs) < 6:
        return 0.005 * PAPER_BANKROLL_USD
    return max(statistics.pstdev(diffs), 1.0)


def expected_hour() -> float:
    """What the open positions should move in an hour, in $, from their own last-hour volatility."""
    import book, exits, paths
    now, var = time.time(), 0.0
    for m, p in book.load().items():
        hist = paths.load(m, since=now - 3600)
        if not hist:
            continue
        vol = exits.volatility_pct(hist) or 10.0          # avg 5-min range in %; a memecoin without history: 10%
        value = p["qty"] * hist[-1]["price"]
        var += (value * vol / 200 * math.sqrt(12)) ** 2     # range/2 ~ a 5-min sigma, x sqrt(12) for an hour
    return math.sqrt(var)


def fall(pts: list[tuple[float, float]], window: float, now: float) -> tuple[float, float, float]:
    """(drop from the window's peak to now in $, the peak, when it was)."""
    w = [(t, b) for t, b in pts if t >= now - window]
    if len(w) < 2:
        return 0.0, 0.0, now
    t_peak, peak = max(w, key=lambda x: x[1])
    return peak - w[-1][1], peak, t_peak


def _closes_since(t0: float) -> list[dict]:
    import book
    after = book.reset_info().get("n_trades", 0)
    stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(t0))
    return [t for t in book.trades()[after:] if t["action"] != "open" and t["time"] >= stamp]


def _entry_facts(mint: str) -> dict:
    """What GARDE saw when it passed the token: the lesson an incident leaves."""
    from config import LOG as CHECKS
    row = {}
    try:
        with open(CHECKS, newline="") as f:
            for r in csv.DictReader(f):
                if r["mint"] == mint and r["verdict"] in ("PASS", "BUY"):
                    row = r
    except OSError:
        pass
    import chains, dossier
    src = (dossier.last(mint, "SCOUT") or {}).get("source")
    return {"chain": chains.split(mint)[0], "lane": row.get("lane"), "score": row.get("score"),
            "flags": row.get("flags") or "", "age_min": row.get("age_min"), "rc_score": row.get("rc_score"),
            "source": src}


def analyze(level: str, why: str, window: float, drop: float, peak: float, now: float, sigma: float) -> dict:
    """Who made the balance fall, and why. Reads files only, plus SOL's cached trend."""
    import book, paths, market, pending
    t0 = now - window
    try:
        marks = _read(os.path.join(DATA, "marks.json"), {}).get("marks", {})
    except Exception:
        marks = {}
    contrib = []
    for m, p in book.load().items():
        hist = paths.load(m, since=t0)
        px = marks.get(m) or (hist[-1]["price"] if hist else None)
        if hist and px:
            contrib.append({"symbol": p["symbol"], "mint": m, "usd": round(p["qty"] * (px - hist[0]["price"]), 2),
                            "pct": round((px / hist[0]["price"] - 1) * 100, 1)})
    closes = _closes_since(t0)

    def window_move(c):
        """A sale's part of the fall: what the sold tokens were worth when the window opened, against what they
        sold for. a winner that gave back from its peak before its trailing stop sold shows here as a loss, which
        is what it did to the balance, though its own pnl is a profit (Wick, Oct 20: +$17.80 sold, -$30 from peak)"""
        hist = paths.load(c["mint"], since=t0)
        sale_t = time.mktime(time.strptime(c["time"], "%Y-%m-%d %H:%M")) + 59
        at_sale = [h for h in hist if h["t"] <= sale_t and h["price"] > 0]
        if not hist or not at_sale or hist[0]["price"] <= 0:
            return float(c["pnl"])
        usd = float(c["usd"] or 0)
        return usd * (1 - hist[0]["price"] / at_sale[-1]["price"])
    realized = [{"symbol": c["symbol"], "mint": c["mint"], "usd": round(window_move(c), 2), "pnl": round(float(c["pnl"]), 2),
                 "reason": c["reason"], "sold": True} for c in closes]
    rugs = [c for c in realized if c["reason"] in RUG_EXITS]
    moves = sorted(contrib + realized, key=lambda c: c["usd"])
    lost = -sum(c["usd"] for c in moves if c["usd"] < 0) or 1e-9
    down = [c for c in contrib if c["pct"] <= -10]
    regime = market.sol_regime() or {}
    try:
        import majors
        dial = majors.dial_value()
    except Exception:
        dial = None
    if rugs:
        cause = "rug"
        detail = "sortie " + ", ".join(f"${r['symbol']} ({r['reason']}, {r['pnl']:+.2f} $)" for r in rugs)
    elif contrib and len(down) >= max(2, 0.6 * len(contrib)) and ((regime.get("sol_1h") or 0) <= -2 or (dial is not None and dial < 0.5)):
        cause = "marché"
        detail = f"{len(down)}/{len(contrib)} positions en baisse avec le marché (SOL 1 h {regime.get('sol_1h')} %, cadran {dial})"
    elif moves and moves[0]["usd"] < 0 and -moves[0]["usd"] >= 0.7 * lost:
        cause = "une position"
        m0 = moves[0]
        detail = f"${m0['symbol']} fait {-m0['usd'] / lost * 100:.0f} % de la baisse ({m0['usd']:+.2f} $)" + (
            f" : redescendu de son plus haut avant que sa sortie ({m0['reason']}) ne vende, le trade reste à {m0['pnl']:+.2f} $"
            if m0.get("sold") and m0["pnl"] > 0 else "")
    elif not moves:
        cause = "non attribuée"
        detail = "aucune position ouverte ni vente dans la fenêtre : relevé de prix à vérifier"
    else:
        cause = "plusieurs positions"
        chains_down = {}
        for c in down:
            ch = c["mint"].split(":")[0] if ":" in c["mint"] else "solana"
            chains_down[ch] = chains_down.get(ch, 0) + 1
        detail = f"{len(down)} positions à -10 % ou pire" + (", même chaîne : " + ", ".join(f"{k} {v}" for k, v in chains_down.items() if v >= 2)
                                                         if any(v >= 2 for v in chains_down.values()) else "")
    expected = expected_hour()
    normal = level == "note" and not rugs and drop <= max(2 * expected, 2 * sigma)
    rec = {"t": now, "time": time.strftime("%Y-%m-%d %H:%M", time.localtime(now)), "level": level, "why": why,
           "window_min": round(window / 60), "drop": round(drop, 2), "peak": round(peak, 2), "sigma": round(sigma, 2),
           "expected_1h": round(expected, 2), "cause": cause, "detail": detail, "moves": moves[:6],
           "sol_1h": regime.get("sol_1h"), "dial": dial, "echo_gap_min": pending.echo_gap_min(), "normal": normal,
           "lessons": {r["mint"]: _entry_facts(r["mint"]) for r in rugs}}
    rec["text"] = describe(rec)
    return rec


def describe(r: dict) -> str:
    head = (f"-{r['drop']:.2f} $ en {r['window_min']} min (le bruit habituel : ±{r['sigma']:.2f} $ par 10 min"
            + (f", les positions bougent de ±{r['expected_1h']:.2f} $ par heure)" if r["expected_1h"] else ")"))
    if r["level"] == "note":
        tail = ("perte normale pour des memecoins, aucune règle n'a cassé : les sorties de VIGIE font leur travail, rien ne change"
                if r["normal"] else "plus que d'habitude : surveillé, rien ne change tant que ce n'est pas un incident")
        return f"ANALYSE · {head} · cause : {r['cause']}, {r['detail']} · {tail}"
    act = f"pause de {PAUSE_MIN} min sur les achats, ECHO relit toutes les positions sur X"
    if r["cause"] == "rug":
        act += ", VIGIE vend ce qui partage des wallets ou un financeur avec le rug, dev et financeur sur liste noire"
    if r.get("echo_gap_min") is not None and r["echo_gap_min"] > 30:
        act += f" · ATTENTION : ECHO n'a rien lu depuis {r['echo_gap_min']:.0f} min"
    return f"INCIDENT · {head} · cause : {r['cause']}, {r['detail']} · réponse : {act} · jamais de mise plus grosse pour se refaire"


# ---------------------------------------------------------------- the answer
def prudence() -> dict:
    """The Turtle rule on the drawdown from the balance's peak since the restart: x0.8 per 10% of the bankroll."""
    pts = points(0)
    if not pts:
        return {"factor": 1.0, "dd_pct": 0.0}
    peak = max(PAPER_BANKROLL_USD, max(b for _, b in pts))
    dd = max(0.0, (peak - pts[-1][1]) / PAPER_BANKROLL_USD * 100)
    steps = min(DD_STEPS, int(dd // DD_STEP_PCT))
    return {"factor": round(DD_CUT ** steps, 3), "dd_pct": round(dd, 1), "peak": round(peak, 2), "steps": steps}


def paused() -> float:
    """Seconds left in the cooling-off after an incident, 0 if none."""
    return max(0.0, _read(STATE, {}).get("pause_until", 0) - time.time())


def urgent() -> dict:
    return _read(URGENT, {})


def tick(now: float | None = None) -> list[dict]:
    """AUDIT's watch on the balance, every minute from the main loop. Files only: cheap. Returns new records."""
    import book
    now = now or time.time()
    st = _read(STATE, {})
    pts = points(now - 86400)
    sigma = noise([p for p in pts if p[0] < now - 3600])    # the noise before the fall, not the fall itself
    out = []
    rows = book.trades()
    start = max(st.get("seen", len(rows)), book.reset_info().get("n_trades", 0))
    st["seen"] = len(rows)                     # first run: nothing old is replayed as new

    def lost_pct(t):                           # a close's result on what it cost (proceeds - pnl)
        basis = float(t["usd"] or 0) - float(t["pnl"] or 0)
        return float(t["pnl"] or 0) / basis * 100 if basis > 0 else 0.0
    bad = [t for t in rows[start:] if t["action"] != "open"
           and (t["reason"] in RUG_EXITS or lost_pct(t) <= TICKET_LOST_PCT)]
    d60, p60, _ = fall(pts, 3600, now)
    d10, p10, _ = fall(pts, 600, now)
    incident_bar = max(INCIDENT_SIGMA * sigma * math.sqrt(6), INCIDENT_PCT / 100 * PAPER_BANKROLL_USD)
    level = window = drop = peak = None
    if bad:
        level, why, window = "incident", "sortie : " + ", ".join(f"${t['symbol']} {t['reason']}" for t in bad), 3600
    elif d60 >= incident_bar and now - st.get("last_incident", 0) > 3600:
        level, why, window = "incident", f"baisse d'une heure au-delà de {incident_bar:.2f} $", 3600
    elif d10 >= max(NOTE_SIGMA * sigma, NOTE_FLOOR_USD) and now - st.get("last_note", 0) > NOTE_EVERY_S \
            and now - st.get("last_incident", 0) > NOTE_EVERY_S:
        level, why, window = "note", f"baisse de 10 min au-delà de {max(NOTE_SIGMA * sigma, NOTE_FLOOR_USD):.2f} $", 600
    if level:
        drop, peak = (d60, p60) if window == 3600 else (d10, p10)
        rec = analyze(level, why, window, drop, peak, now, sigma)
        st["last_" + level] = now
        if level == "incident":
            st["pause_until"] = now + PAUSE_MIN * 60
            _write(URGENT, {"t": now, "mints": list(book.load())})
        with open(LOG, "a") as f:
            f.write(json.dumps(rec) + "\n")
        out.append(rec)
    _write(STATE, st)
    return out


# ---------------------------------------------------------------- memory
def recent(n: int = 10, days: float | None = None) -> list[dict]:
    rows = []
    try:
        with open(LOG) as f:
            rows = [json.loads(l) for l in f if l.strip()]
    except (OSError, ValueError):
        pass
    if days:
        rows = [r for r in rows if time.time() - r["t"] < days * 86400]
    return rows[-n:] if n else rows


def patterns() -> list[str]:
    """Traits shared by PATTERN_N or more rugs of the last PATTERN_DAYS days, and rare among the other buys."""
    lessons = [l for r in recent(0, PATTERN_DAYS) for l in (r.get("lessons") or {}).values()]
    if len(lessons) < PATTERN_N:
        return []
    import book
    week = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - PATTERN_DAYS * 86400))
    bought = [t["mint"] for t in book.trades() if t["action"] == "open" and t["time"] >= week]
    base = [_entry_facts(m) for m in bought] or [{}]

    def traits(x: dict) -> set:
        s = {f"chaîne {x.get('chain')}", f"voie {x.get('lane')}", f"source {x.get('source')}"}
        s |= {f"signal {f}" for f in (x.get("flags") or "").split()}
        try:
            s.add("note < 60" if float(x.get("score") or 0) < 60 else "note ≥ 60")
        except ValueError:
            pass
        return {t for t in s if not t.endswith("None")}
    out = []
    counts = {}
    for l in lessons:
        for t in traits(l):
            counts[t] = counts.get(t, 0) + 1
    for t, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        share = sum(1 for b in base if t in traits(b)) / len(base)
        if n >= PATTERN_N and n / len(lessons) >= 2 * share:
            out.append(f"{n} rugs sur {len(lessons)} en {PATTERN_DAYS} j avaient « {t} », contre {share * 100:.0f} % des achats")
    return out[:3]


def status() -> dict:
    p = prudence()
    return {**p, "paused_s": round(paused()), "recent": recent(8), "patterns": patterns()}
