# majors.py
# TENDANCE: the desk's second book, on assets that trade every day whatever the memecoin market does.
# BTC, ETH, SOL (crypto, 7 days a week) and QQQ, SPY (the Nasdaq 100 and S&P 500 ETFs), in paper,
# with its own $1,000, apart from the memecoin book.
#
# the rule is the oldest one with evidence behind it: hold an asset while its close is above its
# 200-day average, hold cash when it is below (Faber 2007 on equities; on crypto, time-series momentum
# is stronger than on stocks but fragile after costs: Borgards 2021, "A Decade of Evidence of Trend
# Following Investing in Cryptocurrencies"). what it mostly buys is smaller drawdowns, not a bigger
# return. two bands keep it from trading every time the price crosses its average:
#   in  when the close is 1% above the average     out  when it is 3% under
# the assets "in" share the book equally; the others are cash. no leverage, no short.
#
# the same rule runs in the backtest (backtest(), on up to 10 years of daily closes, with costs) and
# live (tick(), every 5 min from agents.py): a rule that wins in the lab is exactly the rule that runs.
# the verdict is written plainly: DATA VALIDATED, TRADE-OFF or NO EDGE (definitions in verdict()).
#
# the regime dial (dial()): BTC above its 200-day, ETH above its 200-day, SOL above its 50-day.
# the share of greens is logged with every memecoin verdict: learn.py and TREND's self-review find out
# whether memecoins bought in a red regime lose, and only then (coach.py's guards) does the meme desk
# stand down below a dial of 0.5.
#
# prices: Coinbase daily candles (Kraken if Coinbase fails) for crypto, Yahoo (Stooq if Yahoo fails)
# for the ETFs. no key, no wallet, nothing is ever sent anywhere: paper only.
import csv, json, math, os, statistics, time
import requests
from config import DATA
import atomic

ASSETS = {
    "BTC": {"kind": "crypto", "cb": "BTC-USD", "kr": "XBTUSD"},
    "ETH": {"kind": "crypto", "cb": "ETH-USD", "kr": "ETHUSD"},
    "SOL": {"kind": "crypto", "cb": "SOL-USD", "kr": "SOLUSD"},
    "QQQ": {"kind": "etf", "yf": "QQQ", "stooq": "qqq.us"},
    "SPY": {"kind": "etf", "yf": "SPY", "stooq": "spy.us"},
}
BANKROLL = 1000.0
SMA_DAYS = 200
BAND_IN, BAND_OUT = 1.01, 0.97
COST_PCT = {"crypto": 0.40, "etf": 0.05}     # per side: a Kraken Pro taker fee; an ETF's spread and slippage
CRYPTO_DAYS = 4000                            # all of it, once (BTC 2015, ETH 2016, SOL 2021), then topped up
REFRESH_S = 900                               # candles re-read every 15 min: the last one is the live price
BACKTEST_S = 24 * 3600
DIAL = (("BTC", 200), ("ETH", 200), ("SOL", 50))
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) rug-desk"}

PRICES = os.path.join(DATA, "majors_prices.json")
STATE = os.path.join(DATA, "majors.json")
BT = os.path.join(DATA, "majors_bt.json")
FILLS = os.path.join(DATA, "majors_trades.csv")
EQUITY = os.path.join(DATA, "majors_equity.csv")
FILL_FIELDS = ["time", "asset", "side", "qty", "price", "usd", "cost", "why"]


