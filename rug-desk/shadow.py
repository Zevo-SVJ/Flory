# shadow.py
# what GARDE turned down, bought in shadow. every token that got past SCOUT's pool rules and was then
# killed by GARDE is priced by VIGIE for 6 h (a ghost, paths.py), and replayed with the desk's own exit
# engine and costs, as if it had been bought at the verdict. per kill reason, this says whether the
# kill saved money or cost it: the one measure of GARDE's value, and so of the Telegram bot's.
# nothing here touches the book.
import csv, os, statistics, time
from config import DATA, EXIT, PAPER_COSTS
import paths

FILE = os.path.join(DATA, "shadow.csv")
FIELDS = ["t", "mint", "symbol", "stage", "reason", "price", "liq"]
HOURS = 6
TICKET = 40.0
STAGES = ("pool", "facts", "deep", "pass")          # "limits" (book full, already open) is no verdict on the token
# at the pool stage only GARDE's own kills: a thin or fresh pool pasted in the dashboard is no verdict either
POOL_KILLS = ("below_graduation", "copycat", "serial_farm", "stale_data", "falling_knife")


def _rows() -> list[dict]:
    try:
        with open(FILE, newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def note(mint: str, v: dict) -> bool:
    """Called by GARDE after a kill. One shadow per token (a retried kill is the same token).
    Returns True if the token is now followed."""
    reason = v.get("reason") or ""
    if v.get("verdict") in ("PASS", "BUY") and str(v.get("action", "")).startswith("not bought") \
            and "regime dial" not in v["action"] and "prudence" not in v["action"]:
        reason = ("model_veto" if "model" in v["action"] else "hot_signals" if "hot signals" in v["action"]
                  else "low_score")                                            # passed every check, not bought
        v = {**v, "verdict": "SKIP", "stage": "score", "reason": reason}
    elif v.get("verdict") in ("PASS", "BUY"):
        # a pass is followed the same way, bought or not: learn.py gets one label per token GARDE judged,
        # replayed from the verdict price with the same exits and costs whatever happened to the position
        v = {**v, "verdict": "SKIP", "stage": "pass", "reason": "pass"}
        reason = "pass"
    elif v.get("verdict") != "SKIP" or v.get("stage") not in STAGES or " failed" in reason:
        return False
    if v["stage"] == "pool" and reason not in POOL_KILLS:
        return False
    if not v.get("price") or not v.get("liq_usd"):
        return False
    if any(r["mint"] == mint for r in _rows()):
        return False
    os.makedirs(DATA, exist_ok=True)
    new = not os.path.exists(FILE)
    with open(FILE, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({"t": round(time.time()), "mint": mint, "symbol": v.get("symbol") or mint[:6],
                    "stage": v["stage"], "reason": reason, "price": v["price"], "liq": round(v["liq_usd"])})
    paths.haunt(mint)
    return True


def path(r: dict):
    """(price path with features, round-trip cost in %) for one shadow, or None if VIGIE missed it."""
    import exits, chains
    t0 = float(r["t"])
    entry = {"t": t0, "price": float(r["price"]), "liq": float(r["liq"]), "b5": None, "s5": None, "v5": None}
    pts = [entry] + [p for p in paths.load(r["mint"], since=t0 + 1, until=t0 + HOURS * 3600)]
    if len(pts) < 10:                       # VIGIE missed it (desk stopped): no fair replay
        return None
    impact = 100 * TICKET / (entry["liq"] / 2)
    c = chains.costs(r["mint"])
    cost = 2 * (c["fee_pct"] + c.get("mev_pct", 0) + impact) + 2 * c["tx_usd"] / TICKET * 100
    return exits.features(pts), cost


def replay(r: dict, params: dict | None = None, p=None) -> float | None:
    """Net % for one shadow buy at the verdict price, the exit profile in force (or `params`), real costs."""
    import exits, exitlab
    p = p or path(r)
    if not p:
        return None
    gross = exitlab.simulate(p[0], params or exits.for_mint(r.get("mint") or ""))
    if gross is None:
        return None
    return gross / exitlab.TICKET_USD * 100 - p[1]


# never waived, whatever the shadow book says: each one is a way to lose the whole ticket at once
HARD = {"pass", "model_veto", "dev_rugged_before", "mint_open", "freeze_open", "lp_unlocked", "nobody_can_sell", "holder_farm",
        "factory_wallets", "rug_funder", "st_rugged", "stale_data", "whale", "no_holders"}
CAP_PCT = 1000              # one shadow token counts at most +1000% in the means: one glitch must not lift a rule
WAIVE_MIN_N = 20            # shadow trades replayed for that reason
WAIVE_MIN_MEAN = 5.0        # net % per trade, after costs, and positive on both halves
_waived = {"t": 0.0, "v": set()}


def waived() -> set:
    """Soft kill reasons the desk stops applying by itself: their shadow buys made money, clearly and
    on both halves. a reason that protects (shadow buys lose) stays. cached 10 min."""
    if time.time() - _waived["t"] > 600:
        try:
            r = results()
            _waived["v"] = {d["reason"] for d in r["reasons"]
                            if d["reason"] not in HARD and not d["reason"].startswith("danger:")
                            and d["n"] >= WAIVE_MIN_N and d["mean"] >= WAIVE_MIN_MEAN
                            and (d.get("half1") or 0) > 0 and (d.get("half2") or 0) > 0
                            and (d.get("low") or -1) > 0}      # and above zero beyond its own noise
        except Exception:
            _waived["v"] = set()
        _waived["t"] = time.time()
    return _waived["v"]


def results() -> dict:
    """Shadows whose 6 h are over, per kill reason and in all, next to what the desk's real buys made."""
    now, done, waiting = time.time(), [], 0
    for r in sorted(_rows(), key=lambda r: float(r["t"])):
        if now < float(r["t"]) + HOURS * 3600:
            waiting += 1
            continue
        x = replay(r)
        if x is not None:
            done.append((r["reason"], min(x, CAP_PCT)))
    by = {}
    for reason, x in done:                  # in kill order, so each reason's list splits into two halves
        by.setdefault(reason, []).append(x)
    mean = lambda xs: round(statistics.mean(xs), 1) if xs else None
    def low(xs):                            # one-sided 90% lower bound of the mean
        if len(xs) < 2:
            return None
        return round(statistics.mean(xs) - 1.645 * statistics.stdev(xs) / len(xs) ** 0.5, 1)
    stat = lambda xs: {"n": len(xs), "mean": mean(xs), "win": round(sum(v > 0 for v in xs) / len(xs), 2),
                       "half1": mean(xs[:len(xs) // 2]), "half2": mean(xs[len(xs) // 2:]), "low": low(xs)} if xs else None
    import edge
    st = edge.stats()
    return {"waiting": waiting, "all": stat([x for _, x in done]),
            "reasons": sorted(({"reason": k, **stat(v)} for k, v in by.items()), key=lambda d: -d["n"]),
            "bought": {"n": st["n"], "mean": st.get("mean_pct")}}
