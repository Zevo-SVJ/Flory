# watch.py
# VIGIE's job: price every open position (and every recently sold one) in one call, record the path,
# and apply the exit rules in exits.py. returns the exits it fired plus the live marks for the balance.
import time
from config import PAPER
from market import pools
import book, exits, paths, facts

_quote_usd = {}             # mint -> last dollar price of its pool's quote token (SOL, or XMR, USDC...)
_mismatch = {}              # mint -> ticks in a row where the chain and DexScreener disagree by half


def chain_marks(positions: dict, live: dict) -> dict:
    """{mint: (price_usd, liq_usd)} read from each PumpSwap pool's vaults, all positions in one RPC call.
    DexScreener lags a pool by seconds to minutes and sometimes drops a pair: a rug factory dumps in
    one block, so the desk reads the pool itself. Empty if the RPC fails (DexScreener still covers).
    each pool is priced in its OWN quote token: a PumpSwap pool is not always against SOL (on Oct 19,
    LUKE's pool was against XMR, and pricing it in SOL read a -84% "rug" that never happened)."""
    for mint, m in live.items():
        if m and m.get("price") and m.get("price_native"):
            _quote_usd[mint] = m["price"] / m["price_native"]      # priceNative is in the pair's quote token
    held = {mint: p["vaults"] for mint, p in positions.items() if p.get("vaults") and _quote_usd.get(mint)}
    if not held:
        return {}
    try:
        flat = facts.reserves([v for vs in held.values() for v in vs])
    except Exception:
        return {}
    out = {}
    for i, mint in enumerate(held):
        tokens, quote = flat[2 * i], flat[2 * i + 1]
        q = _quote_usd[mint]
        if tokens and quote is not None:
            out[mint] = (quote / tokens * q, 2 * quote * q)
    return out


def watch() -> tuple[list[dict], dict]:
    """Returns (exits, marks). marks = {mint: price} for every open position that has a price."""
    out, marks = [], {}
    positions = book.load()
    ghosts = paths.ghosts()
    if not positions and not ghosts:
        return out, marks
    backup = False
    try:
        live = pools(list(positions) + [g for g in ghosts if g not in positions])
    except Exception as e:
        backup = True
        # DexScreener down used to leave every position unpriced, so no stop could fire until it came back
        # (Oct 27 evening). the positions are now priced from the pool itself (Solana, last known quote
        # price) and from GeckoTerminal for the rest, and the exits keep running
        live = backup_marks(positions)
        out.append({"kind": "error", "text": f"price feed down ({str(e)[:120]}), {len(live)}/{len(positions)} "
                                             f"position(s) priced from the backup sources"})

    now = time.time()
    for mint in ghosts:                       # sold tokens: only recorded, for the exit lab
        m = live.get(mint)
        if backup and not m:                  # no price is not a price of zero: nothing is recorded
            continue
        if mint not in positions:
            paths.append(mint, sample(now, m))

    profile = exits.active()
    onchain = chain_marks(positions, live)
    # prices were fetched above without the lock; decisions and sales hold it, so a buy or an ECHO sale
    # from the main thread can't be overwritten by this tick
    with book.LOCK:
        for mint, p in positions.items():
            m = live.get(mint)
            if backup and not m and mint not in onchain:
                continue                          # unpriced while the feed is down: held, never sold at "zero"
            s = sample(now, m)
            if mint in onchain:                   # the pool itself beats any indexer...
                cp, cl = onchain[mint]
                dsp = (m or {}).get("price") or 0
                if dsp and abs(cp / dsp - 1) > 0.5:
                    # ...unless it disagrees with DexScreener by half: a real dump stays dumped 20 s later,
                    # a misread does not. the chain wins only when two ticks in a row agree
                    _mismatch[mint] = _mismatch.get(mint, 0) + 1
                    if _mismatch[mint] >= 2:
                        s["price"], s["liq"] = cp, cl
                else:
                    _mismatch.pop(mint, None)
                    s["price"], s["liq"] = cp, cl
            paths.append(mint, s)
            if s["price"] > 0:
                marks[mint] = s["price"]
                b = book.load()
                if mint not in b:             # GARDE's thread (an ECHO SKIP) closed it meanwhile
                    continue
                pos = b[mint]
                if s["price"] > pos["peak"]:
                    pos["peak"], pos["peak_t"] = s["price"], now
                    book.save(b)
            else:
                pos = p
            hist = paths.load(mint, since=max(pos["opened"], now - 3600))
            d = exits.decide(pos, exits.features(hist)[-1] if hist else s, exits.for_mint(mint, profile))
            if not d:
                continue
            frac, why = d
            pct = (s["price"] / pos["entry"] - 1) * 100 if s["price"] > 0 else -100
            held = pos["qty"] / pos["qty0"] if pos.get("qty0") else 1.0
            share = min(1.0, frac / held) if held > 0 else 1.0     # of what is still held: what a copier sells
            pnl = book.sell(mint, frac, s["price"], why, s.get("liq"))
            closed = mint not in book.load()
            if closed:
                marks.pop(mint, None)
                paths.haunt(mint)
            elif why.startswith("take_profit"):
                b = book.load()
                b[mint]["steps"] += 1
                book.save(b)
            import dossier
            dossier.add(mint, "VIGIE", "vente", reason=why, pct=round(pct, 1), pnl=round(pnl, 2), closed=closed)
            verb = "sold" if PAPER else "SELL NOW in your wallet"
            size = "the rest" if closed else f"{int(frac * 100)}% of the original size"
            out.append({"kind": "sell", "symbol": pos["symbol"], "mint": mint, "pnl": pnl, "pct": pct,
                        "reason": why, "closed": closed, "share": 1.0 if closed else share,
                        "text": f"{pos['symbol']}: {verb} {size} at {pct:+.0f}% ({why}), pnl ${pnl:+.2f}"})
    return out, marks


