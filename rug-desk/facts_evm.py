# facts_evm.py
# the contract and holder checks for an EVM token (Robinhood Chain, BNB Chain, Base, Ethereum...), from
# GoPlus's token security API. it returns the same report as facts.report(), so fact_kill(), the score,
# GARDE and the Telegram bot judge every chain with one set of rules.
#
# what maps to what:
#   mint_authority    the owner can mint (is_mintable) or take ownership back
#   freeze_authority  transfers can be paused, wallets blacklisted, or the owner can edit balances
#   danger            honeypot, sell or buy tax over 10%, can't sell everything, hidden owner,
#                     self-destruct, modifiable tax, trading cooldown, closed source
#   lp_burned_pct     share of the LP burned or locked (GoPlus's lp_holders). on v3/v4 pools (positions are
#                     NFTs) the positions held by contracts count too: a plain wallet holding LP can pull it.
#                     no LP data at all: None (soft "lp_unverified")
#   dev, dev_pct      creator address and its share of the supply
#   top10, whale      the top holders, contracts, locked wallets and the pool itself left out
import requests
from config import FACTS
import chains, sources

GOPLUS = "https://api.gopluslabs.io/api/v1/token_security/{}"
BURN = {"0x0000000000000000000000000000000000000000", "0x000000000000000000000000000000000000dead"}
MAX_TAX = 0.10


def _goplus(chain: str, addr: str) -> dict:
    r = requests.get(GOPLUS.format(chains.CHAINS[chain]["goplus"]), params={"contract_addresses": addr}, timeout=12)
    r.raise_for_status()
    d = r.json()
    res = (d.get("result") or {}).get(addr.lower()) or next(iter((d.get("result") or {}).values()), None)
    if d.get("code") != 1 or not res:
        raise RuntimeError(f"goplus {chain}: {d.get('code')} {d.get('message')}")
    return res


def _f(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def report(key: str, pool: dict | None) -> dict:
    chain, addr = chains.split(key)
    try:
        g = _goplus(chain, addr)
        sources.record("goplus", True, f"{chain} ok")
    except Exception as e:
        sources.record("goplus", False, str(e)[:120])
        raise
    on = lambda k: str(g.get(k, "")) == "1"
    danger = [name for k, name in (("is_honeypot", "honeypot"), ("cannot_sell_all", "cannot_sell_all"),
                                   ("cannot_buy", "cannot_buy"), ("hidden_owner", "hidden_owner"),
                                   ("selfdestruct", "selfdestruct"), ("slippage_modifiable", "tax_modifiable"),
                                   ("personal_slippage_modifiable", "tax_per_wallet"),
                                   ("trading_cooldown", "trading_cooldown"),
                                   ("honeypot_with_same_creator", "creator_made_honeypots")) if on(k)]
    if _f(g.get("sell_tax")) > MAX_TAX or _f(g.get("buy_tax")) > MAX_TAX:
        danger.append("high_tax")
    if str(g.get("is_open_source", "1")) == "0":
        danger.append("closed_source")

    # LP: who can pull the liquidity. a v2 pool: the LP token burned or locked. a v3/v4 pool has no LP token,
    # its positions are NFTs: held by a contract (a launchpad's locker, a pool manager) they can't be pulled
    # by a person in one click; held by a plain wallet they can, and that wallet is the classic rug.
    # so on NFT pools the "locked" share is burned + locked + held by contracts. no LP data at all: None
    lp = g.get("lp_holders") or []
    lp_burned = None
    if lp:
        nft = any(h.get("NFT_list") for h in lp)
        lp_burned = round(100 * sum(_f(h.get("percent")) for h in lp
                                    if (h.get("address") or "").lower() in BURN or str(h.get("is_locked")) == "1"
                                    or (nft and str(h.get("is_contract")) == "1")), 2)

    # holders: wallets only. the pools (pair addresses), lockers and other contracts are not whales
    pairs = {(d.get("pair") or "").lower() for d in g.get("dex") or []} | {((pool or {}).get("pair") or "").lower()}
    wallets = [{"address": h.get("address"), "pct": _f(h.get("percent")) * 100}
               for h in g.get("holders") or []
               if str(h.get("is_contract")) != "1" and str(h.get("is_locked")) != "1"
               and (h.get("address") or "").lower() not in pairs | BURN]
    pcts = sorted((w["pct"] for w in wallets), reverse=True)[:10]
    from facts import _ladder
    creator = (g.get("creator_address") or "").lower() or None
    return {
        "mint": key,
        "symbol": g.get("token_symbol") or (pool or {}).get("symbol"),
        "mint_authority": (on("is_mintable") or on("can_take_back_ownership")) or None,
        "freeze_authority": (on("transfer_pausable") or on("is_blacklisted") or on("owner_change_balance")) or None,
        "danger": danger,
        "dex": (pool or {}).get("dex"),
        "lp_burned_pct": lp_burned,
        "dev": creator,
        "dev_pct": round(_f(g.get("creator_percent")) * 100, 3) if g.get("creator_percent") not in (None, "") else None,
        "top10_pct": round(sum(pcts), 2) if pcts else None,
        "max_wallet_pct": round(pcts[0], 2) if pcts else None,
        "same_sol_wallets": 1,              # Solana-only signal (same SOL balance); not read on EVM
        "ladder_wallets": _ladder(pcts),
        "holders": int(_f(g.get("holder_count"))),
        "farm_wallets": 0, "farm_pct": 0.0,
        "holders_source": "goplus" if pcts else None,
        "wallets": [w["address"] for w in wallets],
        "all_owners": [w["address"] for w in wallets],
        "holder_pcts": [(w["address"], w["pct"]) for w in sorted(wallets, key=lambda w: -w["pct"])],
        "not_checked": ["bundles", "funded_cluster", "solana_tracker"],
    }
