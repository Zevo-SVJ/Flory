# learn.py
# the desk learns from every token it judges, not only from the few it buys. ~250 tokens reach GARDE a
# day; each one is followed in shadow for 6 h (shadow.py) and replayed with the desk's own exits and
# costs. that gives one labelled lesson per token: what GARDE saw at the verdict (checks.csv) -> what
# buying it would have earned. trades alone (~20 a day) would take months to teach anything.
#
# the model is deliberately small: a ridge regression on ~35 features, outliers clipped, so a handful of
# lucky tokens can't write the rules. it is trusted only if it beats chance on data it never saw:
# trained on the older 70%, tested on the newer 30%, its picks must earn more than the average token
# and more than zero, on enough of them. then GARDE lets it decide where the soft rules used to: it can
# buy a token a soft rule killed, or skip a pass it expects to lose. hard rules (mint, freeze, honeypot,
# unburned LP, whale, known factories...) never move. the market's own trend (SOL 1 h and 24 h) is a
# feature: when everything loses, the model says so and the desk buys less.
import csv, json, math, os, time
from config import LOG, DATA
import atomic

MODEL = os.path.join(DATA, "model.json")
CLIP = (-100.0, 200.0)       # a +2,000% moonshot would otherwise be half the model
MIN_TRAIN, MIN_TEST, MIN_PICKS = 80, 30, 8
LIFT_PCT = 3.0               # its picks must beat the average token by this much on unseen data
OVERRIDE_PCT = 5.0           # a soft kill is overridden only above this predicted net % per trade
RETRAIN_S = 2 * 3600       # every 2 h: a new lesson matures every few minutes while the market runs

FLAGS = ["bot_volume", "few_holders", "very_young", "concentrated", "no_socials", "one_sided", "quiet",
         "late", "liq_edge", "smart_money"]
SOFT = ["lp_unverified", "bundle_same_sol", "bundle_ladder", "copycat", "serial_dev", "inorganic_volume",
        "low_organic", "jup_sus", "top10_heavy", "dev_holds", "dev_unknown", "funded_cluster", "fresh_wallets",
        "bundled", "insiders", "snipers", "low_score", "below_graduation", "serial_farm"]
WORDS = {"score": "la note", "log_liq": "un pool plus profond", "log_age": "un token plus âgé",
         "top10": "un top 10 plus concentré", "max_wallet": "un plus gros wallet", "log_holders": "plus de holders",
         "vol_liq": "plus de volume par rapport au pool", "log_avg_trade": "des trades moyens plus gros",
         "chg_1h": "une hausse sur 1 h", "chg_5m": "une hausse sur 5 min", "buy_ratio": "plus d'acheteurs que de vendeurs",
         "log_mcap_liq": "une capitalisation gonflée face au pool", "socials": "des réseaux sociaux",
         "sol_1h": "SOL en hausse sur 1 h", "sol_24h": "SOL en hausse sur 24 h", "organic": "le score organique Jupiter",
         "cluster_pct": "un cluster financé", "fresh_pct": "des wallets neufs", "evm": "une chaîne EVM",
         "momentum": "le couloir momentum", "dial": "le cadran de régime (BTC, ETH, SOL au-dessus de leurs moyennes)",
         "rc_score": "un score de risque RugCheck plus haut", "rc_danger": "un risque « danger » de plus chez RugCheck",
         "rc_lp_locked": "plus de pool verrouillé selon RugCheck"}


def _f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _log(v, floor=0.0):
    x = _f(v)
    return math.log10(max(x, 0) + 1) if x is not None and x >= floor else None


