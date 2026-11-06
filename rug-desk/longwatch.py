# longwatch.py
# does a token caught at 150k-1M of market cap often go on to 3, 5, 10M? Skide sees it often; the shadow book
# follows each token 6 h only, and such runs take days. a sample of the tokens GARDE judges in that range,
# whatever its verdict, is priced for 7 days (paths.py, every 20 s like any ghost). nothing is bought.
#   python3 diag.py --longs     the multiples reached after 1, 3 and 7 days, by chain and by verdict
import csv, os, time
from config import DATA
import paths

FILE = os.path.join(DATA, "longwatch.csv")
FIELDS = ["t", "mint", "symbol", "chain", "mcap", "price", "liq", "verdict", "reason"]
CAP_LO, CAP_HI = 150_000, 1_000_000
DAYS = 7
MAX_ACTIVE = 60             # tokens priced for 7 days at once: VIGIE prices every ghost every 20 s


def rows() -> list[dict]:
    try:
        with open(FILE, newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def note(mint: str, v: dict) -> bool:
    """Called for every GARDE verdict. True if the token is now watched for 7 days."""
    try:
        mcap = float(v.get("mcap_liq") or 0) * float(v.get("liq_usd") or 0)
        price = float(v.get("price") or 0)
    except (TypeError, ValueError):
        return False
    if not CAP_LO <= mcap <= CAP_HI or price <= 0:
        return False
    rs = rows()
    now = time.time()
    if any(r["mint"] == mint for r in rs) or sum(now - float(r["t"]) < DAYS * 86400 for r in rs) >= MAX_ACTIVE:
        return False
    os.makedirs(DATA, exist_ok=True)
    new = not os.path.exists(FILE)
    with open(FILE, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({"t": round(now), "mint": mint, "symbol": v.get("symbol") or mint[:6], "chain": v.get("chain"),
                    "mcap": round(mcap), "price": price, "liq": v.get("liq_usd"), "verdict": v.get("verdict"),
                    "reason": (v.get("reason") or "")[:40]})
    paths.haunt(mint, DAYS * 24)
    return True
