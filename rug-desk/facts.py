# facts.py
# checks 1-9, without Rugcheck (its domain went dark in October 2026).
# two free sources, both read as facts, never as opinions:
#   - the Solana chain itself (public RPC): authorities, pool LP burn, who owns each holder wallet
#   - GoPlus token security (free, no key): Token-2022 traps and the top 10 holders
import base64, struct, time
import requests
from config import FACTS, SOLANA_RPC
import ruggers, env

GOPLUS = "https://api.gopluslabs.io/api/v1/solana/token_security"
SYSTEM_PROGRAM = "11111111111111111111111111111111"
PUMPSWAP = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

# GoPlus flags that are a hard kill when their status is "1". each one is a way the dev keeps
# control of your tokens after you buy.
TRAPS = {
    "closable": "mint_closable",                    # mint can be closed
    "balance_mutable_authority": "balance_editable",  # permanent delegate: can move or burn your tokens
    "transfer_fee_upgradable": "fee_upgradable",    # can add a sell tax later
    "transfer_hook_upgradable": "hook_upgradable",  # can add code that blocks your sell later
    "default_account_state_upgradable": "freeze_by_default_upgradable",
}


def _b58(b: bytes) -> str:
    n, s = int.from_bytes(b, "big"), ""
    while n:
        n, r = divmod(n, 58)
        s = B58[r] + s
    return "1" * (len(b) - len(b.lstrip(b"\0"))) + s


RPC_URL = env.get("SOLANA_RPC") or SOLANA_RPC   # a private RPC URL in .env (Helius, QuickNode...) wins


