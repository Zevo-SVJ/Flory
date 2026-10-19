# exitlab.py
# the exit lab. no study can say when to sell YOUR tokens, so the desk measures it: every closed trade
# has its price path on disk (during the trade and 6 h after), and the lab replays each candidate exit
# profile on every path, as if it had been running instead.
#
# autotune: the lab switches the live profile only when a candidate beats the one in force on BOTH
# halves of the trades (oldest half, newest half), by a clear margin, with enough trades. one lucky
# token can't move the desk.
import csv, json, os, time
from config import EXIT, TRADES, TICKET_USD, EXIT_AUTOTUNE
import exits, paths

MIN_TRADES = 30             # below this, the lab reports but never switches
MIN_EDGE_USD = 5            # a candidate must beat the active profile by at least this much...
MIN_EDGE_SHARE = 0.20       # ...and by 20% of the active profile's absolute result, on each half

PROFILES = {
    "article": {"trail": "fixed", "trail_pct": 30, "arm_pct": 10**9, "lock_after_pct": 10**9,
                "dump_drop_pct": 10**9, "stall_min": 10**9},
    "chandelier k2": {"trail": "chandelier", "trail_k": 2},
    "chandelier k3": {"trail": "chandelier", "trail_k": 3},
    "chandelier k4": {"trail": "chandelier", "trail_k": 4},
    "fixed trail 20%": {"trail": "fixed", "trail_pct": 20},
    "fixed trail 40%": {"trail": "fixed", "trail_pct": 40},
    "ladder 25% x2 x3 x5 x10": {"ladder": [(100, 0.25), (200, 0.25), (400, 0.25), (900, 0.25)]},
    "early ladder +50% +100%": {"ladder": [(50, 0.33), (100, 0.33)]},
    "no ladder": {"ladder": []},
    "no stall exit": {"stall_min": 10**9},
    "arm trail at +20%": {"arm_pct": 20, "lock_after_pct": 20},
}


def trades_to_replay() -> list[dict]:
    """Every position that was opened and fully closed, with its entry."""
    if not os.path.exists(TRADES):
        return []
    with open(TRADES, newline="") as f:
        rows = list(csv.DictReader(f))
    opens, out = {}, []
    for r in rows:
        if r["action"] == "open":
            opens[r["mint"]] = r
        elif r["action"] == "close" and r["mint"] in opens:
            o = opens.pop(r["mint"])
            out.append({"mint": r["mint"], "symbol": r["symbol"], "opened": o["time"], "closed": r["time"]})
    return out


def simulate(path: list[dict], params: dict) -> float | None:
    """Replay one exit profile on one recorded path. Returns pnl in $ for one ticket."""
    if len(path) < 2 or path[0]["price"] <= 0:
        return None
    entry = path[0]["price"]
    pos = {"entry": entry, "qty0": TICKET_USD / entry, "qty": TICKET_USD / entry, "peak": entry,
           "peak_t": path[0]["t"], "liq0": path[0]["liq"] or 0, "opened": path[0]["t"], "steps": 0}
    pnl = 0.0
    for s in path[1:]:
        if s["price"] > pos["peak"]:
            pos["peak"], pos["peak_t"] = s["price"], s["t"]
        d = exits.decide(pos, s, params)
        if not d:
            continue
        frac, why = d
        q = min(pos["qty"], pos["qty0"] * frac)
        pnl += q * (s["price"] - entry)
        pos["qty"] -= q
        if why.startswith("take_profit"):
            pos["steps"] += 1
        if pos["qty"] <= pos["qty0"] * 1e-6:
            return pnl
    return pnl + pos["qty"] * (path[-1]["price"] - entry)     # still open at the end of the data: marked


def run() -> dict:
    """Replay every profile on every closed trade. Returns the ranking, and switches if autotune allows."""
    current = exits.active()
    trades = trades_to_replay()
    replays = []
    for t in trades:
        opened = time.mktime(time.strptime(t["opened"], "%Y-%m-%d %H:%M"))
        path = paths.load(t["mint"], since=opened - 60)
        if len(path) >= 10:
            replays.append((t, exits.features(path)))
    candidates = {"actif": current, **{name: {**EXIT, **over} for name, over in PROFILES.items()}}
    results = []
    for name, params in candidates.items():
        pnls = [simulate(path, params) for _, path in replays]
        pnls = [p for p in pnls if p is not None]
        half = len(pnls) // 2
        results.append({"name": name, "n": len(pnls), "pnl": round(sum(pnls), 2),
                        "win": sum(1 for p in pnls if p > 0), "first_half": round(sum(pnls[:half]), 2),
                        "second_half": round(sum(pnls[half:]), 2), "params": params})
    results.sort(key=lambda r: -r["pnl"])
    act = next(r for r in results if r["name"] == "actif")
    switched = None
    if EXIT_AUTOTUNE and act["n"] >= MIN_TRADES:
        for r in results:
            if r["name"] == "actif":
                break
            edge = lambda a, b: a - b >= max(MIN_EDGE_USD, MIN_EDGE_SHARE * abs(b))
            if edge(r["first_half"], act["first_half"]) and edge(r["second_half"], act["second_half"]):
                with open(exits.PROFILE, "w") as f:
                    json.dump({"name": r["name"], "since": time.time(), "params": r["params"],
                               "evidence": {k: r[k] for k in ("n", "pnl", "first_half", "second_half")},
                               "replaced": {k: act[k] for k in ("n", "pnl", "first_half", "second_half")}}, f)
                switched = r["name"]
                break
    active_name = "actif"
    if os.path.exists(exits.PROFILE):
        with open(exits.PROFILE) as f:
            active_name = json.load(f).get("name", "actif")
    return {"trades": len(replays), "results": [{k: v for k, v in r.items() if k != "params"} for r in results],
            "switched": switched, "active": active_name, "min_trades": MIN_TRADES}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
