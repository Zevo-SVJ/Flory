# scan.py
# optional lead source: fresh Solana tokens that paid DexScreener for a profile or a boost.
# paying is not a quality signal, it just means the dev spent money. the filter decides.
import csv, json, os, time
import requests
from config import LOG, SCHEDULE
import check

SOURCES = ["token-profiles/latest/v1", "token-boosts/latest/v1", "token-boosts/top/v1"]
# kills that can change with time: a pool grows up, a source comes back. retried after this long
RETRY_AFTER_MIN = 30
RETRYABLE = ("too_fresh", "thin_pool", "no_pool", "no_price", "no_report")


def _done() -> set[str]:
    """Mints we never need to look at again: a final verdict, or a retryable kill that's still recent."""
    if not os.path.exists(LOG):
        return set()
    last = {}
    with open(LOG, newline="") as f:
        for r in csv.DictReader(f):
            last[r["mint"]] = r
    cutoff = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - RETRY_AFTER_MIN * 60))
    done = set()
    for mint, r in last.items():
        reason = r["reason"] or ""
        retry = reason in RETRYABLE or " failed" in reason or r["stage"] == "limits"
        if not retry or r["time"] > cutoff:
            done.add(mint)
    return done


def leads() -> list[str]:
    done, out, errors = _done(), [], []
    for src in SOURCES:
        try:
            r = requests.get(f"https://api.dexscreener.com/{src}", timeout=15)
            r.raise_for_status()
        except Exception as e:
            errors.append(f"{src}: {e}")
            continue
        for t in r.json():
            a = t.get("tokenAddress")
            if t.get("chainId") == "solana" and a and a not in done and a not in out:
                out.append(a)
    if len(errors) == len(SOURCES):
        raise RuntimeError("; ".join(errors))
    return out[:SCHEDULE["scan_per_run"]]


def scan() -> list[dict]:
    return [{"mint": m, **check.run(m)} for m in leads()]


if __name__ == "__main__":
    for v in scan():
        print(json.dumps(v))
