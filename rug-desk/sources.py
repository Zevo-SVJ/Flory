# sources.py
# what each outside source last answered, written by the desk, read by the dashboard (two processes).
# without it, a source that silently fails (a key revoked, an API moved) looks the same as a clean token.
import json, os, time
from config import DATA

FILE = os.path.join(DATA, "sources.json")


def record(name: str, ok: bool, detail: str = ""):
    try:
        with open(FILE) as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d[name] = {"ok": ok, "t": time.time(), "detail": detail[:120]}
    os.makedirs(DATA, exist_ok=True)
    with open(FILE + ".tmp", "w") as f:
        json.dump(d, f)
    os.replace(FILE + ".tmp", FILE)


def load() -> dict:
    try:
        with open(FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def calls_today(name: str) -> int:
    """How many calls a metered source got today (Solana Tracker's free plan is 2,500 a month)."""
    d = load().get(f"{name}_count") or {}
    return d.get("n", 0) if d.get("day") == time.strftime("%Y-%m-%d") else 0


def count_call(name: str):
    d = load()
    day = time.strftime("%Y-%m-%d")
    c = d.get(f"{name}_count") or {}
    d[f"{name}_count"] = {"day": day, "n": (c.get("n", 0) if c.get("day") == day else 0) + 1}
    with open(FILE + ".tmp", "w") as f:
        json.dump(d, f)
    os.replace(FILE + ".tmp", FILE)


USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


def probe() -> list[str]:
    """At start: ask every outside source about USDC once, so a dead key or a moved API shows on the
    dashboard within a minute, not the first time a good token reaches the deep read. one Solana Tracker
    credit per start."""
    import facts, jup, stracker
    out = []
    try:
        jup.fetch(USDC)
    except Exception as e:
        out.append(f"Jupiter: {e}")
    if "helius" in facts.RPC_URL:
        try:
            facts._rpc("getTokenAccounts", {"mint": USDC, "limit": 1, "page": 1})
            record("helius_das", True, "ok")
        except Exception as e:
            record("helius_das", False, str(e))
            out.append(f"Helius DAS: {e}")
    if stracker.key():
        try:
            stracker.fetch(USDC)
        except Exception as e:
            out.append(f"Solana Tracker: {e}")
    return out
