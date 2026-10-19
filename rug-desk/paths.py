# paths.py
# every price VIGIE sees for a traded token, kept on disk: during the trade and for 6 hours after the
# exit (a "ghost"), so the exit lab can replay other exit rules and see what each would have earned.
import csv, json, os, time
from config import PATHS, DATA

GHOSTS = os.path.join(DATA, "ghosts.json")
GHOST_HOURS = 6
FIELDS = ["t", "price", "liq", "b5", "s5", "v5"]


def _file(mint: str) -> str:
    return os.path.join(PATHS, f"{mint}.csv")


def append(mint: str, s: dict):
    os.makedirs(PATHS, exist_ok=True)
    f, new = _file(mint), not os.path.exists(_file(mint))
    with open(f, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: s.get(k) for k in FIELDS})


def load(mint: str, since: float = 0, until: float | None = None) -> list[dict]:
    if not os.path.exists(_file(mint)):
        return []
    out = []
    with open(_file(mint), newline="") as fh:
        for r in csv.DictReader(fh):
            t = float(r["t"])
            if t >= since and (until is None or t <= until):
                out.append({"t": t, "price": float(r["price"] or 0),
                            **{k: float(r[k]) if r[k] not in ("", None) else None for k in ("liq", "b5", "s5", "v5")}})
    return out


def ghosts() -> dict:
    if not os.path.exists(GHOSTS):
        return {}
    with open(GHOSTS) as f:
        g = json.load(f)
    now = time.time()
    return {m: u for m, u in g.items() if u > now}


def haunt(mint: str):
    """Keep pricing a token for GHOST_HOURS after the desk sold it."""
    g = ghosts()
    g[mint] = time.time() + GHOST_HOURS * 3600
    os.makedirs(DATA, exist_ok=True)
    with open(GHOSTS, "w") as f:
        json.dump(g, f)
