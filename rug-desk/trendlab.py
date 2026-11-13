# trendlab.py
# TREND's lab: the rules trend followers actually run, each replayed on the same 10 years as the 200-day
# rule, same costs, same timing, and compared to it and to holding. nothing goes live from here unless it
# beats the rule in force on BOTH halves (activate() then puts it in TREND's paper book).
#
# what the evidence says (Oct 26 research):
#   - time-series momentum: the sign of the last 1, 3 and 12 months' return predicts the next month, in
#     every asset class (Moskowitz, Ooi, Pedersen 2012); a blend of the three horizons is more robust than
#     any single one (Hurst, Ooi, Pedersen 2017, "A Century of Evidence on Trend-Following Investing")
#   - each position sized to a fixed volatility, 40% a year per asset in that paper: a calm asset gets a
#     full slot, BTC at 80% vol half of one. no leverage here: a slot is never more than 1/N of the book
#   - on crypto, volatility scaling alone explains much of trend following's smaller drawdowns, so a
#     "volatility only" rule (no trend signal) is in the lab as the baseline any trend rule must beat
#   - the short side: what perp traders add. crypto only (a short ETF is another product), on the same
#     signal; a short perp usually RECEIVES funding (longs paid ~5-11%/yr in 2024-26), which the lab
#     ignores: shorts are judged on price alone, a conservative choice
#
# rules (weight of one asset's slot, from -1 to +1; the slot is 1/N of the book):
#   200j          the rule in force: in above the 200-day average (bands 1.01 / 0.97), else out
#   vol seule     always in, slot scaled to 40% vol            (the baseline)
#   ensemble      share of the 1, 3, 12-month returns that are positive: 0, 1/3, 2/3 or 1
#   ensemble+vol  the same, scaled to 40% vol
#   long/short    crypto: mean of the three signs (-1 .. +1) scaled to 40% vol; ETFs as ensemble+vol
# a slot is re-traded only when its target moves by a quarter slot or more, or changes side
import math, statistics, time
import majors

RULES = ["200j", "vol seule", "ensemble", "ensemble+vol", "long/short"]
LOOK = {"crypto": (30, 90, 365), "etf": (21, 63, 252)}      # 1, 3, 12 months in each market's bars
YEAR = {"crypto": 365, "etf": 252}
VOL_DAYS = 60
TARGET_VOL = 0.40
BAND = 0.25                       # of a slot
WARMUP = 366                      # bars an asset needs before it joins (the 12-month signal)


def _vol(closes: list[float], i: int, kind: str) -> float | None:
    if i < VOL_DAYS:
        return None
    rets = [closes[j] / closes[j - 1] - 1 for j in range(i - VOL_DAYS + 1, i + 1)]
    sd = statistics.stdev(rets)
    return sd * math.sqrt(YEAR[kind]) if sd > 0 else None


def weights(closes: list[float], kind: str, rule: str) -> list[float | None]:
    """The slot weight after each close (None while the asset is warming up)."""
    sig200 = majors.signals(closes) if rule == "200j" else None
    out = []
    for i in range(len(closes)):
        if i < WARMUP:
            out.append(None)
            continue
        if rule == "200j":
            out.append(1.0 if sig200[i] else 0.0)
            continue
        v = _vol(closes, i, kind)
        scale = min(1.0, TARGET_VOL / v) if v else 1.0
        signs = [1 if closes[i] > closes[i - n] else -1 for n in LOOK[kind]]
        share = sum(s > 0 for s in signs) / len(signs)
        if rule == "vol seule":
            w = scale
        elif rule == "ensemble":
            w = share
        elif rule == "ensemble+vol":
            w = share * scale
        elif rule == "long/short":
            w = (sum(signs) / len(signs) if kind == "crypto" else share) * scale
        else:
            raise ValueError(rule)
        out.append(round(w, 4))
    return out


def _series(data: dict, names: list[str], rule: str) -> tuple[dict, list[str]]:
    """{asset: {day: (close, weight)}} on the union calendar, carried forward on days an asset does not
    trade (its return is then 0), from the first day any asset has a weight."""
    raw = {}
    for n in names:
        bars = majors.complete(n, (data.get(n) or {}).get("bars") or [])
        closes = [b[1] for b in bars]
        w = weights(closes, majors.ASSETS[n]["kind"], rule) if rule != "hold" else \
            [None if i < WARMUP else 1.0 for i in range(len(closes))]
        raw[n] = {majors._day(b[0]): (c, x) for b, c, x in zip(bars, closes, w)}
    out, prev = {n: {} for n in names}, {n: None for n in names}
    for d in sorted({d for n in names for d in raw[n]}):
        for n in names:
            prev[n] = raw[n].get(d, prev[n])
            if prev[n] is not None:
                out[n][d] = prev[n]
    days = sorted({d for n in names for d in out[n]})
    first = next((d for d in days if any(d in out[n] and out[n][d][1] is not None for n in names)), None)
    return out, [d for d in days if first and d >= first]


