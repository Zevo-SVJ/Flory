# audit.py
# AUDIT: was the filter right? every verdict logged with a price is re-priced once, N hours later.
# a killed token that crashed = a good kill. a killed token that ran = a trade the filter cost you.
# this is the number that tells you whether to loosen or tighten a check.
import csv, os, time
from config import LOG, AUDIT, SCHEDULE, DATA
from market import pools
import ruggers, smart

FIELDS = ["time", "mint", "symbol", "stage", "verdict", "reason", "price0", "price_after",
          "change_pct", "hours"]
CRASH_PCT = -50          # down this much after N hours: the kill was right
RUG_PCT = -90            # down this much: the creator is blacklisted (ruggers.py)


def _done() -> set[str]:
    if not os.path.exists(AUDIT):
        return set()
    with open(AUDIT, newline="") as f:
        return {r["mint"] for r in csv.DictReader(f)}


def due() -> list[dict]:
    """Latest verdict per token, priced at the time, old enough, not audited yet."""
    if not os.path.exists(LOG):
        return []
    latest = {}
    with open(LOG, newline="") as f:
        for r in csv.DictReader(f):
            latest[r["mint"]] = r
    cutoff = time.strftime("%Y-%m-%d %H:%M",
                           time.localtime(time.time() - SCHEDULE["audit_after_hours"] * 3600))
    done = _done()
    return [r for r in latest.values()
            if r.get("price") not in (None, "", "0", "0.0") and r["time"] <= cutoff and r["mint"] not in done]


