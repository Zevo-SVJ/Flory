# smart.py
# the desk's memory of wallets, the mirror of ruggers.py. no free API ranks wallets honestly (public
# leaderboards reward one lucky trade and ignore what a follower would really get), so the desk keeps
# its own record: the top holders GARDE saw on every token, scored later by AUDIT on what the token did.
# a wallet that was early in several tokens that ran, and rarely in ones that crashed, is "smart".
# research hint: wallets with strong past results joining a launch help predict its success
# (Marino et al., arXiv 2602.14860); several smart wallets in the same token is the stronger signal.
import json, os
from config import DATA

HOLDERS = os.path.join(DATA, "holders")
MEMORY = os.path.join(DATA, "smart.json")
MIN_RUNS = 2               # a wallet needs at least two tokens that ran...
RUN_PCT, CRASH_PCT = 100, -50


def snapshot(mint: str, wallets: list[str]):
    """The top holder wallets GARDE saw when it checked this token."""
    if not wallets:
        return
    os.makedirs(HOLDERS, exist_ok=True)
    with open(os.path.join(HOLDERS, f"{mint}.json"), "w") as f:
        json.dump(wallets, f)


def memory() -> dict:
    if not os.path.exists(MEMORY):
        return {}
    with open(MEMORY) as f:
        return json.load(f)


def learn(mint: str, change_pct: float) -> int:
    """AUDIT calls this once per audited token. Returns how many wallets it updated."""
    path = os.path.join(HOLDERS, f"{mint}.json")
    if not os.path.exists(path) or CRASH_PCT < change_pct < RUN_PCT:
        return 0
    with open(path) as f:
        wallets = json.load(f)
    mem = memory()
    key = "runs" if change_pct >= RUN_PCT else "crashes"
    for w in wallets:
        mem.setdefault(w, {"runs": 0, "crashes": 0})[key] += 1
    with open(MEMORY, "w") as f:
        json.dump(mem, f)
    return len(wallets)


def is_smart(rec: dict) -> bool:
    return rec["runs"] >= MIN_RUNS and rec["runs"] >= 2 * rec["crashes"]   # ...and twice as many runs as crashes


def count(wallets: list[str]) -> int:
    mem = memory()
    return sum(1 for w in wallets or [] if w in mem and is_smart(mem[w]))


def known() -> int:
    return sum(1 for r in memory().values() if is_smart(r))
