# chains.py
# every blockchain the desk trades, in one table. Solana keeps its own deep pipeline (pump.fun graduations,
# PumpSwap pools read on chain, Helius holders, Jupiter, Solana Tracker). the EVM chains share one: tokens
# from DexScreener and GeckoTerminal, the rug checks from GoPlus (honeypot, taxes, mint, pause, blacklist,
# creator, holders, LP lock), prices from DexScreener.
#
# a token is keyed by its Solana mint as before, or "chain:0xaddress" on an EVM chain (the same address
# can exist on several EVM chains). files named after a token use fname().
#
# which chains (Oct 19 2026): DexScreener's paid lists carried Solana, Robinhood Chain (mainnet Jul 1 2026,
# 7 of 30 boosts that evening), BNB Chain and Base; search results added Ethereum. GoPlus covers all of
# them and 40 more EVM chains. costs are per swap, paper estimates: gas, the usual meme pool fee, MEV.
# Ethereum's gas makes a $25 ticket pointless; market.py kills a token whose fixed costs eat the ticket.

CHAINS = {
    # ds: DexScreener chainId · goplus: GoPlus chain id · gt: GeckoTerminal network id
    "solana":    {"goplus": "solana", "gt": "solana",      "tx_usd": 0.50, "fee_pct": 0.3,  "mev_pct": 1.0},
    "robinhood": {"goplus": "4663",   "gt": "robinhood",   "tx_usd": 0.05, "fee_pct": 1.0,  "mev_pct": 0.3},
    "bsc":       {"goplus": "56",     "gt": "bsc",         "tx_usd": 0.10, "fee_pct": 0.25, "mev_pct": 1.0},
    "base":      {"goplus": "8453",   "gt": "base",        "tx_usd": 0.05, "fee_pct": 1.0,  "mev_pct": 0.3},
    "ethereum":  {"goplus": "1",      "gt": "eth",         "tx_usd": 1.50, "fee_pct": 0.3,  "mev_pct": 1.0},
    "arbitrum":  {"goplus": "42161",  "gt": "arbitrum",    "tx_usd": 0.05, "fee_pct": 1.0,  "mev_pct": 0.3},
    "monad":     {"goplus": "143",    "gt": "monad",       "tx_usd": 0.05, "fee_pct": 1.0,  "mev_pct": 0.3},
    "abstract":  {"goplus": "2741",   "gt": "abstract",    "tx_usd": 0.05, "fee_pct": 1.0,  "mev_pct": 0.3},
    "sonic":     {"goplus": "146",    "gt": "sonic",       "tx_usd": 0.05, "fee_pct": 1.0,  "mev_pct": 0.3},
    "avalanche": {"goplus": "43114",  "gt": "avax",        "tx_usd": 0.10, "fee_pct": 0.3,  "mev_pct": 0.5},
    "polygon":   {"goplus": "137",    "gt": "polygon_pos", "tx_usd": 0.05, "fee_pct": 0.3,  "mev_pct": 0.5},
    "optimism":  {"goplus": "10",     "gt": "optimism",    "tx_usd": 0.05, "fee_pct": 1.0,  "mev_pct": 0.3},
    "berachain": {"goplus": "80094",  "gt": "berachain",   "tx_usd": 0.05, "fee_pct": 1.0,  "mev_pct": 0.3},
    "unichain":  {"goplus": "130",    "gt": "unichain",    "tx_usd": 0.05, "fee_pct": 1.0,  "mev_pct": 0.3},
}
GT_TO_CHAIN = {c["gt"]: name for name, c in CHAINS.items()}
# wrapped natives and stables: what a trending list is full of, never a memecoin
NOT_MEMES = {"weth", "wbnb", "wsol", "sol", "eth", "bnb", "usdc", "usdt", "usdc.e", "dai", "wbtc", "cbbtc",
             "usde", "usd1", "fdusd", "wavax", "wmatic", "wpol", "ws", "wbera", "wmon", "usdt0", "weth.e"}


def split(key: str) -> tuple[str, str]:
    """("solana", mint) or ("base", "0xabc...")."""
    if ":" in key:
        chain, addr = key.split(":", 1)
        return chain, addr
    return "solana", key


def key(chain: str, addr: str) -> str:
    return addr if chain == "solana" else f"{chain}:{addr.lower()}"


def is_evm(k: str) -> bool:
    return split(k)[0] != "solana"


def fname(k: str) -> str:
    """A file name for a token: ":" is not welcome in macOS file names."""
    return k.replace(":", "_")


def costs(k: str) -> dict:
    """{tx_usd, fee_pct, mev_pct} for a token's chain."""
    return CHAINS.get(split(k)[0], CHAINS["solana"])


def supported(chain: str) -> bool:
    return chain in CHAINS


def link(k: str) -> str:
    chain, addr = split(k)
    return f"https://dexscreener.com/{chain}/{addr}"
