# journal.py
# Skide's own memecoin trades, by hand, next to the desk's: one line per buy and per sale, so that his
# results can be judged the same way as the desk's (mean per trade, without the best ones, both halves).
#   python3 journal.py achat <CA> <dollars mis>            a buy (the price now is read from DexScreener)
#   python3 journal.py vente <CA> <dollars reçus>          a sale, whole or part (what the wallet received)
#   python3 journal.py bilan                               every trade, the totals, and the desk beside them
#   python3 journal.py wallet <adresse Solana>             once: the desk then reads his buys and sales on chain
#                                                          by itself, every ~20 s, with their dollar amounts
# nothing here trades: it only records what was done in his own wallet.
import csv, os, statistics, sys, time
from config import DATA

FILE = os.path.join(DATA, "manual_trades.csv")
FIELDS = ["time", "mint", "symbol", "side", "usd", "price"]


def _rows() -> list[dict]:
    try:
        with open(FILE, newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def _key(ca: str) -> str:
    """A pasted CA as the desk's key: a Solana mint as is, a 0x address on the chain of its deepest pool."""
    import market
    return market.locate(ca.strip()) or ca.strip()


def _market(key: str) -> dict:
    try:
        import market
        return market.pool(key) or {}
    except Exception:
        return {}


def record(side: str, ca: str, usd: float, now: float | None = None) -> str:
    key = _key(ca)
    m = _market(key)
    os.makedirs(DATA, exist_ok=True)
    new = not os.path.exists(FILE)
    with open(FILE, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({"time": time.strftime("%Y-%m-%d %H:%M", time.localtime(now or time.time())), "mint": key,
                    "symbol": m.get("symbol") or key[:8], "side": side, "usd": round(usd, 2),
                    "price": m.get("price") or ""})
    return f"noté : {side} ${m.get('symbol') or key[:8]} · {usd:.2f} $" + (f" · prix {m['price']:.6g}" if m.get("price") else "")


WALLET = os.path.join(DATA, "journal_wallet.txt")
STATE = os.path.join(DATA, "journal_state.json")
WSOL, USDC = "So11111111111111111111111111111111111111112", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
STABLE = {USDC, "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"}
_last = {"t": 0.0}


def wallet() -> str | None:
    try:
        with open(WALLET) as f:
            return f.read().strip() or None
    except OSError:
        return None


def parse(tx: dict, me: str, sol_usd: float) -> list[tuple[str, str, float]]:
    """(achat|vente, mint, dollars) for one swap of the wallet `me`: tokens in or out, paid or received in
    SOL, wrapped SOL or a dollar stablecoin. a transfer with no money the other way is not a trade."""
    meta = (tx or {}).get("meta") or {}
    if meta.get("err"):
        return []
    keys = [k.get("pubkey") if isinstance(k, dict) else k for k in
            (((tx.get("transaction") or {}).get("message") or {}).get("accountKeys") or [])]
    sol = 0.0
    if me in keys:
        i = keys.index(me)
        sol = (meta["postBalances"][i] - meta["preBalances"][i]) / 1e9
    def held(rows):
        out = {}
        for b in rows or []:
            if b.get("owner") == me:
                out[b["mint"]] = out.get(b["mint"], 0.0) + float((b.get("uiTokenAmount") or {}).get("uiAmount") or 0)
        return out
    pre, post = held(meta.get("preTokenBalances")), held(meta.get("postTokenBalances"))
    delta = {m: post.get(m, 0.0) - pre.get(m, 0.0) for m in set(pre) | set(post)}
    money = (sol + delta.pop(WSOL, 0.0)) * sol_usd + sum(delta.pop(m, 0.0) for m in list(delta) if m in STABLE)
    moved = {m: d for m, d in delta.items() if abs(d) > 1e-9}
    if not moved or abs(money) < 0.5:
        return []
    side = "achat" if money < 0 else "vente"
    return [(side, m, abs(money) / len(moved)) for m, d in moved.items() if (d > 0) == (side == "achat")]


def tick(now: float | None = None) -> int:
    """Read the journal wallet's new transactions; record its trades. Returns how many were recorded."""
    import json
    me = wallet()
    now = now or time.time()
    if not me or now - _last["t"] < 20:
        return 0
    _last["t"] = now
    import facts
    try:
        with open(STATE) as f:
            seen = json.load(f).get("sig")
    except (OSError, ValueError):
        seen = None
    sigs = facts._rpc("getSignaturesForAddress", [me, {"limit": 20}]) or []
    fresh = []
    for s in sigs:
        if s["signature"] == seen:
            break
        fresh.append(s)
    n = 0
    if sigs:
        with open(STATE, "w") as f:
            json.dump({"sig": sigs[0]["signature"]}, f)
    if seen is None or not fresh:                # first read: the journal starts now
        return 0
    import backtest
    sol_usd = backtest.sol_price()
    for s in reversed(fresh):
        try:
            tx = facts._rpc("getTransaction", [s["signature"], {"encoding": "jsonParsed",
                                                                "maxSupportedTransactionVersion": 0}])
        except Exception:
            continue
        for side, mint, usd in parse(tx, me, sol_usd):
            record(side, mint, usd, s.get("blockTime"))
            n += 1
    return n


def trades() -> list[dict]:
    """Per token, in the order of the first buy: dollars in, dollars out, closed or still held."""
    out = {}
    for r in _rows():
        t = out.setdefault(r["mint"], {"mint": r["mint"], "symbol": r["symbol"], "opened": r["time"],
                                      "in": 0.0, "out": 0.0, "closed": None})
        if r["side"] == "achat":
            t["in"] += float(r["usd"])
        else:
            t["out"] += float(r["usd"])
            t["closed"] = r["time"]
    return list(out.values())


def bilan() -> list[str]:
    ts = trades()
    if not ts:
        return ["journal vide : python3 journal.py achat <CA> <dollars>"]
    lines = []
    done = [t for t in ts if t["out"] > 0]
    for t in ts:
        state = f"reçu {t['out']:.2f} $ · {100 * (t['out'] / t['in'] - 1):+.1f} %" if t["out"] > 0 else "encore détenu"
        lines.append(f"{t['opened']} · ${t['symbol']:<12} · misé {t['in']:.2f} $ · {state}")
    if done:
        xs = [100 * (t["out"] / t["in"] - 1) for t in done if t["in"] > 0]
        pnl = sum(t["out"] - t["in"] for t in done)
        h = len(xs) // 2
        lines.append(f"\nTOI : {len(xs)} trades vendus · gain total {pnl:+.2f} $ · moyenne {statistics.mean(xs):+.1f} % · "
                     f"gagnants {100 * sum(x > 0 for x in xs) / len(xs):.0f} %"
                     + (f" · sans les 3 meilleurs {statistics.mean(sorted(xs)[:-3]):+.1f} %" if len(xs) > 3 else "")
                     + (f" · moitiés {statistics.mean(xs[:h]):+.1f} / {statistics.mean(xs[h:]):+.1f}" if h else ""))
        try:
            import edge
            d = [100 * t["pnl"] / t["usd"] for t in edge.closed() if t["usd"]]
            if d:
                lines.append(f"DESK : {len(d)} trades · moyenne {statistics.mean(d):+.1f} % · gagnants "
                             f"{100 * sum(x > 0 for x in d) / len(d):.0f} % (papier, mêmes calculs)")
        except Exception:
            pass
    return lines


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == "wallet":
        import re
        if not re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", a[1]):
            sys.exit("adresse Solana invalide")
        os.makedirs(DATA, exist_ok=True)
        with open(WALLET, "w") as f:
            f.write(a[1])
        print("c'est noté : tes achats et ventes sur ce wallet seront enregistrés tout seuls à partir de maintenant "
              "(python3 journal.py bilan pour les voir)")
    elif len(a) == 3 and a[0] in ("achat", "vente"):
        try:
            usd = float(a[2].replace(",", ".").replace("$", ""))
        except ValueError:
            sys.exit("montant invalide : un nombre de dollars, par exemple 25 ou 37.5")
        print(record(a[0], a[1], usd))
    else:
        print("\n".join(bilan()))
