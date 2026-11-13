# exitmodel.py
# exits that adapt to each memecoin. one rule for every token (a 30% trail, a 45 min stall, a +5% floor) sells
# a slow grinder too early and a wild one too late. this model reads, at every tick of a position, what the
# shadow book's thousands of 6 h price paths say happens next to a token in the same state, and the profile
# "adaptatif" sells when holding no longer pays:
#   gain since entry · fall from the peak · minutes since the peak · minutes held · volatility of the hour ·
#   5-min volume against its hour · buyers' share of the last 5 min swaps · the pool against its size at the
#   buy · the move of the last 5 and 15 min · whether the first profit was taken
# label: the token's move over the next 30 min. a ridge regression, the same small kind as learn.py (no numpy
# on the Mac), standardized from running sums so a million ticks fit in memory.
# the threshold under which it sells is picked on the older 70% of the tokens and judged on the newer 30%,
# never seen: it is kept only if it beats the profile in force there. the pool, the hard stop and the first
# take (half at x2) stay above it, whatever it says. VIGIE uses it only once the exit lab activates it
# (python3 exitlab.py activer adaptatif "...") under the usual rule: better on both halves, beyond the noise.
#
#   python3 exitmodel.py          trains on the shadow book, prints the held-out comparison, saves the model
import json, math, os, statistics, sys, time
from config import DATA

MODEL = os.path.join(DATA, "exit_model.json")
HORIZON_S = 1800             # what the model predicts: the next 30 min
STEP = 6                     # one training tick in 6 (~2 min): neighbouring ticks say the same thing
MAX_TOKENS = 1500            # the most recent shadows: enough, and a few minutes on the Mac
CLIP = 100.0
LAMBDA = 50.0                # shrinkage on standardized features
THETAS = (-0.5, -1.0, -2.0, -4.0, -8.0, -12.0, -20.0)   # % over the next 30 min under which a position is sold
NAMES = ["gain", "dd", "since_peak", "held", "vol", "vratio", "buyers", "liq", "r5", "r15", "took"]
_cache = {"m": None, "mtime": None, "override": None}


def vec(pos: dict, s: dict) -> list[float]:
    """The state of one position at one tick, in the order of NAMES."""
    price, entry, peak = s["price"], pos["entry"], max(pos["peak"], s["price"])
    lg = lambda a, b: math.log(a / b) if a and b and a > 0 and b > 0 else 0.0
    b5, s5 = s.get("b5"), s.get("s5")
    liq0, liq = pos.get("liq_ref") or pos.get("liq0"), s.get("liq")
    return [lg(price, entry), lg(price, peak),
            math.log1p(max(0.0, s["t"] - pos.get("peak_t", pos["opened"])) / 60),
            math.log1p(max(0.0, s["t"] - pos["opened"]) / 60),
            min(s.get("vol") or 10.0, 200.0) / 100,
            lg((s.get("v5") or 0) + 1, (s.get("v5_avg") or 0) + 1),
            b5 / (b5 + s5) if b5 is not None and s5 is not None and b5 + s5 > 0 else 0.5,
            lg(liq, liq0) if liq else 0.0,
            math.log1p(max(-0.99, s.get("r5") or 0.0)), math.log1p(max(-0.99, s.get("r15") or 0.0)),
            1.0 if pos.get("steps", 0) > 0 else 0.0]


def predict(m: dict, x: list[float]) -> float:
    return m["b"] + sum(w * (v - mu) / sd for w, v, mu, sd in zip(m["w"], x, m["mu"], m["sd"]))


def load() -> dict | None:
    """The saved model, re-read only when the file changes. None until exitmodel.py has run."""
    if _cache["override"] is not None:          # training: the candidate being judged
        return _cache["override"]
    try:
        mt = os.path.getmtime(MODEL)
    except OSError:
        return None
    if _cache["mtime"] != mt:
        try:
            with open(MODEL) as f:
                _cache["m"], _cache["mtime"] = json.load(f), mt
        except (OSError, ValueError):
            return None
    return _cache["m"]


def _walk(path: list[dict]):
    """(state vector, next-30-min move in %) along one shadow path, as a position bought at its start."""
    pos = {"entry": path[0]["price"], "peak": path[0]["price"], "peak_t": path[0]["t"], "opened": path[0]["t"],
           "liq0": path[0].get("liq"), "steps": 0}
    j = 0
    for i, s in enumerate(path):
        if s["price"] <= 0:
            return
        if s["price"] > pos["peak"]:
            pos["peak"], pos["peak_t"] = s["price"], s["t"]
        if s["price"] >= 2 * pos["entry"]:
            pos["steps"] = 1
        if i % STEP or s["t"] - pos["opened"] < 120:
            continue
        while j < len(path) - 1 and path[j]["t"] < s["t"] + HORIZON_S:
            j += 1
        if path[j]["t"] < s["t"] + HORIZON_S - 120:
            return                               # the path ends before the 30 min are over
        fut = path[j]["price"]
        y = max(-CLIP, min(CLIP, 100 * math.log(fut / s["price"]))) if fut > 0 else -CLIP
        yield vec(pos, s), y


