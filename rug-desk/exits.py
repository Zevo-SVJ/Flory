# exits.py
# when to sell. one pure function, used live by VIGIE and offline by the exit lab, so a rule that
# wins in the lab is exactly the rule that runs.
#
# what the evidence supports (README, "Exits"), and what each rule answers:
#   liquidity first      a pulled pool beats every other rule, even on a green position
#   hard stop            the floor before anything worked
#   ladder               sell part of a winner into strength: the first sellers after a peak get the price
#   lock                 a +40% peak never turns into a loss
#   chandelier trail     a trailing stop k x volatility under the peak: wide on wild tokens, tight on calm ones
#   dump                 the textbook dump: 30% under the peak with volume collapsing under half its average
#   stall                in profit, no new high for a while, sellers taking over: a stall rarely re-pumps
#   time stop            six flat hours free the slot
import json, os
from config import EXIT, DATA

PROFILE = os.path.join(DATA, "exit_profile.json")   # written by the exit lab when it switches profiles


def active() -> dict:
    """The exit profile in force: config.py's EXIT, overridden by VIGIE's self-review (coach.py, guarded)
    or, before it, the lab's choice if it made one."""
    import coach
    name = coach.get("exit_profile")
    if name:
        import exitlab
        return dict(EXIT) if name == "config" else {**EXIT, **exitlab.PROFILES.get(name, {})}
    p = dict(EXIT)
    if os.path.exists(PROFILE):
        try:
            with open(PROFILE) as f:
                p.update(json.load(f).get("params") or {})
        except ValueError:
            pass
    return p


def volatility_pct(hist: list[dict], bars: int = 12, bar_s: int = 300) -> float | None:
    """Average 5-minute range as % of price over the last hour: an ATR built from VIGIE's samples."""
    buckets = {}
    for s in hist:
        b = int(s["t"] // bar_s)
        hi, lo, _ = buckets.get(b, (s["price"], s["price"], s["price"]))
        buckets[b] = (max(hi, s["price"]), min(lo, s["price"]), s["price"])
    ranges = [(hi - lo) / close for hi, lo, close in (buckets[k] for k in sorted(buckets)[-bars:]) if close > 0]
    return 100 * sum(ranges) / len(ranges) if len(ranges) >= 3 else None


def features(path: list[dict], window_s: int = 3600) -> list[dict]:
    """Per tick, the two numbers the rules need from the past hour: volatility and average 5-min
    volume. Computed once per path, so replaying a dozen profiles stays fast."""
    out, start = [], 0
    for i, s in enumerate(path):
        while path[start]["t"] < s["t"] - window_s:
            start += 1
        win = path[start:i + 1]
        vols = [h["v5"] for h in win if h.get("v5") is not None]
        out.append({**s, "vol": volatility_pct(win), "v5_avg": sum(vols) / len(vols) if vols else None})
    return out


def trail_pct(s: dict, p: dict) -> float:
    if p["trail"] == "chandelier":
        v = s.get("vol")
        if v is not None:
            return max(p["trail_min_pct"], min(p["trail_max_pct"], p["trail_k"] * v))
    return p["trail_pct"]


def decide(pos: dict, s: dict, p: dict | None = None) -> tuple[float, str] | None:
    """pos: the open position. s: this tick {t, price, liq, b5, s5, v5} plus its features (vol, v5_avg).
    Returns (fraction of the ORIGINAL size to sell, reason), or None to hold."""
    p = p or active()
    price, entry = s["price"], pos["entry"]
    if price <= 0:
        return 1.0, "pool_gone"
    pct = (price / entry - 1) * 100
    peak_pct = (pos["peak"] / entry - 1) * 100
    hours = (s["t"] - pos["opened"]) / 3600

    if s.get("liq") is not None and s["liq"] < pos["liq0"] * (1 - p["liq_drop_pct"] / 100):
        return 1.0, "liquidity_pulled"
    if pct <= p["stop_pct"]:
        return 1.0, "stop"
    ladder = p["ladder"]
    if pos["steps"] < len(ladder) and pct >= ladder[pos["steps"]][0]:
        level, frac = ladder[pos["steps"]]
        return frac, f"take_profit_{level}"
    if peak_pct >= p["lock_after_pct"] and pct <= p["lock_floor_pct"]:
        return 1.0, "lock"
    if pos["steps"] > 0 or peak_pct >= p["arm_pct"]:
        if price <= pos["peak"] * (1 - trail_pct(s, p) / 100):
            return 1.0, "trailing_stop"
    if peak_pct >= p["arm_pct"] and price <= pos["peak"] * (1 - p["dump_drop_pct"] / 100):
        avg = s.get("v5_avg")
        if avg and (s.get("v5") or 0) < avg * p["dump_volume_ratio"]:
            return 1.0, "dump"
    if (pct >= p["stall_min_pct"] and s["t"] - pos.get("peak_t", pos["opened"]) >= p["stall_min"] * 60
            and (s.get("s5") or 0) >= p["stall_sell_ratio"] * max(1, s.get("b5") or 0)):
        return 1.0, "stall"
    if hours >= p["time_stop_hours"] and pct < p["time_stop_min_pct"]:
        return 1.0, "time_stop"
    return None