def simulate(series: dict, days: list[str], a: int, b: int) -> dict:
    """The book over days[a:b]. Each asset with a weight owns 1/N of the book (N = assets with a weight
    that day); the weight of close d is traded at close d+1, costs on every dollar traded."""
    names = list(series)
    eq, pos, want, curve, trades, drag = majors.BANKROLL, {}, None, [], 0, 0.0
    for i in range(a, b):
        d = days[i]
        if i > a:
            y = days[i - 1]
            for n in list(pos):
                if d in series[n] and y in series[n]:
                    r = series[n][d][0] / series[n][y][0] - 1
                    eq += pos[n] * r
                    pos[n] *= 1 + r
        if want is not None:
            for n, w in want.items():
                target = w * eq
                cur = pos.get(n, 0.0)
                slot = eq / max(1, len(want))
                flip = (target > 0) != (cur > 0) and (abs(target) > 1e-9 or abs(cur) > 1e-9)
                if abs(target - cur) >= BAND * slot or flip and abs(target - cur) > 0.01:
                    c = abs(target - cur) * majors.COST_PCT[majors.ASSETS[n]["kind"]] / 100
                    eq -= c
                    drag += 100 * c / eq if eq > 0 else 0
                    pos[n] = target
                    trades += 1
            for n in list(pos):
                if n not in want and pos[n]:
                    c = abs(pos[n]) * majors.COST_PCT[majors.ASSETS[n]["kind"]] / 100
                    eq -= c
                    pos.pop(n)
                    trades += 1
        curve.append(eq)
        live = {n: series[n][d][1] for n in names if d in series[n] and series[n][d][1] is not None}
        want = {n: w / len(live) for n, w in live.items()} if live else {}
    return {"curve": curve, "trades": trades, "drag": drag}


def run(data: dict | None = None, names: list[str] | None = None) -> dict:
    data = data or majors.prices()
    names = names or [n for n in majors.ASSETS
                      if len(majors.complete(n, (data.get(n) or {}).get("bars") or [])) >= WARMUP + 120]
    out = {"t": time.time(), "assets": names, "rules": []}
    if not names:
        return out
    for rule in ["hold"] + RULES:
        series, days = _series(data, names, rule)
        if len(days) < 240:
            continue
        mid = len(days) // 2
        res = {"rule": rule, "from": days[0], "to": days[-1]}
        for key, (a, b) in {"full": (0, len(days)), "h1": (0, mid), "h2": (mid, len(days))}.items():
            s = simulate(series, days, a, b)
            res[key] = majors.metrics(s["curve"], majors._years(days[a:b]))
            if key == "full":
                res["trades"], res["cost_pct_year"] = s["trades"], round(s["drag"] / majors._years(days), 2)
        out["rules"].append(res)
    cur = next((r for r in out["rules"] if r["rule"] == "200j"), None)
    for r in out["rules"]:
        r["verdict"] = judge(r, cur) if cur and r["rule"] not in ("200j", "hold") else "-"
    return out


def judge(r: dict, cur: dict) -> str:
    """MEILLEUR: positive and a better Sharpe than the 200-day rule on each half, and no deeper drawdown.
    TRADE-OFF: a drawdown at most 3/4 of the 200-day rule's, positive, not better on both halves. else NON."""
    try:
        both = all(r[h]["cagr"] > 0 and r[h]["sharpe"] > cur[h]["sharpe"] for h in ("h1", "h2"))
        if both and r["full"]["mdd"] <= cur["full"]["mdd"]:
            return "MEILLEUR"
        if r["full"]["mdd"] <= 0.75 * cur["full"]["mdd"] and r["full"]["cagr"] > 0:
            return "TRADE-OFF"
    except KeyError:
        pass
    return "NON"


def activate(name: str, res: dict | None = None) -> str:
    """Put a lab rule in TREND's paper book. Refused unless the lab judged it MEILLEUR (better than the
    200-day rule on both halves, no deeper drawdown). "200j" always goes back to the rule in force."""
    import coach
    if name != "200j":
        res = res or run()
        r = next((x for x in res["rules"] if x["rule"] == name), None)
        if not r or r["verdict"] != "MEILLEUR":
            return f"refusé : « {name} » est jugé {r['verdict'] if r else 'inconnu'} au labo, il faut MEILLEUR"
    t = coach.tuning()
    old = t.get("trend_rule")
    t["trend_rule"] = name
    coach._write(coach.TUNING, t)
    coach._log({"id": f"{int(time.time())}-Skide-trend_rule", "t": time.time(), "agent": "Skide", "key": "trend_rule",
                "old": old, "new": name, "why": "trendlab: MEILLEUR sur les deux moitiés" if name != "200j" else "retour à la règle 200 j",
                "evidence": {}, "status": "active", "balance": None})
    return f"TREND applique maintenant la règle « {name} »"


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "activer":
        print(activate(sys.argv[2]))
        sys.exit(0)
    print("TREND lab : les règles des trend followers contre la règle 200 j, coûts compris, 10 ans de prix en cache")
    res = run()
    print("actifs :", ", ".join(res["assets"]))
    print(f"{'règle':<14}{'%/an':>8}{'chute max':>11}{'Sharpe':>8}{'Sh. 1re':>9}{'Sh. 2e':>8}{'ordres':>8}  verdict")
    for r in res["rules"]:
        f = r["full"]
        print(f"{r['rule']:<14}{f.get('cagr', 0):>+8.1f}{f.get('mdd', 0):>10.1f}%{f.get('sharpe', 0):>8.2f}"
              f"{r['h1'].get('sharpe', 0):>9.2f}{r['h2'].get('sharpe', 0):>8.2f}{r['trades']:>8}  {r['verdict']}")
    if res["rules"]:
        print(f"période {res['rules'][0]['from']} → {res['rules'][0]['to']}. MEILLEUR = mieux que la règle 200 j "
              f"sur les deux moitiés et pas de chute plus profonde.")
