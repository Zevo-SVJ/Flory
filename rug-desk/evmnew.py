# evmnew.py
# SCOUT's launch feed for the EVM chains: what grads.py is for Solana. GeckoTerminal's newest pools across
# every network (free, no key), kept for the chains in chains.py, then priced every run until they are
# old enough for GARDE (FACTS min_age_min) or dead. a pool under $10k two hours after birth is dropped.
import json, os, time
import requests
from config import DATA, FACTS
import atomic, chains, gt

STATE = os.path.join(DATA, "evm_new.json")
NEW = "https://api.geckoterminal.com/api/v2/networks/new_pools"
PAGES = 2                      # 20 pools a page, every 3 min: the busiest chains add fewer than that
error = None


def load() -> dict:
    try:
        with open(STATE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save(s: dict):
    os.makedirs(DATA, exist_ok=True)
    tmp = atomic.tmp(STATE)
    with open(tmp, "w") as f:
        json.dump(s, f)
    os.replace(tmp, STATE)


def fetch() -> int:
    """Read the newest pools on every network; keep the EVM chains the desk trades. Returns new tokens."""
    global error
    s, new = load(), 0
    try:
        for page in range(1, PAGES + 1):
            r = gt.get(NEW, params={"page": page})                     # the shared budget (gt.py)
            r.raise_for_status()
            for p in r.json().get("data") or []:
                rel = p.get("relationships") or {}
                net = ((rel.get("network") or {}).get("data") or {}).get("id") or ""
                chain = chains.GT_TO_CHAIN.get(net)
                base = ((rel.get("base_token") or {}).get("data") or {}).get("id") or ""
                name = ((p.get("attributes") or {}).get("name") or "").split(" / ")[0].strip().lower()
                if not chain or chain == "solana" or not base.startswith(net + "_") or name in chains.NOT_MEMES:
                    continue
                k = chains.key(chain, base[len(net) + 1:])
                if k not in s:
                    s[k] = time.time()
                    new += 1
        error = None
    except Exception as e:
        error = f"GeckoTerminal new pools unreadable: {e}"[:200]
    cutoff = time.time() - FACTS["max_age_hours"] * 3600
    save({k: t for k, t in s.items() if t >= cutoff})
    return new


def recent() -> list[str]:
    return [k for k, _ in sorted(load().items(), key=lambda kv: -kv[1])]


def forget(keys: list[str]):
    s = load()
    for k in keys:
        s.pop(k, None)
    save(s)
