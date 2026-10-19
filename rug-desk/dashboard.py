# dashboard.py
# a private page that reads the desk's files. it never writes anything and never trades.
# start it:  python3 dashboard.py      then open http://localhost:8765
# it only listens on your own machine (127.0.0.1), nobody else can open it.
import csv, json, os, time
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from config import DATA, LOG, TRADES, PAPER, JUDGE, TICKET_USD, EXIT, HERE
import book, market

PORT = 8765
X_READS = os.path.join(DATA, "x_reads.csv")
HEARTBEAT = os.path.join(DATA, "heartbeat.json")


def _csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _stage(r: dict) -> str:
    reason = r.get("reason") or ""
    if " failed" in reason:
        return "source_down"
    return r.get("stage") or "?"


def state() -> dict:
    now = time.time()
    checks, trades, xreads = _csv(LOG), book.trades(), _csv(X_READS)
    positions = book.load()

    # live prices for open positions, one call. a failure leaves them unpriced, never guessed
    live, price_error = {}, None
    if positions:
        try:
            live = market.pools(list(positions))
        except Exception as e:
            price_error = str(e)

    open_rows, unrealized = [], 0.0
    for mint, p in positions.items():
        m = live.get(mint)
        price = m["price"] if m and m["price"] > 0 else None
        pnl = p["qty"] * (price - p["entry"]) if price else None
        unrealized += pnl or 0
        open_rows.append({
            "mint": mint, "symbol": p["symbol"], "entry": p["entry"], "price": price,
            "pct": (price / p["entry"] - 1) * 100 if price else None,
            "peak_pct": (p["peak"] / p["entry"] - 1) * 100,
            "pnl": pnl, "left_pct": p["qty"] / p["qty0"] * 100,
            "hours": (now - p["opened"]) / 3600, "steps": p["steps"],
            "liq": m["liq_usd"] if m else None, "liq0": p["liq0"],
            "url": m["url"] if m else f"https://dexscreener.com/solana/{mint}",
        })

    # realized pnl over time: every partial and close is one step of the curve
    exits = [t for t in trades if t["action"] != "open"]
    curve, total = [], 0.0
    for t in exits:
        total += float(t["pnl"])
        curve.append({"time": t["time"], "pnl": round(total, 2), "symbol": t["symbol"],
                      "step": float(t["pnl"]), "reason": t["reason"]})
    day = time.strftime("%Y-%m-%d")
    closes = [t for t in trades if t["action"] == "close"]

    # pnl per token, realized + still open, so a verdict can be judged against what happened
    per_mint = Counter()
    for t in exits:
        per_mint[t["mint"]] += float(t["pnl"])
    for r in open_rows:
        per_mint[r["mint"]] += r["pnl"] or 0
    wins = [m for m in {t["mint"] for t in closes} if per_mint[m] > 0]

    # the funnel uses the latest verdict per token: a retried token counts once
    latest = {}
    for r in checks:
        latest[r["mint"]] = r
    rows = list(latest.values())
    stages = Counter(_stage(r) if r["verdict"] == "SKIP" else "pass" for r in rows)
    n = len(rows)
    after_pool = n - stages["limits"] - stages["pool"] - stages["source_down"]
    funnel = [
        {"label": "Tokens analysés", "n": n},
        {"label": "Pool OK (liquidité, âge, ventes)", "n": after_pool},
        {"label": "Contrat OK (autorités, LP, holders)", "n": after_pool - stages["facts"]},
        {"label": "PASS du desk", "n": stages["pass"]},
    ]
    kills = Counter("source en panne" if _stage(r) == "source_down" else r["reason"]
                    for r in rows if r["verdict"] == "SKIP")

    # the experiment: every PASS, what X said, what the paper trade did
    xr = {r["mint"]: r for r in xreads}
    passes = [r for r in rows if r["verdict"] in ("PASS", "BUY")]
    experiment = []
    for r in sorted(passes, key=lambda r: r["time"], reverse=True):
        x = xr.get(r["mint"])
        experiment.append({
            "time": r["time"], "mint": r["mint"], "symbol": r["symbol"],
            "x_verdict": x["verdict"] if x else None, "x_reason": x["raison"] if x else None,
            "pnl": round(per_mint[r["mint"]], 2), "open": r["mint"] in positions,
        })
    groups = {}
    for g in ("BUY", "SKIP", None):
        sel = [e for e in experiment if e["x_verdict"] == g]
        groups[g or "non lu"] = {"n": len(sel), "pnl": round(sum(e["pnl"] for e in sel), 2)}

    hb = None
    if os.path.exists(HEARTBEAT):
        with open(HEARTBEAT) as f:
            hb = json.load(f)

    return {
        "now": now, "paper": PAPER, "judge": JUDGE, "ticket": TICKET_USD, "exit": EXIT,
        "heartbeat_age_s": now - hb["time"] if hb else None,
        "realized": round(total, 2), "realized_today": round(book.today_pnl(), 2),
        "unrealized": round(unrealized, 2), "price_error": price_error,
        "closed": len(closes), "won": len(wins),
        "open": sorted(open_rows, key=lambda r: r["hours"]),
        "curve": curve, "funnel": funnel,
        "kills": [{"label": k, "n": v} for k, v in kills.most_common(8)],
        "experiment": experiment, "groups": groups,
        "trades": [t for t in reversed(exits)][:30],
        "checked_today": sum(1 for r in checks if r["time"].startswith(day)),
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/state":
            body, kind = json.dumps(state()).encode(), "application/json"
        elif self.path in ("/", "/index.html"):
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

    def log_message(self, *args):     # keep the terminal quiet
        pass


if __name__ == "__main__":
    print(f"dashboard: http://localhost:{PORT}   (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