def _rpc(method: str, params: list):
    """One RPC call. A 429 (rate limit) is retried twice with a pause: the public endpoint throttles
    hard, and a skipped check costs a token we could have traded."""
    for attempt in range(3):
        r = requests.post(RPC_URL, timeout=20,
                          json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
        throttled = r.status_code == 429 or ('"code":429' in (getattr(r, "text", "") or "").replace(" ", "")[:200])
        if throttled and attempt < 2:
            time.sleep(1.5 * (attempt + 1))
            continue
        r.raise_for_status()
        d = r.json()
        if "error" in d:
            raise RuntimeError(f"solana rpc {method}: {d['error']}")
        return d["result"]


def _goplus(mint: str) -> dict:
    r = requests.get(GOPLUS, params={"contract_addresses": mint}, timeout=30)
    r.raise_for_status()
    d = r.json()
    res = (d.get("result") or {}).get(mint)
    if d.get("code") != 1 or not res:
        raise RuntimeError(f"goplus: {d.get('code')} {d.get('message')}")
    return res


def pool_chain(mint: str, pair: str, dex: str) -> dict:
    """Read the pool account on chain: how much LP is burned, and who created the token.
    PumpSwap only for now: anything else stays None (unverified)."""
    out = {"lp_burned_pct": None, "dev": None}
    if dex != "pumpswap":
        return out
    a = _rpc("getAccountInfo", [pair, {"encoding": "base64"}])["value"]
    if not a or a["owner"] != PUMPSWAP:
        return out
    d = base64.b64decode(a["data"][0])
    if _b58(d[43:75]) != mint:                            # not this token's pool
        return out
    if len(d) >= 243:
        out["dev"] = _b58(d[211:243])                     # coin_creator: the wallet that launched the token
    lp_mint = _b58(d[107:139])
    minted = struct.unpack("<Q", d[203:211])[0]           # LP ever minted, recorded by the pool
    if minted:
        live = int(_rpc("getTokenSupply", [lp_mint])["value"]["amount"])  # LP still in existence
        out["lp_burned_pct"] = round((1 - live / minted) * 100, 2)
    return out


def dev_pct(mint: str, dev: str | None) -> float | None:
    """Check 8: how much of the supply the creator wallet still holds."""
    if not dev:
        return None
    accounts = _rpc("getTokenAccountsByOwner", [dev, {"mint": mint}, {"encoding": "jsonParsed"}])["value"]
    held = sum(int(a["account"]["data"]["parsed"]["info"]["tokenAmount"]["amount"]) for a in accounts)
    supply = int(_rpc("getTokenSupply", [mint])["value"]["amount"])
    return round(held / supply * 100, 3) if supply else None


def _ladder(pcts: list[float]) -> int:
    """Longest run of big holders whose bags are within 2% of each other: one hand, many wallets."""
    big = [p for p in pcts if p >= FACTS["ladder_min_pct"]]
    best = run = 1 if big else 0
    for a, b in zip(big, big[1:]):
        run = run + 1 if abs(a - b) <= 0.02 * max(a, b) else 1
        best = max(best, run)
    return best


def _same_sol(lamports: list[int]) -> int:
    """Biggest group of holder wallets with the exact same SOL balance (10 lamports apart at most)."""
    xs = sorted(lamports)
    best = 1 if xs else 0
    i = 0
    for j in range(len(xs)):
        while xs[j] - xs[i] > 10:
            i += 1
        best = max(best, j - i + 1)
    return best


def report(mint: str, pool: dict) -> dict:
    acc = _rpc("getAccountInfo", [mint, {"encoding": "jsonParsed"}])["value"]
    info = (((acc or {}).get("data") or {}).get("parsed") or {}).get("info") or {}
    if not info:
        raise RuntimeError("mint account not found on chain")
    g = _goplus(mint)
    status = lambda k: str((g.get(k) or {}).get("status", "")) if isinstance(g.get(k), dict) else ""

    holders = g.get("holders") or []
    owners = [h["account"] for h in holders]
    kinds = _rpc("getMultipleAccounts", [owners, {"encoding": "base64",
                 "dataSlice": {"offset": 0, "length": 0}}])["value"] if owners else []
    wallets = []        # pool vaults and lockers are program-owned accounts: they are not whales
    for h, k in zip(holders, kinds):
        if k is None or k["owner"] == SYSTEM_PROGRAM:
            wallets.append({"pct": float(h["percent"]) * 100, "lamports": (k or {}).get("lamports", 0),
                            "address": h["account"]})
    pcts = sorted((w["pct"] for w in wallets), reverse=True)
    # GoPlus lists 10 holders. each slot taken by a pool is filled with the smallest wallet we saw,
    # so the top 10 is never under-counted
    top10 = sum(pcts) + (10 - len(pcts)) * (pcts[-1] if pcts else 0) if pcts else None

    traps = [name for key, name in TRAPS.items() if status(key) == "1"]
    if status("non_transferable") == "1" or g.get("non_transferable") == "1":
        traps.append("non_transferable")
    if g.get("transfer_hook"):
        traps.append("transfer_hook")
    if any(str(v) not in ("0", "", "None") for v in (g.get("transfer_fee") or {}).values()):
        traps.append("transfer_fee")
    if str(g.get("default_account_state")) not in ("1", "None"):
        traps.append("frozen_by_default")

    chain = pool_chain(mint, pool.get("pair"), pool.get("dex"))
    return {
        "mint": mint,
        "symbol": ((g.get("metadata") or {}).get("symbol")) or pool.get("symbol"),
        "mint_authority": info.get("mintAuthority") or (status("mintable") == "1" or None),
        "freeze_authority": info.get("freezeAuthority") or (status("freezable") == "1" or None),
        "danger": traps,
        "dex": pool.get("dex"),
        "lp_burned_pct": chain["lp_burned_pct"],
        "dev": chain["dev"],
        "dev_pct": dev_pct(mint, chain["dev"]) if chain["dev"] else None,
        "top10_pct": round(top10, 2) if top10 is not None else None,
        "max_wallet_pct": round(pcts[0], 2) if pcts else None,
        "same_sol_wallets": _same_sol([w["lamports"] for w in wallets]),
        "ladder_wallets": _ladder(pcts),
        "holders": g.get("holder_count"),
        "wallets": [w["address"] for w in wallets],      # top holder wallets, for the smart-wallet memory
        "not_checked": ["risk_score", "insider_graph"],
    }


def fact_kill(t: dict) -> str | None:
    """Plain comparisons. First failure wins, the reason gets logged."""
    if t.get("dev") and t["dev"] in ruggers.known():             return "dev_rugged_before"
    if t["mint_authority"]:                                      return "mint_open"
    if t["freeze_authority"]:                                    return "freeze_open"
    if t["danger"]:                                              return "danger:" + t["danger"][0]
    if t["lp_burned_pct"] is None:                               return "lp_unverified"
    if t["lp_burned_pct"] < FACTS["min_lp_locked_pct"]:          return "lp_unlocked"
    if t["dev_pct"] is None:                                     return "dev_unknown"
    if t["dev_pct"] > FACTS["max_dev_pct"]:                      return "dev_holds"
    if t["top10_pct"] is None:                                   return "no_holders"
    if t["top10_pct"] > FACTS["max_top10_pct"]:                  return "top10_heavy"
    if t["max_wallet_pct"] > FACTS["max_wallet_pct"]:            return "whale"
    if t["same_sol_wallets"] >= FACTS["bundle_same_sol"]:        return "bundle_same_sol"
    if t["ladder_wallets"] >= FACTS["bundle_ladder"]:            return "bundle_ladder"
    return None
