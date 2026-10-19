# book.py
# positions, trades, limits. the desk's memory lives in two files you can open yourself.
import csv, json, os, sys, time
from config import (DATA, POSITIONS, TRADES, TICKET_USD, MAX_OPEN, MAX_ENTRIES_PER_DAY,
                    DAILY_LOSS_HALT_USD, COOLDOWN_HOURS, PAPER_BANKROLL_USD, PAPER_COSTS, PAPER)

COSTS = PAPER        # paper fills pay fees and price impact; live fills are booked at the price you paid


def _cost_pct(usd: float, liq: float | None) -> float:
    """Pool fee + price impact of an order of this size on this pool, in %."""
    impact = 100 * usd / (liq / 2) if liq else 0
    return PAPER_COSTS["fee_pct"] + impact

FIELDS = ["time", "mint", "symbol", "action", "usd", "pnl", "reason"]


def load() -> dict:
    if not os.path.exists(POSITIONS):
        return {}
    with open(POSITIONS) as f:
        return json.load(f)


def save(book: dict):
    os.makedirs(DATA, exist_ok=True)
    tmp = POSITIONS + ".tmp"
    with open(tmp, "w") as f:
        json.dump(book, f, indent=2)
    os.replace(tmp, POSITIONS)        # a crash mid-write never leaves half a book


def trades() -> list[dict]:
    if not os.path.exists(TRADES):
        return []
    with open(TRADES, newline="") as f:
        return list(csv.DictReader(f))


def record(mint, symbol, action, usd, pnl, reason):
    os.makedirs(DATA, exist_ok=True)
    new = not os.path.exists(TRADES)
    with open(TRADES, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({"time": time.strftime("%Y-%m-%d %H:%M"), "mint": mint, "symbol": symbol,
                    "action": action, "usd": round(usd, 2), "pnl": round(pnl, 2), "reason": reason})


def today_pnl() -> float:
    day = time.strftime("%Y-%m-%d")
    return sum(float(t["pnl"]) for t in trades() if t["time"].startswith(day))


def realized() -> float:
    return sum(float(t["pnl"]) for t in trades())


def cash(book: dict | None = None) -> float:
    """Paper cash: starting bankroll + realized pnl - what is still tied up in open positions."""
    book = load() if book is None else book
    tied = sum(p["qty"] * p["entry"] for p in book.values())
    return PAPER_BANKROLL_USD + realized() - tied


def guard(mint: str) -> str | None:
    """Limits run before any network call. A blocked entry costs nothing."""
    day = time.strftime("%Y-%m-%d")
    book = load()
    if today_pnl() <= -DAILY_LOSS_HALT_USD:                      return "halted_daily_loss"
    if mint in book:                                             return "already_open"
    if len(book) >= MAX_OPEN:                                    return "max_open"
    if cash(book) < TICKET_USD:                                  return "no_cash"
    opens = [t for t in trades() if t["action"] == "open" and t["time"].startswith(day)]
    if len(opens) >= MAX_ENTRIES_PER_DAY:                        return "max_entries_today"
    cutoff = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - COOLDOWN_HOURS * 3600))
    if any(t["mint"] == mint and t["action"] == "close" and t["time"] >= cutoff for t in trades()):
        return "cooldown"
    return None


def open_position(mint, symbol, price, liq_usd, usd=TICKET_USD, vaults=None, sol0=None):
    book = load()
    if COSTS:   # the entry is what the tokens really cost: fee and impact on top, the tx fee off the ticket
        price = price * (1 + _cost_pct(usd, liq_usd) / 100)
        qty = (usd - PAPER_COSTS["tx_usd"]) / price
    else:
        qty = usd / price
    book[mint] = {"symbol": symbol, "entry": price, "qty0": qty, "qty": qty,
                  "peak": price, "peak_t": time.time(), "liq0": liq_usd, "opened": time.time(), "steps": 0,
                  "vaults": vaults, "sol0": sol0}     # PumpSwap only: VIGIE reads the pool on chain every tick
    save(book)
    record(mint, symbol, "open", usd, 0, "entry")


def sell(mint, frac_of_original, price, reason, liq_usd=None) -> float:
    """Sells a fraction of the ORIGINAL size (1.0 = everything left). Returns realized pnl."""
    book = load()
    p = book[mint]
    q = min(p["qty"], p["qty0"] * frac_of_original)
    if COSTS and price > 0:
        price = price * (1 - _cost_pct(q * price, liq_usd or p["liq0"]) / 100)
        pnl = q * (price - p["entry"]) - PAPER_COSTS["tx_usd"]
    else:
        pnl = q * (price - p["entry"])
    p["qty"] -= q
    action = "close" if p["qty"] <= p["qty0"] * 1e-6 else "partial"
    record(mint, p["symbol"], action, q * price, pnl, reason)
    if action == "close":
        del book[mint]
    save(book)
    return pnl


if __name__ == "__main__":
    # live mode: after you buy in your own wallet ->  python book.py add <mint> <usd> <price> <liq_usd>
    # after you sell by hand                     ->  python book.py close <mint> <price>
    # see what's open                            ->  python book.py show
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "add":
        mint, usd, price, liq = sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
        open_position(mint, mint[:6], price, liq, usd)
    elif cmd == "close":
        print(round(sell(sys.argv[2], 1.0, float(sys.argv[3]), "manual"), 2))
    else:
        print(json.dumps(load(), indent=2))
