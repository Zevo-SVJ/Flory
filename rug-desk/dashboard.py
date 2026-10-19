# dashboard.py
# Claude Bot's private dashboard. it reads the desk's files and never writes, trades or calls an API:
# live prices come from VIGIE (data/marks.json), so opening the page costs nothing.
# start it:  python3 dashboard.py      then open http://localhost:8765 (only this Mac, unless DASH_HOST is set)
import csv, json, os, re, time
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from config import (DATA, LOG, PAPER, JUDGE, TICKET_USD, HERE, EQUITY, PAPER_BANKROLL_USD,
                    DAILY_LOSS_HALT_USD, MEGA_PROFIT_PCT, SCHEDULE, MIN_SCORE)
import book, events, audit, pending, market, ruggers, edge, smart

PORT = 8765
X_READS = os.path.join(DATA, "x_reads.csv")
HEARTBEAT = os.path.join(DATA, "heartbeat.json")
MARKS = os.path.join(DATA, "marks.json")
INBOX = os.path.join(DATA, "inbox.txt")
SOLANA_ADDRESS = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
RANGES = {"1h": 3600, "24h": 86400, "7j": 7 * 86400, "tout": None}

AGENTS = [   # fixed order = fixed color slot on the page
    ("VIGIE", "surveille les positions", "prix toutes les 20 s, stops, prises de profit"),
    ("SCOUT", "trouve les tokens", "graduations pump.fun, tendances, toutes les 3 min"),
    ("GARDE", "tue les rugs", "pool, nom, contrat, holders, lecture approfondie"),
    ("ECHO", "lit X", "Claude dans Chrome, verdict BUY/SKIP par PASS"),
    ("AUDIT", "apprend et rend compte", "re-prix des verdicts 6 h après, rapports du soir et du matin"),
]


