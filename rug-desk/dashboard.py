# dashboard.py
# Claude Bot's private dashboard. it reads the desk's files and never writes, trades or calls an API:
# live prices come from VIGIE (data/marks.json), so opening the page costs nothing.
# start it:  python3 dashboard.py      then open http://localhost:8765 (only reachable from this Mac)
import csv, json, os, re, time
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from config import (DATA, LOG, PAPER, JUDGE, TICKET_USD, HERE, EQUITY, PAPER_BANKROLL_USD,
                    DAILY_LOSS_HALT_USD, MEGA_PROFIT_PCT, SCHEDULE, MIN_SCORE)
import book, events, audit, pending

PORT = 8765
X_READS = os.path.join(DATA, "x_reads.csv")
HEARTBEAT = os.path.join(DATA, "heartbeat.json")
MARKS = os.path.join(DATA, "marks.json")
INBOX = os.path.join(DATA, "inbox.txt")
SOLANA_ADDRESS = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
RANGES = {"1h": 3600, "24h": 86400, "7j": 7 * 86400, "tout": None}

AGENTS = [   # fixed order = fixed color slot on the page
    ("VIGIE", "surveille les positions", "prix toutes les 20 s, stops, prises de profit"),
    ("SCOUT", "trouve les tokens", "nouveaux tokens DexScreener toutes les 10 min"),
    ("GARDE", "tue les rugs", "13 checks : pool, autorités, LP, holders, bundles"),
    ("ECHO", "lit X", "Claude dans Chrome, verdict BUY/SKIP par PASS"),
    ("AUDIT", "vérifie le filtre", "re-prix des verdicts 6 h après"),
    ("PLUME", "écrit le rapport", "bilan du soir à 21:30"),
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
    return {"status": "idle", "msg": f"{len(xreads)} lecture(s) X faite(s)" if xreads else "attend un PASS",
            "last": last}


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

    xr = {r["mint"]: r for r in xreads}
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
    for g in ("BUY", "SKIP", None):
        sel = [e for e in experiment if e["x"] == g]
        groups[g or "non lu"] = {"n": len(sel), "pnl": round(sum(e["pnl"] for e in sel), 2)}

    st = events.agents()
    st["ECHO"] = echo_status(waiting, xreads, now)
    agents = [{"name": n, "role": role, "detail": detail, **st.get(n, {"status": "idle", "msg": "pas encore lancé"})}
              for n, role, detail in AGENTS]

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
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/api/state":
            rng = parse_qs(url.query).get("range", ["auto"])[0]
            body, kind = json.dumps(state(rng)).encode(), "application/json"
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
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
