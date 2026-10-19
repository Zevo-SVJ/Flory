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
    """The holder wallets GARDE saw when it checked this token: every holder above 0.01% of supply with
    Helius (a factory hides below the top 10), else the top 10."""
    if not wallets:
        return
    os.makedirs(HOLDERS, exist_ok=True)
    with open(os.path.join(HOLDERS, f"{mint}.json"), "w") as f:
        json.dump(wallets, f)


SEED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seeds", "factory_wallets.json")


def memory() -> dict:
    """What the desk learned, on top of the factory wallets found by hand (seeds/), which count as
    two crashes each: they sold in the one-block dumps of several Oct 19 rugs."""
    mem = {}
    if os.path.exists(SEED):
        with open(SEED) as f:
            mem = {w: {"runs": 0, "crashes": 2} for w in json.load(f)}
    if os.path.exists(MEMORY):
        with open(MEMORY) as f:
            mem.update(json.load(f))
    return mem


def learn(mint: str, change_pct: float) -> int:
    """AUDIT calls this once per audited token. Returns how many wallets it updated."""
    path = os.path.join(HOLDERS, f"{mint}.json")
    if not os.path.exists(path) or CRASH_PCT < change_pct < RUN_PCT:
        return 0
    done = os.path.join(HOLDERS, f"{mint}.learned")
    if os.path.exists(done):            # VIGIE already learned it from the rug: AUDIT doesn't count it twice
        return 0
    open(done, "w").close()
    with open(path) as f:
        wallets = json.load(f)
    mem = {}
    if os.path.exists(MEMORY):
        with open(MEMORY) as f:
            mem = json.load(f)
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


def is_toxic(rec: dict) -> bool:
    """Held two tokens that crashed and none that ran: a factory or a rugger's wallet."""
    return rec["crashes"] >= 2 and rec["runs"] == 0


def toxic(wallets: list[str]) -> int:
    mem = memory()
    return sum(1 for w in wallets or [] if w in mem and is_toxic(mem[w]))


def known() -> int:
    return sum(1 for r in memory().values() if is_smart(r))
