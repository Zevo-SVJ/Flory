# grads.py
# SCOUT's on-chain source: every token that graduates from the pump.fun bonding curve to PumpSwap.
# pump.fun's migration account signs one transaction (sometimes two) per graduation, nothing else,
# so its signature list is the full feed of new PumpSwap pools, without DexScreener's paid lists.
# the DexScreener search mostly returns old pools: on a live test, 0 young PumpSwap pools out of 6 words.
import json, os, time
from config import DATA, FACTS
import facts

MIGRATION = "39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg"   # pump.fun's migration authority
WSOL = "So11111111111111111111111111111111111111112"
STATE = os.path.join(DATA, "graduates.json")
PER_RUN = 80         # transactions read per SCOUT run at most (about 1 h of graduations)


def load() -> dict:
    try:
        with open(STATE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"last_sig": None, "mints": {}}


def save(s: dict):
    os.makedirs(DATA, exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(s, f)
    os.replace(tmp, STATE)


def fetch() -> int:
    """Read the graduations signed since the last run. Returns how many new tokens were found."""
    s = load()
    params = {"limit": 100}
    if s["last_sig"]:
        params["until"] = s["last_sig"]
    sigs = facts._rpc("getSignaturesForAddress", [MIGRATION, params]) or []
    if sigs:
        s["last_sig"] = sigs[0]["signature"]
    new = 0
    for sig in [x for x in sigs if not x.get("err")][:PER_RUN]:
        try:
            tx = facts._rpc("getTransaction", [sig["signature"], {"maxSupportedTransactionVersion": 1,
                                                                  "encoding": "jsonParsed"}])
        except Exception:
            continue                      # one unreadable transaction is not a reason to stop
        meta = (tx or {}).get("meta") or {}
        if not any("Instruction: Migrate" in l for l in meta.get("logMessages") or []):
            continue
        for b in meta.get("postTokenBalances") or []:
            m = b.get("mint")
            if m and m != WSOL and m not in s["mints"]:
                s["mints"][m] = sig.get("blockTime") or time.time()
                new += 1
    cutoff = time.time() - FACTS["max_age_hours"] * 3600
    s["mints"] = {m: t for m, t in s["mints"].items() if t >= cutoff}
    save(s)
    return new


def recent() -> list[str]:
    """Graduates still inside the age window, newest first."""
    return [m for m, _ in sorted(load()["mints"].items(), key=lambda kv: -kv[1])]


def forget(mints: list[str]):
    """Graduates whose pool died: no need to price them every run for 3 days."""
    s = load()
    for m in mints:
        s["mints"].pop(m, None)
    save(s)


if __name__ == "__main__":
    print(fetch(), "new graduate(s);", len(recent()), "in the window")