_gt_seen: dict[str, tuple[float, float]] = {}     # key -> (time, price): GeckoTerminal is read once a minute
GT_EVERY_S = 60


def backup_marks(positions: dict) -> dict:
    """{mint: market-like dict} when DexScreener is down: the pool's own reserves where the desk knows the
    vaults (Solana), else GeckoTerminal's token price (no liquidity: the liquidity exit waits for it)."""
    import chains, gt
    out = {}
    for mint, (price, liq) in chain_marks(positions, {}).items():
        out[mint] = {"price": price, "liq_usd": liq}
    now = time.time()
    rest = {}
    for mint in positions:
        if mint in out:
            continue
        seen = _gt_seen.get(mint)
        if seen and now - seen[0] < GT_EVERY_S:
            out[mint] = {"price": seen[1], "liq_usd": None}
            continue
        chain, addr = chains.split(mint)
        if chains.supported(chain):
            rest.setdefault(chain, []).append((mint, addr))
    for chain, items in rest.items():
        net = chains.CHAINS[chain]["gt"]
        try:
            r = gt.get(f"https://api.geckoterminal.com/api/v2/simple/networks/{net}/token_price/"
                       + ",".join(a for _, a in items), wait_max=5)
            r.raise_for_status()
            px = ((r.json().get("data") or {}).get("attributes") or {}).get("token_prices") or {}
        except Exception:
            continue
        low = {k.lower(): v for k, v in px.items()}
        for mint, addr in items:
            v = low.get(addr.lower())
            try:
                p = float(v)
            except (TypeError, ValueError):
                continue
            if p > 0:
                _gt_seen[mint] = (now, p)
                out[mint] = {"price": p, "liq_usd": None}
    return out


def sample(t: float, m: dict | None) -> dict:
    if not m:
        return {"t": t, "price": 0.0, "liq": None, "b5": None, "s5": None, "v5": None}
    return {"t": t, "price": m["price"], "liq": m["liq_usd"], "b5": m.get("buys_5m"),
            "s5": m.get("sells_5m"), "v5": m.get("vol_5m")}


if __name__ == "__main__":
    for e in watch()[0]:
        print(e["text"])