def _csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _json(path: str, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def curve(range_s: int | None, now: float) -> list[list[float]]:
    """Balance points [t, balance], thinned to ~400 so a week of 20-second ticks stays light."""
    pts, before = [], None
    start = None if range_s is None else now - range_s
    if os.path.exists(EQUITY):
        with open(EQUITY) as f:
            next(f, None)
            for line in f:
                t, bal = line.split(",")[:2]
                t = float(t)
                if start is None or t >= start:
                    pts.append([t, float(bal)])
                else:
                    before = [start, float(bal)]   # the balance as the window opens
    if before:
        pts.insert(0, before)
    if len(pts) > 400:
        step = len(pts) / 399
        pts = [pts[int(i * step)] for i in range(399)] + [pts[-1]]
    return pts


def first_point() -> float | None:
    """When the balance log starts: the auto range shows everything until there is a full day."""
    if not os.path.exists(EQUITY):
        return None
    with open(EQUITY) as f:
        next(f, None)
        line = f.readline()
    return float(line.split(",")[0]) if line else None


def megas(since: float | None) -> list[dict]:
    """Every MEGA sale in the window, not just the ones still in the activity log's tail."""
    out = []
    if os.path.exists(events.EVENTS):
        with open(events.EVENTS) as f:
            for line in f:
                if '"kind": "sell"' not in line:
                    continue
                e = json.loads(line)
                if (e.get("pct") or 0) >= MEGA_PROFIT_PCT and (since is None or e["t"] >= since):
                    out.append({"t": e["t"], "symbol": e.get("symbol"), "pct": e["pct"], "pnl": e.get("pnl")})
    return out


def echo_status(waiting: dict, xreads: list[dict], now: float) -> dict:
    """ECHO runs in its own Claude session. It is late if a PASS waits more than 45 min unread."""
    last = max((r["time"] for r in xreads), default=None)
    oldest = min((v["since"] for v in waiting.values()), default=None)
    if oldest and now - oldest > 45 * 60:
        return {"status": "error", "msg": f"{len(waiting)} PASS non lu(s) : la session ECHO est-elle ouverte ?",
                "last": last}
    if waiting:
        return {"status": "work", "msg": f"{len(waiting)} PASS à lire", "last": last}
    # with nothing to read, the narrative scan (every 2 h) is ECHO's only sign of life
    try:
        quiet_h = (now - os.path.getmtime(os.path.join(DATA, "narratives.txt"))) / 3600
    except OSError:
        quiet_h = None
    if quiet_h is not None and quiet_h > 3:
        return {"status": "error", "msg": f"aucun scan X depuis {quiet_h:.0f} h : la boucle ECHO tourne-t-elle ?",
                "last": last}
    return {"status": "idle", "msg": f"{len(xreads)} lecture(s) X faite(s)" if xreads else "attend un PASS",
            "last": last}


def last_report() -> str | None:
    """PLUME's latest evening report or morning brief, from the event log."""
    text = None
    if os.path.exists(events.EVENTS):
        with open(events.EVENTS) as f:
            for line in f:
                if '"kind": "report"' in line:
                    text = json.loads(line).get("text")
    return text


_card = {"t": 0.0, "card": None}
_shadow = {"t": 0.0, "v": None}


def learn_state() -> dict:
    import learn
    m = learn.load()
    return {k: m.get(k) for k in ("t", "n", "trusted", "why", "test_n", "test_avg", "picks", "pick_avg")} | \
        {"lessons": [learn.explain(l) for l in m.get("lessons", [])], "min": learn.MIN_TRAIN + learn.MIN_TEST}


def shadow_state() -> dict | None:
    """GARDE's kills bought in shadow, replayed: cached 2 min (each replay reads a price path)."""
    if time.time() - _shadow["t"] > 120:
        import shadow
        try:
            _shadow["v"] = {**shadow.results(), "waived": sorted(shadow.waived())}
        except Exception:
            _shadow["v"] = None
        _shadow["t"] = time.time()
    return _shadow["v"]


def backtest_state() -> dict:
    """The cumulative backtest for AUDIT's panel: the last run's scorecard (computed here, cached, until
    a first run has written one), its history, and when the next run starts."""
    import backtest
    st = _json(backtest.STATE, {})
    card = st.get("card")
    if not card:
        if time.time() - _card["t"] > 600:
            try:
                _card["card"] = backtest.scorecard()
            except Exception:
                _card["card"] = None
            _card["t"] = time.time()
        card = _card["card"]
    nxt = st.get("started", 0) + SCHEDULE["backtest_every_h"] * 3600
    running = backtest.alive(st)
    return {"card": card, "history": backtest.history(), "running": running, "finished": st.get("finished"),
            "next": nxt if st.get("started") else None, "early_error": st.get("early_error"),
            "momentum_error": st.get("momentum_error"), "every_h": SCHEDULE["backtest_every_h"]}


def state(range_key: str = "auto") -> dict:
    now = time.time()
    first = first_point()
    auto = range_key not in RANGES
    if auto:      # everything until the desk has a full day of history, then the last 24 h
        range_key = "tout" if first is None or now - first < 86400 else "24h"
    range_s = RANGES[range_key]
    checks, trades, xreads = _csv(LOG), book.trades(), _csv(X_READS)
    positions = book.load()
    marks = _json(MARKS, {"t": 0, "marks": {}})
    live = marks.get("marks", {})

    open_rows, unrealized = [], 0.0
    for mint, p in positions.items():
        price = live.get(mint)
        pnl = p["qty"] * (price - p["entry"]) if price else 0.0
        unrealized += pnl
        open_rows.append({
            "mint": mint, "symbol": p["symbol"], "entry": p["entry"], "price": price,
            "pct": (price / p["entry"] - 1) * 100 if price else None,
            "peak_pct": (p["peak"] / p["entry"] - 1) * 100, "pnl": pnl if price else None,
            "left_pct": p["qty"] / p["qty0"] * 100, "hours": (now - p["opened"]) / 3600,
            "cost": p["qty"] * p["entry"],          # what is still tied up: tickets now vary with the setup
        })

    realized = book.realized()
    exits = [t for t in trades if t["action"] != "open"]
    per_mint = Counter()
    for t in exits:
        per_mint[t["mint"]] += float(t["pnl"])
    closed = {t["mint"] for t in trades if t["action"] == "close"}
    wins = sum(1 for m in closed if per_mint[m] > 0)
    for r in open_rows:
        per_mint[r["mint"]] += r["pnl"] or 0

    latest = {}
    for r in checks:
        latest[r["mint"]] = r
    rows = list(latest.values())
    kills = Counter("source en panne" if " failed" in (r["reason"] or "") else r["reason"]
                    for r in rows if r["verdict"] == "SKIP")
    passes = [r for r in rows if r["verdict"] in ("PASS", "BUY")]

    xr = {r["mint"]: {**r, "verdict": "SKIP" if r["verdict"].upper() == "SCAM" else r["verdict"]} for r in xreads}
    waiting = pending.load()
    bought = {t["mint"] for t in trades if t["action"] == "open"}

    def status(r):
        if r["mint"] in positions:
            return "en position"
        if r["mint"] in waiting:
            return "attend X"
        if r["mint"] in bought:
            return "vendu"
        if r.get("score") and int(r["score"]) < MIN_SCORE:
            return "note trop basse"
        return "écarté par X" if r["mint"] in xr else "non acheté"

    experiment = [{"time": r["time"], "mint": r["mint"], "symbol": r["symbol"],
                   "x": xr[r["mint"]]["verdict"] if r["mint"] in xr else None,
                   "why": xr[r["mint"]]["raison"] if r["mint"] in xr else None,
                   "score": int(r["score"]) if r.get("score") else None, "flags": r.get("flags") or "",
                   "status": status(r), "pnl": round(per_mint[r["mint"]], 2), "open": r["mint"] in positions}
                  for r in sorted(passes, key=lambda r: r["time"], reverse=True)]
    groups = {}
    for g in ("BUY", "SKIP", "NO_X", None):
        sel = [e for e in experiment if e["x"] == g]
        groups[g or "non lu"] = {"n": len(sel), "pnl": round(sum(e["pnl"] for e in sel), 2)}

    st = events.agents()
    st["ECHO"] = echo_status(waiting, xreads, now)
    agents = [{"name": n, "role": role, "detail": detail, **st.get(n, {"status": "idle", "msg": "pas encore lancé"})}
              for n, role, detail in AGENTS]
    import facts, stracker, sources, tgbot
    src = sources.load()

    hb = _json(HEARTBEAT, None)
    balance = PAPER_BANKROLL_USD + realized + unrealized
    return {
        "now": now, "paper": PAPER, "judge": JUDGE, "ticket": TICKET_USD,
        "alive": bool(hb and now - hb["time"] < 120),
        "bankroll": PAPER_BANKROLL_USD, "balance": balance, "realized": realized, "unrealized": unrealized,
        "pnl": balance - PAPER_BANKROLL_USD, "today": book.today_pnl(), "loss_limit": DAILY_LOSS_HALT_USD,
        "cash": book.cash(positions), "marks_age": now - marks.get("t", 0),
        "wins": wins, "losses": len(closed) - wins, "mega_pct": MEGA_PROFIT_PCT,
        "curve": curve(range_s, now), "range": range_key, "range_s": range_s, "auto": auto,
        "megas": megas(None if range_s is None else now - range_s),
        "events": events.recent(40), "tasks": events.count(),
        "agents": agents, "open": sorted(open_rows, key=lambda r: -(r["pct"] or -1e9)),
        "experiment": experiment[:30], "groups": groups,
        "kills": [{"label": k, "n": v} for k, v in kills.most_common(8)],
        "audit": audit.summary(), "vigie_every": SCHEDULE["vigie_every_s"],
        "sol": market.sol_regime(),
        "breakdown": audit.breakdown(), "ruggers": len(ruggers.known()),
        "edge": edge.stats(), "smart": smart.known(), "living": edge.living(),
        "lab": _json(os.path.join(DATA, "exitlab.json"), {"trades": 0, "results": [], "active": "actif"}),
        # the agent panels: what each outside source last answered, which keys exist, PLUME's last words
        "sources": {k: v for k, v in src.items() if not k.endswith("_count")},
        "keys": {"helius": "helius" in facts.RPC_URL, "stracker": bool(stracker.key())},
        "stracker_today": sources.calls_today("stracker"), "stracker_cap": stracker.DAILY_CAP,
        "last_report": last_report(), "report_at": SCHEDULE["report_at"],
        "backtest": (bt := backtest_state()), "bilan": edge.bilan(bt["card"]), "tgbot": tgbot.stats(), "shadow": shadow_state(), "learn": learn_state(),
        "reviews": __import__("coach").reviews(), "journal": __import__("coach").journal(last=20),
        "by_chain": edge.split(lambda t: __import__("chains").split(t["mint"])[0]),
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/api/state":
            rng = parse_qs(url.query).get("range", ["auto"])[0]
            body, kind = json.dumps(state(rng)).encode(), "application/json"
        elif url.path == "/api/dossier":
            import dossier
            mint = parse_qs(url.query).get("mint", [""])[0]
            if not SOLANA_ADDRESS.match(mint):
                self.send_error(400)
                return
            body, kind = json.dumps(dossier.load(mint)).encode(), "application/json"
        elif url.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "dashboard.html"), "rb") as f:
                body, kind = f.read(), "text/html; charset=utf-8"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        """Paste a CA in the page: it is queued for GARDE. The page itself never runs a check."""
        if urlparse(self.path).path != "/api/check":
            self.send_error(404)
            return
        try:
            n = min(int(self.headers.get("Content-Length") or 0), 2000)
            mint = str(json.loads(self.rfile.read(n) or b"{}").get("mint", "")).strip()
        except ValueError:
            mint = ""
        ok = bool(SOLANA_ADDRESS.match(mint))
        if ok:
            os.makedirs(DATA, exist_ok=True)
            with open(INBOX, "a") as f:
                f.write(mint + "\n")
        body = json.dumps({"ok": ok, "error": None if ok else "adresse Solana invalide"}).encode()
        self.send_response(200 if ok else 400)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):     # keep the terminal quiet
        pass


if __name__ == "__main__":
    print(f"dashboard: http://localhost:{PORT}   (Ctrl+C to stop)")
    # only this Mac by default. DASH_HOST=0.0.0.0 in .env opens it to your other devices: use it behind
    # Tailscale (a private network between your own devices), never with a port opened on the internet
    import env
    ThreadingHTTPServer((env.get("DASH_HOST") or "127.0.0.1", PORT), Handler).serve_forever()
