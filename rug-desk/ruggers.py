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
