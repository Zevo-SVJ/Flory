# watch.py
# VIGIE's job: price every open position (and every recently sold one) in one call, record the path,
# and apply the exit rules in exits.py. returns the exits it fired plus the live marks for the balance.
import time
from config import PAPER
from market import pools
import book, exits, paths


def watch() -> tuple[list[dict], dict]:
    """Returns (exits, marks). marks = {mint: price} for every open position that has a price."""
    out, marks = [], {}
    positions = book.load()
    ghosts = paths.ghosts()
    if not positions and not ghosts:
        return out, marks
    try:
        live = pools(list(positions) + [g for g in ghosts if g not in positions])
    except Exception as e:
        return [{"kind": "error", "text": f"price feed down ({e}), holding, will retry"}], marks

    now = time.time()
    for mint in ghosts:                       # sold tokens: only recorded, for the exit lab
        m = live.get(mint)
        if mint not in positions:
            paths.append(mint, sample(now, m))

    profile = exits.active()
    for mint, p in positions.items():
        m = live.get(mint)
        s = sample(now, m)
        paths.append(mint, s)
        if s["price"] > 0:
            marks[mint] = s["price"]
            b = book.load(); pos = b[mint]
            if s["price"] > pos["peak"]:
                pos["peak"], pos["peak_t"] = s["price"], now
                book.save(b)
        else:
            pos = p
        hist = paths.load(mint, since=max(pos["opened"], now - 3600))
        d = exits.decide(pos, exits.features(hist)[-1] if hist else s, profile)
        if not d:
            continue
        frac, why = d
        pct = (s["price"] / pos["entry"] - 1) * 100 if s["price"] > 0 else -100
        pnl = book.sell(mint, frac, s["price"], why)
        closed = mint not in book.load()
        if closed:
            marks.pop(mint, None)
            paths.haunt(mint)
        elif why.startswith("take_profit"):
            b = book.load()
            b[mint]["steps"] += 1
            book.save(b)
        verb = "sold" if PAPER else "SELL NOW in your wallet"
        size = "the rest" if closed else f"{int(frac * 100)}% of the original size"
        out.append({"kind": "sell", "symbol": pos["symbol"], "mint": mint, "pnl": pnl, "pct": pct,
                    "reason": why, "closed": closed,
                    "text": f"{pos['symbol']}: {verb} {size} at {pct:+.0f}% ({why}), pnl ${pnl:+.2f}"})
    return out, marks


def sample(t: float, m: dict | None) -> dict:
    if not m:
        return {"t": t, "price": 0.0, "liq": None, "b5": None, "s5": None, "v5": None}
    return {"t": t, "price": m["price"], "liq": m["liq_usd"], "b5": m.get("buys_5m"),
            "s5": m.get("sells_5m"), "v5": m.get("vol_5m")}


if __name__ == "__main__":
    for e in watch()[0]:
        print(e["text"])
