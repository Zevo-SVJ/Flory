# coach.py
# every agent looks at its own decisions, finds its mistakes, and changes one thing when the data says so.
# the danger is learning from noise: with tokens that move +-70% in a few hours, the "best" of ten
# variants wins by luck most of the time (Bailey & Lopez de Prado on backtest overfitting). so no agent
# changes itself directly. it proposes; the coach applies a change only past these guards:
#   1. enough cases           MIN_N lessons behind any change, never one token
#   2. beyond noise           paired gain, its 1-sided lower bound above a margin, z raised for the
#                             number of variants tried (more tries, higher bar)
#   3. both halves            the gain holds on the older half and on the newer half of the data
#   4. one at a time          one change per agent per RATE_S, a value from a closed list only
#   5. checked afterwards     after EVAL_S, the change is re-tested on data it never saw; worse -> undone
#   6. circuit breaker        the balance down CIRCUIT_PCT within 24 h of a change -> every recent change undone
# every change and every undo is written to data/journal.jsonl, shown on the dashboard, sent to Telegram.
# config.py is never touched: changes live in data/tuning.json and vanish with it.
import json, math, os, statistics, time
from config import DATA, PAPER_BANKROLL_USD
import atomic

JOURNAL = os.path.join(DATA, "journal.jsonl")
TUNING = os.path.join(DATA, "tuning.json")
REVIEWS = os.path.join(DATA, "reviews.json")
MIN_N = 40
RATE_S = 24 * 3600
EVAL_S = 48 * 3600
CIRCUIT_PCT = 10.0
LOCKED = set()           # keys nobody may change by itself (add one here to freeze it)


def z_for(k: int) -> float:
    """One-sided z for a 10% family-wise error over k variants (Bonferroni): 1 -> 1.28, 10 -> 2.33."""
    import statistics as st
    return st.NormalDist().inv_cdf(1 - 0.10 / max(1, k))


def paired(diffs: list[float], k: int = 1, margin: float = 1.0) -> dict:
    """Is a paired gain (new - old, per case) real? n, mean, lower bound, both halves, verdict."""
    n = len(diffs)
    out = {"n": n, "ok": False}
    if n < 2:
        return {**out, "why": f"{n} cas : il en faut {MIN_N}"}
    m = statistics.mean(diffs)
    se = statistics.stdev(diffs) / math.sqrt(n)
    h = n // 2
    a, b = statistics.mean(diffs[:h]) if h else 0, statistics.mean(diffs[h:])
    low = m - z_for(k) * se
    out.update(mean=round(m, 2), low=round(low, 2), half1=round(a, 2), half2=round(b, 2))
    if n < MIN_N:
        out["why"] = f"{n} cas : il en faut {MIN_N}"
    elif low <= margin:
        out["why"] = f"gain {m:+.1f} pts mais dans le bruit (borne basse {low:+.1f})"
    elif a <= 0 or b <= 0:
        out["why"] = f"gain sur une seule moitié ({a:+.1f} / {b:+.1f})"
    else:
        out.update(ok=True, why=f"gain {m:+.1f} pts par trade sur {n} cas, borne basse {low:+.1f}, les deux moitiés positives")
    return out


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


def tuning() -> dict:
    return _read(TUNING, {})


def get(key: str, default=None):
    return tuning().get(key, default)


def journal(last: int | None = None) -> list[dict]:
    try:
        with open(JOURNAL) as f:
            rows = [json.loads(l) for l in f if l.strip()]
    except (OSError, ValueError):
        rows = []
    return rows[-last:] if last else rows


def _log(entry: dict):
    os.makedirs(DATA, exist_ok=True)
    with open(JOURNAL, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _update(entry_id: str, **fields):
    rows = journal()
    for r in rows:
        if r["id"] == entry_id:
            r.update(fields)
    os.makedirs(DATA, exist_ok=True)
    tmp = atomic.tmp(JOURNAL)
    with open(tmp, "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)
    os.replace(tmp, JOURNAL)


def can_change(agent: str, key: str) -> str | None:
    """None if allowed, else why not."""
    if key in LOCKED:
        return f"« {key} » est verrouillé"
    recent = [r for r in journal() if r["agent"] == agent and r["status"] in ("active", "confirmed")
              and time.time() - r["t"] < RATE_S]
    if recent:
        return f"{agent} a déjà changé quelque chose il y a moins de 24 h"
    return None


def apply(agent: str, key: str, new, evidence: dict, balance: float | None = None) -> dict | None:
    """Change one tuning value if the guards allow. Returns the journal entry, or None."""
    if can_change(agent, key) or not evidence.get("ok"):
        return None
    t = tuning()
    old = t.get(key)
    if old == new:
        return None
    t[key] = new
    _write(TUNING, t)
    entry = {"id": f"{int(time.time())}-{agent}-{key}", "t": time.time(), "agent": agent, "key": key,
             "old": old, "new": new, "why": evidence.get("why"), "evidence": {k: evidence.get(k) for k in
             ("n", "mean", "low", "half1", "half2")}, "status": "active", "balance": balance}
    _log(entry)
    return entry


def undo(entry: dict, why: str):
    t = tuning()
    if entry["old"] is None:
        t.pop(entry["key"], None)
    else:
        t[entry["key"]] = entry["old"]
    _write(TUNING, t)
    _update(entry["id"], status="rolled_back", undone_at=time.time(), undone_why=why)


def evaluate(tests: dict) -> list[dict]:
    """Re-test every active change older than EVAL_S on the data that came after it.
    tests: {key: f(entry) -> paired() result of new vs old on post-change cases}."""
    out = []
    for e in journal():
        if e["status"] != "active" or time.time() - e["t"] < EVAL_S or e["key"] not in tests:
            continue
        res = tests[e["key"]](e)
        if res.get("n", 0) < MIN_N // 2:
            continue                                           # not enough new cases yet: wait
        if res.get("mean", 0) < 0:
            undo(e, f"après le changement : {res.get('mean'):+.1f} pts sur {res['n']} nouveaux cas")
            out.append({**e, "status": "rolled_back"})
        else:
            _update(e["id"], status="confirmed", confirmed_at=time.time())
            out.append({**e, "status": "confirmed"})
    return out


def circuit(balance: float) -> list[dict]:
    """The balance fell CIRCUIT_PCT of the bankroll since a change made in the last 24 h: undo them all."""
    out = []
    for e in journal():
        if e["status"] == "active" and time.time() - e["t"] < 24 * 3600 and e.get("balance") is not None \
                and balance < e["balance"] - CIRCUIT_PCT / 100 * PAPER_BANKROLL_USD:
            undo(e, f"disjoncteur : le solde a perdu plus de {CIRCUIT_PCT:.0f} % de la banque depuis")
            out.append(e)
    return out


def save_reviews(reviews: dict):
    _write(REVIEWS, {"t": time.time(), **reviews})


def reviews() -> dict:
    return _read(REVIEWS, {})
