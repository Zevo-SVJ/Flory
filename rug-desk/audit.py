# audit.py
# AUDIT: was the filter right? every verdict logged with a price is re-priced once, N hours later.
# a killed token that crashed = a good kill. a killed token that ran = a trade the filter cost you.
# this is the number that tells you whether to loosen or tighten a check.
import csv, os, time
from config import LOG, AUDIT, SCHEDULE, DATA
from market import pools

FIELDS = ["time", "mint", "symbol", "stage", "verdict", "reason", "price0", "price_after",
          "change_pct", "hours"]
CRASH_PCT = -50          # down this much after N hours: the kill was right


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
    return out


def summary() -> dict:
    """Share of killed vs passed tokens that crashed. A useful filter kills more crashers than it passes."""
    if not os.path.exists(AUDIT):
        empty = {"n": 0, "crashed": 0, "ran": 0}
        return {"killed": {"n": 0, "crashed": 0}, "passed": {"n": 0, "crashed": 0}, "missed": [],
                "x": {"BUY": dict(empty), "SKIP": dict(empty)}}
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
            xr = {r["mint"]: r["verdict"].upper() for r in csv.DictReader(f) if r.get("mint")}
    def tally(sel):
        return {"n": len(sel), "crashed": sum(1 for r in sel if float(r["change_pct"]) <= CRASH_PCT),
                "ran": sum(1 for r in sel if float(r["change_pct"]) >= 100)}
    out["x"] = {v: tally([r for r in groups["passed"] if xr.get(r["mint"]) == v]) for v in ("BUY", "SKIP")}
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