def features(r: dict) -> dict:
    """One verdict row (checks.csv, or GARDE's live dict) -> named features. None where unknown."""
    flags = set((r.get("flags") or "").split())
    reason = r.get("reason") or ""
    clip = lambda v, a, b: None if v is None else max(a, min(b, v))
    out = {"score": _f(r.get("score")), "log_liq": _log(r.get("liq_usd")), "log_age": _log(r.get("age_min")),
           "top10": _f(r.get("top10")), "max_wallet": _f(r.get("max_wallet")), "log_holders": _log(r.get("holders")),
           "vol_liq": clip(_f(r.get("vol_liq")), 0, 10), "log_avg_trade": _log(r.get("avg_trade")),
           "chg_1h": clip(_f(r.get("chg_1h")), -100, 300), "chg_5m": clip(_f(r.get("chg_5m")), -50, 100),
           "buy_ratio": _f(r.get("buy_ratio")), "log_mcap_liq": _log(r.get("mcap_liq")), "socials": _f(r.get("socials")),
           "sol_1h": _f(r.get("sol_1h")), "sol_24h": _f(r.get("sol_24h")), "organic": _f(r.get("organic")),
           "cluster_pct": _f(r.get("cluster_pct")), "fresh_pct": _f(r.get("fresh_pct")),
           "evm": 1.0 if (r.get("chain") or "solana") != "solana" else 0.0,
           "momentum": 1.0 if r.get("lane") == "momentum" else 0.0, "dial": _f(r.get("dial")),
           "rc_score": _f(r.get("rc_score")), "rc_danger": _f(r.get("rc_danger")), "rc_lp_locked": _f(r.get("rc_lp_locked"))}
    out.update({f"flag:{f}": 1.0 if f in flags else 0.0 for f in FLAGS})
    out.update({f"kill:{k}": 1.0 if reason == k else 0.0 for k in SOFT})
    return out


def dataset() -> list[dict]:
    """(features, label, time) for every shadowed token whose 6 h are over, oldest first."""
    import shadow
    rows = {}
    if os.path.exists(LOG):
        with open(LOG, newline="") as f:
            for r in csv.DictReader(f):
                rows.setdefault(r["mint"], []).append(r)
    out = []
    for s in sorted(shadow._rows(), key=lambda r: float(r["t"])):
        t = float(s["t"])
        if time.time() < t + shadow.HOURS * 3600:
            continue
        y = shadow.replay(s)
        if y is None:
            continue
        stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(t + 60))
        seen = [r for r in rows.get(s["mint"], []) if r["time"] <= stamp]
        if not seen:
            continue
        r = dict(seen[-1])
        if s["reason"] == "low_score":
            r["reason"] = "low_score"
        out.append({"x": features(r), "y": max(CLIP[0], min(CLIP[1], y)), "t": t})
    return out


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting: no numpy on the Mac."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        if abs(m[c][c]) < 1e-12:
            continue
        for r in range(n):
            if r != c:
                k = m[r][c] / m[c][c]
                m[r] = [x - k * y for x, y in zip(m[r], m[c])]
    return [m[i][n] / m[i][i] if abs(m[i][i]) > 1e-12 else 0.0 for i in range(n)]


def fit(data: list[dict], lam: float | None = None) -> dict:
    """Ridge regression on standardized features (missing = the mean). Returns the model."""
    names = sorted({k for d in data for k in d["x"]})
    cols = {k: [d["x"].get(k) for d in data] for k in names}
    mu = {k: (sum(v for v in vs if v is not None) / max(1, sum(v is not None for v in vs))) for k, vs in cols.items()}
    sd = {}
    for k, vs in cols.items():
        xs = [v for v in vs if v is not None]
        var = sum((v - mu[k]) ** 2 for v in xs) / max(1, len(xs) - 1) if len(xs) > 1 else 0
        sd[k] = math.sqrt(var) or 1.0
    keep = [k for k in names if any(v is not None and v != mu[k] for v in cols[k])]
    X = [[((d["x"].get(k) if d["x"].get(k) is not None else mu[k]) - mu[k]) / sd[k] for k in keep] for d in data]
    ys = [d["y"] for d in data]
    y0 = sum(ys) / len(ys)
    lam = lam if lam is not None else 0.3 * len(data)          # strong shrinkage: few, noisy lessons
    p = len(keep)
    xtx = [[sum(r[i] * r[j] for r in X) + (lam if i == j else 0) for j in range(p)] for i in range(p)]
    xty = [sum(r[i] * (y - y0) for r, y in zip(X, ys)) for i in range(p)]
    w = _solve(xtx, xty) if p else []
    return {"keep": keep, "mu": mu, "sd": sd, "w": dict(zip(keep, w)), "b": y0}