def audit(limit: int = 60) -> list[dict]:
    rows = due()[:limit]
    if not rows:
        return []
    live = pools([r["mint"] for r in rows])
    new = not os.path.exists(AUDIT)
    out = []
    with open(AUDIT, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        for r in rows:
            p0 = float(r["price"])
            m = live.get(r["mint"])
            p1 = m["price"] if m and m["price"] > 0 else 0.0     # pool gone counts as -100%
            hours = (time.time() - time.mktime(time.strptime(r["time"], "%Y-%m-%d %H:%M"))) / 3600
            row = {"time": time.strftime("%Y-%m-%d %H:%M"), "mint": r["mint"], "symbol": r["symbol"],
                   "stage": r["stage"], "verdict": r["verdict"], "reason": r["reason"], "price0": p0,
                   "price_after": p1, "change_pct": round((p1 / p0 - 1) * 100, 1), "hours": round(hours, 1)}
            w.writerow(row)
            out.append(row)
            import dossier
            dossier.add(r["mint"], "AUDIT", "6 h après", change_pct=row["change_pct"], hours=row["hours"],
                        verdict=r["verdict"], reason=r["reason"])
            smart.learn(r["mint"], row["change_pct"])     # the early holders of a runner or a crasher
            if row["change_pct"] <= RUG_PCT:          # near-total collapse: the creator goes on the blacklist
                ruggers.add(ruggers.dev_of(r["mint"]), r["mint"], r["symbol"],
                            f"{row['change_pct']:+.0f}% {row['hours']:.0f}h after the verdict")
    return out


def summary() -> dict:
    """Share of killed vs passed tokens that crashed. A useful filter kills more crashers than it passes."""
    if not os.path.exists(AUDIT):
        empty = {"n": 0, "crashed": 0, "ran": 0}
        return {"killed": {"n": 0, "crashed": 0}, "passed": {"n": 0, "crashed": 0}, "missed": [],
                "x": {"BUY": dict(empty), "SKIP": dict(empty), "NO_X": dict(empty)},
                "regime": {"SOL up": dict(empty), "SOL down": dict(empty)}}
    with open(AUDIT, newline="") as f:
        rows = list(csv.DictReader(f))
    groups = {"killed": [r for r in rows if r["verdict"] == "SKIP" and " failed" not in (r["reason"] or "")],
              "passed": [r for r in rows if r["verdict"] in ("PASS", "BUY")]}
    out = {k: {"n": len(v), "crashed": sum(1 for r in v if float(r["change_pct"]) <= CRASH_PCT)}
           for k, v in groups.items()}
    # killed tokens that went up a lot: where the filter may be too strict
    missed = sorted((r for r in groups["killed"] if float(r["change_pct"]) >= 100),
                    key=lambda r: -float(r["change_pct"]))[:5]
    out["missed"] = [{"symbol": r["symbol"], "reason": r["reason"], "change_pct": float(r["change_pct"])}
                     for r in missed]

    # was ECHO right? every PASS it read, bought or not, scored the same way
    xr = {}
    path = os.path.join(DATA, "x_reads.csv")
    if os.path.exists(path):
        with open(path, newline="") as f:
            xr = {r["mint"]: r["verdict"].upper().replace("SCAM", "SKIP") for r in csv.DictReader(f) if r.get("mint")}
    def tally(sel):
        return {"n": len(sel), "crashed": sum(1 for r in sel if float(r["change_pct"]) <= CRASH_PCT),
                "ran": sum(1 for r in sel if float(r["change_pct"]) >= 100)}
    out["x"] = {v: tally([r for r in groups["passed"] if xr.get(r["mint"]) == v]) for v in ("BUY", "SKIP", "NO_X")}

    # did passes do worse when SOL was falling? the trend logged with each verdict decides the bucket
    sol = {}
    if os.path.exists(LOG):
        with open(LOG, newline="") as f:
            sol = {r["mint"]: r.get("sol_24h") for r in csv.DictReader(f) if r.get("sol_24h") not in (None, "")}
    out["regime"] = {"SOL up": tally([r for r in groups["passed"] if r["mint"] in sol and float(sol[r["mint"]]) >= 0]),
                     "SOL down": tally([r for r in groups["passed"] if r["mint"] in sol and float(sol[r["mint"]]) < 0])}
    return out


# which number in config.py each kill reason comes from, so the report can say what to question
KNOB = {"thin_pool": "min_liquidity_usd", "too_fresh": "min_age_min", "too_old": "max_age_hours",
        "top10_heavy": "max_top10_pct", "whale": "max_wallet_pct", "dev_holds": "max_dev_pct",
        "bundle_same_sol": "bundle_same_sol", "bundle_ladder": "bundle_ladder",
        "lp_unlocked": "min_lp_locked_pct", "lp_unverified": "min_lp_locked_pct (PumpSwap only)",
        "nobody_can_sell": "honeypot rule in market.py"}


def by_reason(min_n: int = 3) -> list[dict]:
    """Per kill reason, among audited tokens: how many crashed (good kill) and how many ran (missed)."""
    if not os.path.exists(AUDIT):
        return []
    with open(AUDIT, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["verdict"] == "SKIP" and " failed" not in (r["reason"] or "")]
    out = {}
    for r in rows:
        o = out.setdefault(r["reason"], {"reason": r["reason"], "n": 0, "crashed": 0, "ran": 0})
        o["n"] += 1
        o["crashed"] += float(r["change_pct"]) <= CRASH_PCT
        o["ran"] += float(r["change_pct"]) >= 100
    return [o for o in out.values() if o["n"] >= min_n]


if __name__ == "__main__":
    for r in audit():
        print(r["symbol"], r["verdict"], r["reason"], f"{r['change_pct']:+.0f}%")
    print(summary())


def breakdown() -> dict:
    """Where the desk wins and loses: closed positions grouped by entry hour and by the token's age
    at entry. The bot has no 2 AM tilt, but markets have quiet hours and late entries."""
    from config import TRADES
    if not os.path.exists(TRADES):
        return {"hour": [], "age": [], "tier": []}
    with open(TRADES, newline="") as f:
        trades = list(csv.DictReader(f))
    ages, tiers = {}, {}
    if os.path.exists(LOG):
        with open(LOG, newline="") as f:
            for r in csv.DictReader(f):
                if r.get("age_min") not in (None, ""):
                    ages[r["mint"]] = float(r["age_min"])
                if r.get("tier"):
                    tiers[r["mint"]] = r["tier"]
    opened, pnl, closed = {}, {}, set()
    for t in trades:
        if t["action"] == "open":
            opened[t["mint"]] = t["time"]
            pnl[t["mint"]] = 0.0
        else:
            pnl[t["mint"]] = pnl.get(t["mint"], 0.0) + float(t["pnl"])
            if t["action"] == "close":
                closed.add(t["mint"])
    hours = [("00-04", 0, 4), ("04-08", 4, 8), ("08-12", 8, 12), ("12-16", 12, 16), ("16-20", 16, 20), ("20-24", 20, 24)]
    age_b = [("< 3 h", 0, 180), ("3-12 h", 180, 720), ("12-36 h", 720, 2160), ("36-72 h", 2160, 10**9)]
    def group(buckets, key):
        out = []
        for name, lo, hi in buckets:
            sel = [m for m in closed if m in opened and key(m) is not None and lo <= key(m) < hi]
            out.append({"bucket": name, "n": len(sel), "pnl": round(sum(pnl[m] for m in sel), 2),
                        "win": sum(1 for m in sel if pnl[m] > 0)})
        return out
    # does a bigger ticket go with better trades? the tier size.py gave at entry, as 0/1/2
    rank = {"explore": -1, "base": 0, "strong": 1, "max": 2}     # explore: a full pass under MIN_SCORE, paper only
    tier_b = [("explore", -1, 0), ("base", 0, 1), ("strong", 1, 2), ("max", 2, 3)]
    return {"hour": group(hours, lambda m: int(opened[m][11:13])),
            "age": group(age_b, lambda m: ages.get(m)),
            "tier": group(tier_b, lambda m: rank.get(tiers.get(m)))}