def _read(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write(path, obj):
    os.makedirs(DATA, exist_ok=True)
    tmp = atomic.tmp(path)
    with open(tmp, "w") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


# ---------------------------------------------------------------- prices
# every fetcher returns bars [[t, close], ...] oldest first, t = the bar's start (UTC seconds).
# the newest bar may still be open: complete() says which ones are done.

def _coinbase(sym: str, days: int) -> list[list[float]]:
    out, end = {}, time.time()
    while days > 0:
        n = min(290, days)                                # Coinbase answers 300 candles at most
        start = end - n * 86400
        r = requests.get(f"https://api.exchange.coinbase.com/products/{sym}/candles", headers=UA, timeout=20,
                         params={"granularity": 86400, "start": _iso(start), "end": _iso(end)})
        r.raise_for_status()
        rows = r.json()                                   # [time, low, high, open, close, volume], newest first
        if not rows:
            break
        for row in rows:
            out[float(row[0])] = float(row[4])
        end, days = start, days - n
        time.sleep(0.2)                                   # public limit: 10 calls a second
    if not out:
        raise ValueError("Coinbase: aucune bougie")
    return [[t, out[t]] for t in sorted(out)]


def _iso(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def _kraken(pair: str) -> list[list[float]]:
    r = requests.get("https://api.kraken.com/0/public/OHLC", params={"pair": pair, "interval": 1440},
                     headers=UA, timeout=20)
    r.raise_for_status()
    j = r.json()
    if j.get("error"):
        raise ValueError(f"Kraken: {j['error']}")
    rows = next(v for k, v in j["result"].items() if k != "last")   # [time, o, h, l, close, vwap, vol, n]
    return [[float(x[0]), float(x[4])] for x in rows]


def _yahoo(sym: str) -> list[list[float]]:
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                     params={"range": "10y", "interval": "1d"}, headers=UA, timeout=20)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    closes = res["indicators"]["quote"][0]["close"]
    return [[float(t), float(c)] for t, c in zip(res["timestamp"], closes) if c is not None]


def _stooq(sym: str) -> list[list[float]]:
    r = requests.get("https://stooq.com/q/d/l/", params={"s": sym, "i": "d"}, headers=UA, timeout=20)
    r.raise_for_status()
    out = []
    for row in csv.DictReader(r.text.splitlines()):
        try:
            day = time.mktime(time.strptime(row["Date"], "%Y-%m-%d")) - time.timezone   # midnight UTC
            out.append([day + 13.5 * 3600, float(row["Close"])])                          # the 09:30 New York open
        except (KeyError, ValueError):
            continue
    if not out:
        raise ValueError("Stooq: réponse vide")
    return out[-2600:]


def _fetch(name: str, deep: bool) -> tuple[list[list[float]], str]:
    a = ASSETS[name]
    errors = []
    if a["kind"] == "crypto":
        tries = (("coinbase", lambda: _coinbase(a["cb"], CRYPTO_DAYS if deep else 290)),
                 ("kraken", lambda: _kraken(a["kr"])))
    else:
        tries = (("yahoo", lambda: _yahoo(a["yf"])), ("stooq", lambda: _stooq(a["stooq"])))
    for src, fn in tries:
        try:
            bars = fn()
            if len(bars) >= 2:
                return bars, src
            errors.append(f"{src}: {len(bars)} bougies")
        except Exception as e:
            errors.append(f"{src}: {str(e)[:80]}")
    raise RuntimeError(" ; ".join(errors))


def span(name: str) -> float:
    """How long one bar stays open: a crypto day, or an ETF session (09:30 to 16:00 New York, plus margin)."""
    return 86400 if ASSETS[name]["kind"] == "crypto" else 7 * 3600


def complete(name: str, bars: list, now: float | None = None) -> list:
    now = now or time.time()
    return [b for b in bars if b[0] + span(name) <= now]


def refresh(force: bool = False, say=None) -> dict:
    """Top up every asset's bars. A source that fails keeps the cache and says why (data['errors']).
    say: called with a line before and after each asset (the command line shows progress with it)."""
    data = _read(PRICES, {})
    errors = {}
    for name in ASSETS:
        cur = data.get(name) or {}
        if not force and time.time() - cur.get("t", 0) < REFRESH_S:
            continue
        deep = ASSETS[name]["kind"] == "crypto" and cur.get("depth") != CRYPTO_DAYS   # the whole history, once
        if say:
            say(f"{name} : lecture des prix" + (" depuis le début (une seule fois, ~15 s)" if deep else "") + "…")
        t0 = time.time()
        try:
            bars, src = _fetch(name, deep)
        except Exception as e:
            errors[name] = str(e)[:200]
            if say:
                say(f"{name} : source en panne : {errors[name]}")
            continue
        if say:
            say(f"{name} : {len(bars)} jours reçus de {src} en {time.time() - t0:.0f} s")
        merged = {b[0]: b[1] for b in cur.get("bars") or []}
        merged.update({b[0]: b[1] for b in bars})
        data[name] = {"t": time.time(), "src": src, "bars": [[t, merged[t]] for t in sorted(merged)],
                      "depth": CRYPTO_DAYS if deep and src == "coinbase" else cur.get("depth")}
    data["errors"] = errors
    data["checked"] = time.time()
    _write(PRICES, data)
    return data


def prices() -> dict:
    return _read(PRICES, {})


def last(name: str, data: dict | None = None) -> float | None:
    bars = ((data or prices()).get(name) or {}).get("bars") or []
    return bars[-1][1] if bars else None


# ---------------------------------------------------------------- the rule
def sma(xs: list[float], n: int) -> list[float | None]:
    out, s = [], 0.0
    for i, x in enumerate(xs):
        s += x
        if i >= n:
            s -= xs[i - n]
        out.append(s / n if i >= n - 1 else None)
    return out


def signals(closes: list[float], n: int = SMA_DAYS) -> list[bool | None]:
    """In (True) or out (False) after each close, None before there are n closes. The bands make it
    sticky: in above average x1.01, out under average x0.97, unchanged in between."""
    out, state = [], None
    for c, m in zip(closes, sma(closes, n)):
        if m is None:
            out.append(None)
            continue
        if state is None:
            state = c > m
        elif state and c < m * BAND_OUT:
            state = False
        elif not state and c > m * BAND_IN:
            state = True
        out.append(state)
    return out


def live_signals(data: dict | None = None) -> dict:
    """Per asset: in/out after its last complete close, its close, its 200-day average, the gap in %."""
    data = data or prices()
    out = {}
    for name in ASSETS:
        bars = complete(name, (data.get(name) or {}).get("bars") or [])
        closes = [b[1] for b in bars]
        if len(closes) < SMA_DAYS:
            out[name] = {"in": None, "why": f"{len(closes)} jours d'historique, il en faut {SMA_DAYS}"}
            continue
        m = sum(closes[-SMA_DAYS:]) / SMA_DAYS
        out[name] = {"in": signals(closes)[-1], "close": closes[-1], "sma": round(m, 4),
                     "gap_pct": round((closes[-1] / m - 1) * 100, 1), "day": bars[-1][0]}
    return out


def dial(data: dict | None = None) -> dict | None:
    """The regime dial: share of BTC > 200 d, ETH > 200 d, SOL > 50 d, on the live price."""
    data = data or prices()
    parts = {}
    for name, n in DIAL:
        bars = complete(name, (data.get(name) or {}).get("bars") or [])
        px = last(name, data)
        if len(bars) < n or not px:
            continue
        m = sum(b[1] for b in bars[-n:]) / n
        parts[f"{name}>{n}j"] = px > m
    if len(parts) < len(DIAL):
        return None
    return {"value": round(sum(parts.values()) / len(parts), 2), "parts": parts}


_dial = {"t": 0.0, "v": None}


def dial_value() -> float | None:
    """The dial from the price cache only (no network): GARDE logs it with every verdict. Cached 5 min."""
    if time.time() - _dial["t"] > 300:
        try:
            d = dial()
            _dial["v"] = d["value"] if d and time.time() - prices().get("checked", 0) < 6 * 3600 else None
        except Exception:
            _dial["v"] = None
        _dial["t"] = time.time()
    return _dial["v"]


# ---------------------------------------------------------------- backtest
def _day(t: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(t))


def _move(cash: float, qty: dict, px: dict, want: set) -> tuple[float, list]:
    """Equal weight among `want` at prices px, sells first so the buys use the cash they free, costs paid.
    Changes qty in place. Returns (cash, fills [(asset, usd, qty, cost)]). Used by the backtest and live."""
    eq = cash + sum(q * px[n] for n, q in qty.items())
    target = {n: eq / len(want) for n in want} if want else {}
    done = []
    for side in ("sell", "buy"):
        for n in sorted(px):
            delta = target.get(n, 0.0) - qty.get(n, 0.0) * px[n]
            if not (side == "sell" and delta < -0.01 or side == "buy" and delta > 0.01):
                continue
            c = abs(delta) * COST_PCT[ASSETS[n]["kind"]] / 100
            usd = delta if side == "sell" else min(delta, cash - c)
            if side == "buy" and usd <= 0:
                continue
            q = usd / px[n]
            qty[n] = qty.get(n, 0.0) + q
            if qty[n] * px[n] < 0.01:
                qty.pop(n)
            cash -= usd + c
            done.append((n, usd, q, c))
    return cash, done


def simulate(series: dict, days: list[str], start: int, end: int, mode: str = "trend") -> dict:
    """One run of the book over days[start:end]. series: {asset: {day: (close, signal)}}, forward-filled.
    mode "trend": the 200-day rule, equal weight among assets in, the signal of close d traded at close d+1.
    mode "hold": the benchmark, always in every asset that exists, equal weight, same timing and costs.
    an asset joins the day it has 200 closes (SOL in 2022, BTC in 2015): the book is never longer than the data."""
    names = list(series)
    cash, qty, curve, costs, trades, exposed, want = BANKROLL, {}, [], 0.0, 0, 0, None
    drag = 0.0                                            # costs as % of the book when paid: $ grow with the book
    for i in range(start, end):
        d = days[i]
        px = {n: series[n][d][0] for n in names if d in series[n]}
        if want is not None:                              # yesterday's signal, filled at today's close
            eq = cash + sum(q * px[n] for n, q in qty.items())
            cash, done = _move(cash, qty, px, want)
            costs += sum(f[3] for f in done)
            drag += 100 * sum(f[3] for f in done) / eq if eq > 0 else 0
            trades += len(done)
            want = None
        curve.append(cash + sum(q * px[n] for n, q in qty.items()))
        exposed += bool(qty)
        live = {n for n in px if series[n][d][1] is not None}
        now_in = live if mode == "hold" else {n for n in live if series[n][d][1]}
        if now_in != set(qty):
            want = now_in
    return {"curve": curve, "costs": round(costs, 2), "drag": drag, "trades": trades, "exposed": exposed / max(1, end - start)}


def metrics(curve: list[float], years: float) -> dict:
    """Return per year, worst fall from a peak, Sharpe (annualized on the bars actually traded)."""
    if len(curve) < 2 or years <= 0:
        return {}
    rets = [b / a - 1 for a, b in zip(curve, curve[1:]) if a > 0]
    peak, mdd = curve[0], 0.0
    for x in curve:
        peak = max(peak, x)
        mdd = max(mdd, 1 - x / peak)
    sd = statistics.stdev(rets) if len(rets) > 1 else 0
    per_year = len(rets) / years
    return {"cagr": round(((curve[-1] / curve[0]) ** (1 / years) - 1) * 100, 1) if curve[-1] > 0 else -100.0,
            "mdd": round(mdd * 100, 1),
            "sharpe": round(statistics.mean(rets) / sd * math.sqrt(per_year), 2) if sd else 0.0,
            "total": round((curve[-1] / curve[0] - 1) * 100, 1)}


def verdict(full: dict, halves: list[dict]) -> tuple[str, str]:
    """DATA VALIDATED: positive on each half, a better Sharpe than holding on each half, a smaller drawdown.
    TRADE-OFF: a drawdown at most 3/4 of holding's, still positive, but not better on both halves.
    NO EDGE: anything else."""
    s, h = full["trend"], full["hold"]
    both = all(x["trend"].get("cagr", -1) > 0 and x["trend"].get("sharpe", 0) > x["hold"].get("sharpe", 0) for x in halves)
    if both and s["mdd"] < h["mdd"]:
        return "DATA VALIDATED", (f"meilleur que garder sur chaque moitié (Sharpe {halves[0]['trend']['sharpe']} / "
                                  f"{halves[1]['trend']['sharpe']} contre {halves[0]['hold']['sharpe']} / {halves[1]['hold']['sharpe']}), "
                                  f"chute max {s['mdd']} % contre {h['mdd']} %")
    if s["mdd"] <= 0.75 * h["mdd"] and s["cagr"] > 0:
        return "TRADE-OFF", (f"chute max {s['mdd']} % au lieu de {h['mdd']} %, "
                             f"rendement {s['cagr']:+.1f} %/an contre {h['cagr']:+.1f} % : moins de risque, pas plus de gain sûr")
    return "NO EDGE", f"{s['cagr']:+.1f} %/an, chute max {s['mdd']} % contre {h['cagr']:+.1f} %/an et {h['mdd']} % en gardant"


def _series(data: dict, names: list[str]) -> tuple[dict, list[str]]:
    """Common calendar (the union of the assets' trading days), each asset's close and signal carried
    forward over the days it does not trade, from the first day any asset has a signal."""
    raw = {}
    for n in names:
        bars = complete(n, (data.get(n) or {}).get("bars") or [])
        raw[n] = {_day(b[0]): (b[1], s) for b, s in zip(bars, signals([b[1] for b in bars]))}
    out, prev = {n: {} for n in names}, {n: None for n in names}
    for d in sorted({d for n in names for d in raw[n]}):
        for n in names:
            prev[n] = raw[n].get(d, prev[n])
            if prev[n] is not None:
                out[n][d] = prev[n]
    all_days = sorted({d for n in names for d in out[n]})
    first = next((d for d in all_days if any(d in out[n] and out[n][d][1] is not None for n in names)), None)
    days = [d for d in all_days if first and d >= first]
    return {n: {d: out[n][d] for d in days if d in out[n]} for n in names}, days


def _years(days: list[str]) -> float:
    t = lambda d: time.mktime(time.strptime(d, "%Y-%m-%d"))
    return max(1.0, t(days[-1]) - t(days[0]) + 86400) / (365.25 * 86400)


def backtest_one(data: dict, names: list[str]) -> dict | None:
    series, days = _series(data, names)
    if len(days) < 120:
        return None
    mid = len(days) // 2

    def run(a, b):
        y = _years(days[a:b])
        t, h = simulate(series, days, a, b, "trend"), simulate(series, days, a, b, "hold")
        return t, {"trend": metrics(t["curve"], y), "hold": metrics(h["curve"], y)}

    t, full = run(0, len(days))
    halves = [run(0, mid)[1], run(mid, len(days))[1]]
    v, why = verdict(full, halves)
    return {"assets": names, "from": days[0], "to": days[-1], "days": len(days), **full,
            "halves": halves, "trades": t["trades"], "costs": t["costs"],
            "cost_pct_year": round(t["drag"] / _years(days), 2),
            "exposed": round(t["exposed"] * 100), "verdict": v, "why": why}


def backtest(data: dict | None = None) -> dict:
    """The rule on the whole book and on each asset alone, with costs, written to data/majors_bt.json."""
    data = data or prices()
    have = [n for n in ASSETS if len(complete(n, (data.get(n) or {}).get("bars") or [])) >= SMA_DAYS + 120]
    out = {"t": time.time(), "runs": []}
    if len(have) >= 2:
        r = backtest_one(data, have)
        if r:
            out["runs"].append({"name": "portefeuille", **r})
    for n in have:
        r = backtest_one(data, [n])
        if r:
            out["runs"].append({"name": n, **r})
    _write(BT, out)
    return out


# ---------------------------------------------------------------- the live paper book
def book() -> dict:
    return _read(STATE, {"cash": BANKROLL, "qty": {}, "started": None, "fills": 0})


def equity(b: dict | None = None, data: dict | None = None) -> float | None:
    b, data = b or book(), data or prices()
    total = b["cash"]
    for n, q in b["qty"].items():
        px = last(n, data)
        if px is None:
            return None
        total += q * px
    return total


def _fill(asset: str, side: str, qty: float, price: float, usd: float, cost: float, why: str):
    os.makedirs(DATA, exist_ok=True)
    new = not os.path.exists(FILLS)
    with open(FILLS, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FILL_FIELDS)
        if new:
            w.writeheader()
        w.writerow({"time": time.strftime("%Y-%m-%d %H:%M"), "asset": asset, "side": side, "qty": round(qty, 8),
                    "price": price, "usd": round(usd, 2), "cost": round(cost, 4), "why": why})


def fills() -> list[dict]:
    if not os.path.exists(FILLS):
        return []
    with open(FILLS, newline="") as f:
        return list(csv.DictReader(f))


def rebalance(b: dict, want: set, data: dict, sig: dict) -> list[str]:
    """Move the paper book to equal weight among `want`, at the live price, costs paid. Returns what it did."""
    px = {n: last(n, data) for n in set(want) | set(b["qty"])}
    if any(v is None for v in px.values()):
        return []
    b["cash"], done = _move(b["cash"], b["qty"], px, want)
    did = []
    for n, usd, q, c in done:
        s = sig.get(n) or {}
        why = (f"clôture {s['close']:.2f} {'au-dessus' if s.get('in') else 'sous'} de la moyenne 200 j "
               f"{s['sma']:.2f} ({s['gap_pct']:+.1f} %)" if s.get("sma") else "rééquilibrage")
        _fill(n, "achat" if q > 0 else "vente", abs(q), px[n], abs(usd), c, why)
        b["fills"] = b.get("fills", 0) + 1
        did.append(f"{'achète' if q > 0 else 'vend'} {n} ${abs(usd):.0f} à {px[n]:,.2f}")
    return did


def log_equity(b: dict, data: dict):
    eq = equity(b, data)
    if eq is None:
        return
    new = not os.path.exists(EQUITY)
    d = dial(data)
    with open(EQUITY, "a") as f:
        if new:
            f.write("t,equity,cash,dial\n")
        f.write(f"{time.time():.0f},{eq:.4f},{b['cash']:.4f},{'' if d is None else d['value']}\n")


def tick() -> tuple[str, list[str]]:
    """TREND's turn: refresh prices, read the rule, trade the paper book if the set of assets in changed,
    re-run the backtest once a day. Returns (status line, the trades it made)."""
    data = refresh()
    sig = live_signals(data)
    b = book()
    if b.get("started") is None:
        b["started"] = time.time()
    held_now = set(b["qty"])
    want = {n for n, s in sig.items() if s.get("in")}
    unknown = {n for n, s in sig.items() if s.get("in") is None}
    want |= held_now & unknown                 # a source down keeps what is held: no blind sale
    did = rebalance(b, want, data, sig) if want != held_now else []
    _write(STATE, b)
    log_equity(b, data)
    if time.time() - _read(BT, {}).get("t", 0) > BACKTEST_S:
        backtest(data)
    eq = equity(b, data)
    d = dial(data)
    line = (f"${eq:,.0f} ({(eq / BANKROLL - 1) * 100:+.1f} %)" if eq is not None else "prix incomplets")
    line += " · en position : " + (", ".join(sorted(b["qty"])) or "rien, tout en cash")
    if d:
        line += f" · cadran {sum(d['parts'].values())}/{len(d['parts'])}"
    if data.get("errors"):
        line += " · source en panne : " + ", ".join(sorted(data["errors"]))
    return line, did


def summary() -> dict:
    """For the dashboard and /etat: the book, the rule per asset, the dial, the backtest verdicts."""
    data = prices()
    b = book()
    sig = live_signals(data)
    eq = equity(b, data)
    rows = []
    for n in ASSETS:
        px = last(n, data)
        q = b["qty"].get(n, 0.0)
        rows.append({"asset": n, "price": px, "in": sig[n].get("in"), "gap_pct": sig[n].get("gap_pct"),
                     "sma": sig[n].get("sma"), "why": sig[n].get("why"), "usd": round(q * px, 2) if px else None,
                     "src": (data.get(n) or {}).get("src")})
    curve = []
    if os.path.exists(EQUITY):
        with open(EQUITY) as f:
            next(f, None)
            for line in f:
                t, e = line.split(",")[:2]
                curve.append([float(t), float(e)])
    if len(curve) > 300:
        step = len(curve) / 299
        curve = [curve[int(i * step)] for i in range(299)] + [curve[-1]]
    return {"equity": eq, "bankroll": BANKROLL, "cash": b["cash"], "started": b.get("started"),
            "assets": rows, "dial": dial(data), "bt": _read(BT, {}), "fills": fills()[-10:][::-1],
            "n_fills": len(fills()), "errors": data.get("errors") or {}, "checked": data.get("checked"),
            "curve": curve}


if __name__ == "__main__":
    say = lambda s: print(s, flush=True)
    say("TENDANCE : prix, puis backtest. compter 1 minute la première fois.")
    data = refresh(force=True, say=say)
    say("")
    for n in ASSETS:
        bars = (data.get(n) or {}).get("bars") or []
        print(f"{n}: {len(bars)} jours ({(data.get(n) or {}).get('src')})"
              + (f", de {_day(bars[0][0])} à {_day(bars[-1][0])}" if bars else ""))
    d = dial(data)
    print("cadran :", d)
    say("backtest en cours…")
    r = backtest(data)
    for run in r["runs"]:
        print(f"\n{run['name']} ({run['from']} → {run['to']}, {run['days']} jours, {run['trades']} ordres, "
              f"coûts {run['cost_pct_year']} % du capital par an, investi {run['exposed']} % du temps)")
        print(f"  règle 200 j : {run['trend']['cagr']:+.1f} %/an, chute max {run['trend']['mdd']} %, Sharpe {run['trend']['sharpe']}")
        print(f"  garder      : {run['hold']['cagr']:+.1f} %/an, chute max {run['hold']['mdd']} %, Sharpe {run['hold']['sharpe']}")
        print(f"  → {run['verdict']} : {run['why']}")