def fit(paths: list[list[dict]]) -> dict:
    """Ridge on standardized features, from running sums: Z'Z = (X'X - n mu mu') / (sd sd')."""
    p = len(NAMES)
    n, sx, sy = 0, [0.0] * p, 0.0
    sxx = [[0.0] * p for _ in range(p)]
    sxy, syy = [0.0] * p, 0.0
    for path in paths:
        for x, y in _walk(path):
            n += 1
            sy += y
            syy += y * y
            for a in range(p):
                sx[a] += x[a]
                sxy[a] += x[a] * y
                for b in range(a, p):
                    sxx[a][b] += x[a] * x[b]
    if n < 1000:
        raise RuntimeError(f"trop peu de ticks pour apprendre ({n})")
    mu = [v / n for v in sx]
    sd = [math.sqrt(max(sxx[a][a] / n - mu[a] ** 2, 1e-12)) for a in range(p)]
    ybar = sy / n
    ztz = [[((sxx[min(a, b)][max(a, b)] - n * mu[a] * mu[b]) / (sd[a] * sd[b])) + (LAMBDA if a == b else 0)
            for b in range(p)] for a in range(p)]
    zty = [(sxy[a] - n * mu[a] * ybar) / sd[a] for a in range(p)]
    import learn
    w = learn._solve(ztz, zty)
    return {"w": w, "mu": mu, "sd": sd, "b": ybar, "n_ticks": n, "names": NAMES}


def _mean(xs):
    return round(statistics.mean(xs), 1) if xs else None


def train() -> dict:
    import shadow, exitlab, exits
    rows = sorted((r for r in shadow._rows() if time.time() >= float(r["t"]) + shadow.HOURS * 3600),
                  key=lambda r: float(r["t"]))[-MAX_TOKENS:]
    data = []
    for i, r in enumerate(rows):
        got = shadow.path(r)
        if got:
            data.append((r, got[0], got[1]))
        if (i + 1) % 250 == 0:
            print(f"  {i + 1}/{len(rows)} trajets lus…", flush=True)
    if len(data) < 100:
        raise RuntimeError(f"trop peu de trajets fantômes ({len(data)})")
    cut = int(len(data) * 0.7)
    train_set, test_set = data[:cut], data[cut:]
    m = fit([p for _, p, _ in train_set])
    active = exits.active()

    def net(path, cost, params):
        g = exitlab.simulate(path, params)
        return None if g is None else g / exitlab.TICKET_USD * 100 - cost

    best = None
    for th in THETAS:                            # the threshold, chosen on the older 70% only
        _cache["override"] = {**m, "theta": th}
        xs = [x for _, p, c in train_set[::3] if (x := net(p, c, {**active, "adaptive": True})) is not None]
        if xs and (best is None or statistics.mean(xs) > best[1]):
            best = (th, statistics.mean(xs))
    m["theta"] = best[0]
    _cache["override"] = m
    ada, act = [], []
    for _, p, c in test_set:                     # judged on the newer 30%, never seen
        a, b = net(p, c, {**active, "adaptive": True}), net(p, c, active)
        if a is not None and b is not None:
            ada.append(a)
            act.append(b)
    h = len(ada) // 2
    m["test"] = {"n": len(ada), "adaptatif": _mean(ada), "actif": _mean(act),
                 "halves_adaptatif": [_mean(ada[:h]), _mean(ada[h:])], "halves_actif": [_mean(act[:h]), _mean(act[h:])],
                 "without_top5_adaptatif": _mean(sorted(ada)[:-5]), "without_top5_actif": _mean(sorted(act)[:-5])}
    m["trained"] = time.strftime("%Y-%m-%d %H:%M")
    _cache["override"], _cache["m"], _cache["mtime"] = None, None, None
    os.makedirs(DATA, exist_ok=True)
    with open(MODEL, "w") as f:
        json.dump(m, f, indent=1)
    return m


if __name__ == "__main__":
    # run through the module itself: exits.decide imports "exitmodel", and the candidate being judged must be
    # the one it sees (as __main__ this file is a second copy, and the first run judged the profile in force)
    import exitmodel
    m = exitmodel.train()
    t = m["test"]
    print(f"\nmodèle appris sur {m['n_ticks']} ticks · vend sous {m['theta']} % prévu sur 30 min")
    print("poids (standardisés) : " + " · ".join(f"{k} {w:+.2f}" for k, w in zip(m["names"], m["w"])))
    print(f"\njugé sur {t['n']} tokens jamais vus (les 30 % les plus récents), même trajets, mêmes coûts :")
    print(f"  adaptatif : moyenne {t['adaptatif']:+} % · moitiés {t['halves_adaptatif']} · sans top 5 {t['without_top5_adaptatif']:+}")
    print(f"  actif     : moyenne {t['actif']:+} % · moitiés {t['halves_actif']} · sans top 5 {t['without_top5_actif']:+}")
    print("\nle labo de sortie (python3 exitlab.py) compare maintenant aussi « adaptatif » sur les vrais trades")
