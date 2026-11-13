# cluster.py
# the Bubblemaps read, done by the desk itself on any RPC: who funded the biggest holders?
# a factory needs SOL in every wallet it buys with, so its wallets are fresh (a few transactions old)
# and their first SOL comes from the same few sources. organic holders are older wallets funded from
# everywhere. Bubblemaps' own rule of thumb: a linked group holding 10%+ of supply is a major red flag.
# exchanges fund thousands of unrelated wallets, so a funder this busy is ignored, never clustered.
# cost: ~2 RPC calls per holder, only for tokens that passed every cheaper check. time-boxed.
import time
from collections import defaultdict
import facts

FRESH_TXS = 100          # fewer transactions than this in the wallet's whole life: its first one is visible
BUSY_FUNDER_TXS = 1000   # a funder with this many transactions is an exchange or a router: not a cluster


def _first_funder(owner: str, sigs: list[dict]) -> str | None:
    """Who sent this wallet its first SOL: the account whose SOL went down the most in its first transaction."""
    tx = facts._rpc("getTransaction", [sigs[-1]["signature"], {"maxSupportedTransactionVersion": 1,
                                                               "encoding": "jsonParsed"}])
    if not tx:
        return None
    keys = [k["pubkey"] if isinstance(k, dict) else k for k in tx["transaction"]["message"]["accountKeys"]]
    pre, post = tx["meta"]["preBalances"], tx["meta"]["postBalances"]
    drops = [(pre[i] - post[i], keys[i]) for i in range(len(keys)) if keys[i] != owner and pre[i] > post[i]]
    return max(drops)[1] if drops else None


def analyze(holders: list[tuple[str, float]], budget_s: float = 25) -> dict:
    """holders: [(wallet, % of supply)], biggest first, pools already removed.
    Returns fresh_pct (supply in wallets with < 100 transactions), cluster_pct (biggest group sharing a
    funder, 3+ wallets), the funders seen, and how many holders were actually read."""
    t0, fresh_pct, by_funder, funders, read = time.time(), 0.0, defaultdict(list), {}, 0
    for wallet, pct in holders:
        if time.time() - t0 > budget_s:
            break
        try:
            sigs = facts._rpc("getSignaturesForAddress", [wallet, {"limit": FRESH_TXS}]) or []
        except Exception:
            continue
        read += 1
        if not sigs or len(sigs) >= FRESH_TXS:
            continue                                  # an old, busy wallet: not a farm wallet
        fresh_pct += pct
        try:
            f = _first_funder(wallet, sigs)
        except Exception:
            f = None
        if f:
            by_funder[f].append((wallet, pct))
            funders[wallet] = f
    best_f, best = None, []
    for f, ws in by_funder.items():
        if len(ws) >= 3 and sum(p for _, p in ws) > sum(p for _, p in best):
            try:                                      # an exchange hot wallet funds everyone: skip it
                busy = len(facts._rpc("getSignaturesForAddress", [f, {"limit": BUSY_FUNDER_TXS}]) or []) >= BUSY_FUNDER_TXS
            except Exception:
                busy = True
            if not busy:
                best_f, best = f, ws
    return {"fresh_pct": round(fresh_pct, 2), "cluster_pct": round(sum(p for _, p in best), 2),
            "cluster_wallets": len(best), "cluster_funder": best_f, "funders": sorted(set(funders.values())),
            "read": read}


def kill(c: dict | None, thresholds: dict, rug_funders: set[str]) -> str | None:
    if not c or not c["read"]:
        return None
    if rug_funders & set(c["funders"]):                       return "rug_funder"
    if c["cluster_pct"] >= thresholds["max_cluster_pct"]:      return "funded_cluster"
    if c["fresh_pct"] >= thresholds["max_fresh_pct"]:          return "fresh_wallets"
    return None
