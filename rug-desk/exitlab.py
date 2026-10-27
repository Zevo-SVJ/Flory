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
SPEEDS = [1, 3, 6]          # the speed test: VIGIE looking at every tick (20 s), every 3rd (60 s), every 6th (2 min)
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
    "volume fade 25%": {"fade_ratio": 0.25},
    # Oct 21 review: the two biggest losers were a -36% stop and a -31% time stop, and 11 of 23 trades left by
    # the 6 h time stop near flat. the lab tests a tighter stop and a shorter clock on the same paths
    "stop -25%": {"stop_pct": -25},
    "time stop 3 h": {"time_stop_hours": 3},
    # Oct 26: Skide's style B (narrative momentum, hours to days), the exits Profit and Orangie describe:
    # stop -50%, stake back at x2, 25% at x5, 15% at x10, the rest on a 30% trail; no lock, stall or time stop
    # Oct 28: no clock at all left AXIS, BAN, XDP flat for 33-42 h, ~$120 that new tokens could not use.
    # a token not even +20% after 24 h is let go (the 6 h clock cut slow starters too early; the lab's
    # paths end 6 h after a sale, so this one is a judgment call, not a lab result)
    "regles B": {"stop_pct": -50, "ladder": [(100, 0.50), (400, 0.25), (900, 0.15)], "trail": "fixed",
                 "trail_pct": 30, "arm_pct": 100, "lock_after_pct": 10**9, "dump_drop_pct": 10**9,
                 "stall_min": 10**9, "time_stop_hours": 24, "time_stop_min_pct": 20},
    # Oct 27: Rugikk's article runs the same ladder start (half off at x2) with a -35% stop. the lab and
    # VIGIE's review judge it against "regles B" on the same paths; nothing changes unless it wins
    "regles B stop -35%": {"stop_pct": -35, "ladder": [(100, 0.50), (400, 0.25), (900, 0.15)], "trail": "fixed",
                           "trail_pct": 30, "arm_pct": 100, "lock_after_pct": 10**9, "dump_drop_pct": 10**9,
                           "stall_min": 10**9, "time_stop_hours": 24, "time_stop_min_pct": 20},
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


def fill(value: float, liq: float | None) -> float:
    """What a sale worth `value` at the quoted price really pays out of a pool holding `liq` $ (both sides).
    a constant-product pool pays R*V/(R+V) from its quote reserve R = liq/2: about V while V is small, and never
    more than the pool holds. without this a drained pool's glitch price was replayed as a fortune: tokens
    killed for an unlocked LP showed +3,427,854% per trade on Oct 21 (one at +263,944,237%), money no one
    could have taken out of a pool with nothing left in it. small sales (under 10% of R) are left as quoted:
    their impact is already in the desk's costs"""
    if liq is None:
        return value
    r = max(0.0, liq) / 2
    if value <= 0.1 * r:
        return value
    return r * value / (r + value) if r > 0 else 0.0


SPIKE_X = 10      # a tick 10x above (or below) the recent median...
SPIKE_LOOK = 5    # ...of the 5 ticks before it, that the next tick does not confirm, is a bad quote


def clean(path: list[dict]) -> list[dict]:
    """Drops one-tick price glitches before a replay. Oct 25 audit: NODF (Base) quoted x44,600 for one
    tick on a pool that held $1.99 the tick after, and the replay sold there: +317,496% for one shadow
    token, which alone pushed the mint_open row to +13,220%. a real move is still there one tick later"""
    out = path[:1]
    for i, s in enumerate(path[1:], 1):
        prev = sorted(p["price"] for p in out[-SPIKE_LOOK:] if p["price"] > 0)
        nxt = path[i + 1]["price"] if i + 1 < len(path) else None
        if prev and s["price"] > 0:
            med = prev[len(prev) // 2]
            up = s["price"] > SPIKE_X * med and (nxt is None or nxt < s["price"] / 2)
            down = s["price"] < med / SPIKE_X and (nxt is None or nxt > 2 * s["price"])
            if up or down:
                continue
        out.append(s)
    return out


def simulate(path: list[dict], params: dict) -> float | None:
    """Replay one exit profile on one recorded path. Returns pnl in $ for one ticket."""
    path = clean(path)
    if len(path) < 2 or path[0]["price"] <= 0:
        return None
    entry = path[0]["price"]
    pos = {"entry": entry, "qty0": TICKET_USD / entry, "qty": TICKET_USD / entry, "peak": entry,
           "peak_t": path[0]["t"], "liq0": path[0]["liq"] or 0, "opened": path[0]["t"], "steps": 0}
    pnl = 0.0
    liq = path[0]["liq"]
    for s in path[1:]:
        if s.get("liq") is not None:
            liq = s["liq"]
        if s["price"] > pos["peak"]:
            pos["peak"], pos["peak_t"] = s["price"], s["t"]
        d = exits.decide(pos, s, params)
        if not d:
            continue
        frac, why = d
        q = min(pos["qty"], pos["qty0"] * frac)
        pnl += fill(q * s["price"], liq) - q * entry
        pos["qty"] -= q
        if why.startswith("take_profit"):
            pos["steps"] += 1
        if pos["qty"] <= pos["qty0"] * 1e-6:
            return pnl
    return pnl + fill(pos["qty"] * path[-1]["price"], liq) - pos["qty"] * entry   # still open at the end: marked


def run() -> dict:
    """Replay every profile on every closed trade. Returns the ranking, and switches if autotune allows."""
    current = exits.active()
    trades = trades_to_replay()
    replays = []
    raw = []
    for t in trades:
        opened = time.mktime(time.strptime(t["opened"], "%Y-%m-%d %H:%M"))
        path = paths.load(t["mint"], since=opened - 60)
        if len(path) >= 10:
            raw.append(path)
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
            "switched": switched, "active": active_name, "min_trades": MIN_TRADES, "autotune": EXIT_AUTOTUNE,
            "speed": speed_test(raw, exits.active())}


def speed_test(raw: list[list[dict]], params: dict) -> list[dict]:
    """Does VIGIE's speed matter? The active profile replayed as if VIGIE looked every 20 s, 60 s
    and 2 min. If 60 s barely does worse than 20 s, going faster than 20 s won't pay either."""
    out = []
    for k in SPEEDS:
        pnls = [simulate(exits.features(path[::k]), params) for path in raw]
        pnls = [p for p in pnls if p is not None]
        step = round(sum(path[i + 1]["t"] - path[i]["t"] for path in raw for i in range(len(path) - 1))
                     / max(1, sum(len(path) - 1 for path in raw))) * k if raw else 20 * k
        out.append({"every_s": step, "n": len(pnls), "pnl": round(sum(pnls), 2),
                    "win": sum(1 for p in pnls if p > 0)})
    return out


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
