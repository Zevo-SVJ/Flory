# watch.py
# every open position, priced in one call. returns the exits it fired, plus the live marks
# so VIGIE can log the balance. prints nothing when nothing changed.
import time
from config import EXIT, PAPER
from market import pools
import book


def watch() -> tuple[list[dict], dict]:
    """Returns (exits, marks). marks = {mint: price} for every position that still has a price."""
    exits, marks = [], {}
    positions = book.load()
    if not positions:
        return exits, marks
    try:
        live = pools(list(positions))
    except Exception as e:
        return [{"kind": "error", "text": f"price feed down ({e}), holding, will retry"}], marks

    for mint, p in positions.items():
        m = live.get(mint)
        if not m or m["price"] <= 0:
            pnl = book.sell(mint, 1.0, 0.0, "pool_gone")
            exits.append({"kind": "sell", "symbol": p["symbol"], "mint": mint, "pnl": pnl, "pct": -100,
                          "reason": "pool_gone", "text": f"{p['symbol']}: pool gone, treated as rugged"})
            continue

        price = m["price"]
        marks[mint] = price
        b = book.load(); s = b[mint]
        s["peak"] = max(s["peak"], price); book.save(b)
        pct = (price / s["entry"] - 1) * 100
        hours = (time.time() - s["opened"]) / 3600

        def out(frac, why):
            pnl = book.sell(mint, frac, price, why)
            verb = "sold" if PAPER else "SELL NOW in your wallet"
            size = "the rest" if frac >= 1 else f"{int(frac * 100)}% of the original size"
            exits.append({"kind": "sell", "symbol": s["symbol"], "mint": mint, "pnl": pnl, "pct": pct,
                          "reason": why, "text": f"{s['symbol']}: {verb} {size} at {pct:+.0f}% ({why}), "
                                                f"pnl ${pnl:+.2f}"})
            if frac >= 1:
                marks.pop(mint, None)

        if m["liq_usd"] < s["liq0"] * (1 - EXIT["liq_drop_pct"] / 100):
            out(1.0, "liquidity_pulled"); continue
        if pct <= EXIT["stop_pct"]:
            out(1.0, "stop"); continue
        ladder = EXIT["ladder"]
        if s["steps"] < len(ladder) and pct >= ladder[s["steps"]][0]:
            level, frac = ladder[s["steps"]]
            out(frac, f"take_profit_{level}")
            b = book.load()
            if mint in b:
                b[mint]["steps"] += 1; book.save(b)
            continue
        if s["steps"] > 0 and price <= s["peak"] * (1 - EXIT["trail_pct"] / 100):
            out(1.0, "trailing_stop"); continue
        if hours >= EXIT["time_stop_hours"] and pct < EXIT["time_stop_min_pct"]:
            out(1.0, "time_stop")
    return exits, marks


if __name__ == "__main__":
    for e in watch()[0]:
        print(e["text"])