def predict(model: dict, x: dict) -> float:
    return model["b"] + sum(model["w"][k] * (((x.get(k) if x.get(k) is not None else model["mu"][k])
                                               - model["mu"][k]) / model["sd"][k]) for k in model["keep"])


def train() -> dict:
    """Validate on unseen data, then fit on everything. Saves data/model.json."""
    data = dataset()
    n = len(data)
    out = {"t": time.time(), "n": n, "trusted": False}
    cut = int(n * 0.7)
    if cut >= MIN_TRAIN and n - cut >= MIN_TEST:
        m = fit(data[:cut])
        test = data[cut:]
        preds = [(predict(m, d["x"]), d["y"]) for d in test]
        picks = [y for p, y in preds if p > 0]
        avg = sum(y for _, y in preds) / len(preds)
        pick_avg = sum(picks) / len(picks) if picks else None
        out.update(test_n=len(test), test_avg=round(avg, 1), picks=len(picks),
                   pick_avg=round(pick_avg, 1) if pick_avg is not None else None)
        # luck is the enemy: on pure noise a first version "beat" the average by 3.7 points on 54 picks.
        # its picks must clear zero and the average by more than their own noise (90% one-sided bound)
        if len(picks) > 1:
            sd_p = math.sqrt(sum((y - pick_avg) ** 2 for y in picks) / (len(picks) - 1))
            se = sd_p / math.sqrt(len(picks))
        else:
            se = float("inf")
        out["pick_low"] = round(pick_avg - 1.645 * se, 1) if pick_avg is not None and se != float("inf") else None
        out["trusted"] = bool(len(picks) >= MIN_PICKS and pick_avg is not None
                              and pick_avg - 1.645 * se > 0 and pick_avg - 1.645 * se >= avg + LIFT_PCT / 2
                              and pick_avg >= avg + LIFT_PCT)
        out["why"] = (f"sur {len(test)} tokens jamais vus, ses choix ({len(picks)}) font "
                      f"{pick_avg:+.1f} % contre {avg:+.1f} % pour la moyenne" if pick_avg is not None else
                      f"sur {len(test)} tokens jamais vus, il ne choisit aucun token : il prévoit une perte partout")
    else:
        out["why"] = f"{n} leçons : il en faut {MIN_TRAIN + MIN_TEST} pour s'entraîner et se tester"
    if n >= 20:
        out["model"] = fit(data)
        mdl = out["model"]
        binary = lambda k: k.startswith(("flag:", "kill:")) or k in ("evm", "momentum")
        # a yes/no feature: its effect when present. a number: its effect for one standard deviation more
        eff = {k: (w / mdl["sd"][k] if binary(k) else w) for k, w in mdl["w"].items()}
        top = sorted(eff.items(), key=lambda kv: -abs(kv[1]))[:6]
        out["lessons"] = [{"feature": k, "effect": round(v, 1), "binary": binary(k)} for k, v in top]
    tmp = atomic.tmp(MODEL)
    os.makedirs(DATA, exist_ok=True)
    with open(tmp, "w") as f:
        json.dump(out, f)
    os.replace(tmp, MODEL)
    return out


_cache = {"t": 0.0, "v": None}


def load() -> dict:
    if time.time() - _cache["t"] > 300:
        try:
            with open(MODEL) as f:
                _cache["v"] = json.load(f)
        except (OSError, ValueError):
            _cache["v"] = None
        _cache["t"] = time.time()
    return _cache["v"] or {}


def due() -> bool:
    return time.time() - load().get("t", 0) > RETRAIN_S


def expected(row: dict) -> float | None:
    """Predicted net % per trade for a token as GARDE sees it now, if the model is trusted; else None."""
    m = load()
    if not m.get("trusted") or not m.get("model"):
        return None
    return predict(m["model"], features(row))


def explain(lesson: dict) -> str:
    k, e = lesson["feature"], lesson["effect"]
    if k.startswith("flag:"):
        what = f"le signal « {k[5:]} »"
    elif k.startswith("kill:"):
        what = f"les tokens écartés pour « {k[5:]} »"
    else:
        what = WORDS.get(k, k)
    return f"{what} : {e:+.1f} % par trade" + ("" if lesson.get("binary", True) else " (pour un écart-type de plus)")
