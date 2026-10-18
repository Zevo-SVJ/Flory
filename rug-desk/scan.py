# scan.py
# optional lead source: fresh Solana tokens that just paid for a DexScreener profile.
# a paid profile is not a quality signal, it just means the dev spent money. the filter decides.
import csv, json, os
import requests
from config import LOG, SCHEDULE
import check


def leads() -> list[str]:
    seen = set()
    if os.path.exists(LOG):
        with open(LOG, newline="") as f:
            seen = {r["mint"] for r in csv.DictReader(f)}
    r = requests.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=15)
    r.raise_for_status()
    out = []
    for t in r.json():
        a = t.get("tokenAddress")
        if t.get("chainId") == "solana" and a and a not in seen and a not in out:
            out.append(a)
    return out[:SCHEDULE["scan_per_run"]]


def scan() -> list[dict]:
    return [{"mint": m, **check.run(m)} for m in leads()]


if __name__ == "__main__":
    for v in scan():
        print(json.dumps(v))
