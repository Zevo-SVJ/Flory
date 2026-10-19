# ruggers.py
# the desk's own blacklist of token creators. no free API says "this dev rugged before", so the desk
# learns it: when a token it saw crashes (AUDIT: -80% or worse) or its pool is pulled (VIGIE), the
# creator wallet goes on the list, and GARDE kills every later token from that wallet.
import csv, os, time
from config import DATA

FILE = os.path.join(DATA, "ruggers.csv")
FIELDS = ["time", "dev", "mint", "symbol", "why"]


def known() -> set[str]:
    if not os.path.exists(FILE):
        return set()
    with open(FILE, newline="") as f:
        return {r["dev"] for r in csv.DictReader(f) if r.get("dev")}


def add(dev: str | None, mint: str, symbol: str, why: str) -> bool:
    """Returns True if the dev is new on the list."""
    if not dev or dev in known():
        return False
    os.makedirs(DATA, exist_ok=True)
    new = not os.path.exists(FILE)
    with open(FILE, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({"time": time.strftime("%Y-%m-%d %H:%M"), "dev": dev, "mint": mint, "symbol": symbol, "why": why})
    return True


def dev_of(mint: str) -> str | None:
    """The creator GARDE recorded for this token, from checks.csv."""
    from config import LOG
    if not os.path.exists(LOG):
        return None
    dev = None
    with open(LOG, newline="") as f:
        for r in csv.DictReader(f):
            if r["mint"] == mint and r.get("dev"):
                dev = r["dev"]
    return dev


# the factory's money: funders of linked holder groups (cluster.py) on tokens that then rugged.
# a factory reuses its funding wallets, so a holder funded by one of them kills the next token.
import json
FUNDERS = os.path.join(DATA, "rug_funders.json")
SEEN = os.path.join(DATA, "token_funders.json")        # mint -> cluster funder found at check time


def _load(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(path: str, d: dict):
    os.makedirs(DATA, exist_ok=True)
    with open(path + ".tmp", "w") as f:
        json.dump(d, f)
    os.replace(path + ".tmp", path)


def note_funder(mint: str, funder: str | None):
    if funder:
        d = _load(SEEN)
        d[mint] = funder
        _save(SEEN, d)


def funder_rugged(mint: str, symbol: str) -> str | None:
    """The token rugged: its cluster funder goes on the list. Returns the funder, if one was known."""
    f = _load(SEEN).get(mint)
    if f:
        d = _load(FUNDERS)
        d[f] = {"mint": mint, "symbol": symbol, "time": time.strftime("%Y-%m-%d %H:%M")}
        _save(FUNDERS, d)
    return f


def funders() -> set[str]:
    return set(_load(FUNDERS))
