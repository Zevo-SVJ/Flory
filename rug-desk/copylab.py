# copylab.py
# the copy wave, measured. on fomo a followed trader's buy reaches tens of thousands of phones at once
# (bystevenr 93.5K followers, Brez 215K): the followers buy in the next seconds and minutes, the price rises
# on their orders, then fades unless the token has more than that. whoever buys just after the trader and
# sells into the wave sells to the copiers. this file tells whether the desk can be that buyer:
#   - every ~20 s (VIGIE's tick) it reads the newest transactions of each wallet in COPYLAB (Helius, the
#     desk's Solana RPC) and logs every token the wallet bought (its token balance went up)
#   - the token is then priced every 20 s for 2 h like any ghost (paths.py)
#   - python3 copylab.py: for each buy, the move from the first price the desk saw (what it could have
#     bought at) to 1, 5, 15, 30 and 60 min later, net of the costs of a $25 round trip
# nothing is bought: shadow only, in its own file. no rule changes until it pays on enough buys.
import csv, json, math, os, re, statistics, time
from config import DATA, COPYLAB

FILE = os.path.join(DATA, "copylab.csv")
STATE = os.path.join(DATA, "copylab_state.json")
FIELDS = ["t", "seen", "who", "wallet", "mint", "sig", "amount"]
QUOTE = {"So11111111111111111111111111111111111111112", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
         "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"}      # SOL, USDC, USDT: what they pay with
HORIZONS = (1, 5, 15, 30, 60)
# Nov 11: of the first 692 "buys", 23 tokens only: one wallet bought the same token 216 times, another one
# Helius staked SOL. a wave starts on the trader's FIRST buy of a token, and only a memecoin rides one: a
# repeated buy of a token he already bought in the last 6 h is not counted, nor a token that is a dollar, a
# staked or wrapped SOL, a stock, or too big for followers to move (cap over $300M or pool over $10M)
REPEAT_S = 6 * 3600
NOT_WAVE = re.compile(r"usd|staked|stake|wrapped|helius|jito|marinade|msol|jitosol|bsol|xstock|robinhood token|"
                      r"\bsol\b|bitcoin|ether", re.I)
TRAILS = (10, 20)            # %: sold once the price falls this far under its high since the buy (60 min at most)
WATCH_H = 2
_last = {"t": 0.0}


EXTRA = os.path.join(DATA, "copylab_wallets.json")       # wallets added by hand: python3 copylab.py --ajouter


def wallets() -> dict:
    """config COPYLAB's wallets, plus the ones added with --ajouter."""
    out = dict(COPYLAB.get("wallets") or {})
    try:
        with open(EXTRA) as f:
            out.update(json.load(f))
    except (OSError, ValueError):
        pass
    return out


def find(symbol: str, millions: float, usd: float | None = None) -> list[str]:
    """The holders of a Solana token closest to `millions` tokens: how a fomo trader's wallet is found from a
    position his profile shows (bystevenr: 18.42M FLOAT). several tokens share a symbol (CATE): with the
    position's value in $, the one whose price matches it is taken; without, the deepest pool."""
    import requests, facts
    ps = [p for p in requests.get("https://api.dexscreener.com/latest/dex/search", params={"q": symbol},
                                  timeout=15).json().get("pairs") or []
          if p.get("chainId") == "solana" and (p.get("baseToken") or {}).get("symbol", "").upper() == symbol.upper()]
    if not ps:
        return [f"aucun token {symbol} sur Solana"]
    if usd:
        want = usd / (millions * 1e6)
        best = min(ps, key=lambda p: abs(math.log(max(float(p.get("priceUsd") or 1e-18), 1e-18) / want)))
    else:
        best = max(ps, key=lambda p: (p.get("liquidity") or {}).get("usd") or 0)
    mint = best["baseToken"]["address"]
    rows = []
    for a in facts._rpc("getTokenLargestAccounts", [mint])["value"]:
        info = facts._rpc("getAccountInfo", [a["address"], {"encoding": "jsonParsed"}])["value"]
        rows.append((float(a["uiAmountString"]) / 1e6, info["data"]["parsed"]["info"]["owner"]))
    if not any(abs(m - millions) <= 0.02 * millions for m, _ in rows):
        rows += _all_holders(mint)          # below the top 20: every token account of this mint
    rows.sort(key=lambda r: abs(r[0] - millions))
    return [f"{symbol} : {mint} · prix {best.get('priceUsd')} $"] + [f"{m:9.2f} M  ->  {o}" for m, o in rows[:5]]


def _all_holders(mint: str) -> list[tuple[float, str]]:
    """(millions held, owner) for every token account of `mint`, read in one call per token program,
    only the 40 bytes that matter (owner, amount)."""
    import base64, struct, facts
    dec = int(facts._rpc("getTokenSupply", [mint])["value"]["decimals"])
    out = []
    for prog, size in (("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA", 165), ("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb", None)):
        filters = [{"memcmp": {"offset": 0, "bytes": mint}}] + ([{"dataSize": size}] if size else [])
        try:
            accs = facts._rpc("getProgramAccounts", [prog, {"encoding": "base64", "filters": filters,
                                                             "dataSlice": {"offset": 32, "length": 40}}]) or []
        except Exception:
            continue
        for a in accs:
            raw = base64.b64decode(a["account"]["data"][0])
            if len(raw) == 40:
                out.append((struct.unpack("<Q", raw[32:40])[0] / 10 ** dec / 1e6, facts._b58(raw[:32])))
    return out


def _state() -> dict:
    try:
        with open(STATE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def buys_in(tx: dict, wallet: str) -> list[tuple[str, float]]:
    """(mint, amount bought) for every token whose balance held by `wallet` went up in this transaction."""
    meta = (tx or {}).get("meta") or {}
    if meta.get("err"):
        return []
    def held(rows):
        out = {}
        for b in rows or []:
            if b.get("owner") == wallet and b.get("mint") not in QUOTE:
                out[b["mint"]] = out.get(b["mint"], 0.0) + float((b.get("uiTokenAmount") or {}).get("uiAmount") or 0)
        return out
    pre, post = held(meta.get("preTokenBalances")), held(meta.get("postTokenBalances"))
    return [(m, post[m] - pre.get(m, 0.0)) for m in post if post[m] > pre.get(m, 0.0) * 1.0001]


def tick(now: float | None = None) -> int:
    """Read the wallets' newest transactions; log the buys. Returns how many buys were logged."""
    if not COPYLAB.get("on") or not wallets():
        return 0
    now = now or time.time()
    if now - _last["t"] < COPYLAB.get("every_s", 20):
        return 0
    _last["t"] = now
    import facts, paths
    st, n = _state(), 0
    for who, wallet in wallets().items():
        try:
            sigs = facts._rpc("getSignaturesForAddress", [wallet, {"limit": 15}]) or []
        except Exception:
            continue
        seen = st.get(wallet)
        fresh = []
        for s in sigs:
            if s["signature"] == seen:
                break
            fresh.append(s)
        if sigs:
            st[wallet] = sigs[0]["signature"]
        if seen is None:                      # first read: start from now, the past is not a wave we can catch
            continue
        for s in reversed(fresh):
            try:
                tx = facts._rpc("getTransaction", [s["signature"], {"encoding": "jsonParsed",
                                                                    "maxSupportedTransactionVersion": 0}])
            except Exception:
                continue
            for mint, amt in buys_in(tx, wallet):
                lastb = st.setdefault("_last", {})
                k, bt = f"{who}:{mint}", s.get("blockTime") or now
                if bt - lastb.get(k, -1e18) < REPEAT_S:      # a repeat buy: no new wave, not logged
                    lastb[k] = bt
                    continue
                lastb[k] = bt
                new = not os.path.exists(FILE)
                with open(FILE, "a", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=FIELDS)
                    if new:
                        w.writeheader()
                    w.writerow({"t": s.get("blockTime") or round(now), "seen": round(now), "who": who,
                                "wallet": wallet, "mint": mint, "sig": s["signature"], "amount": round(amt, 4)})
                paths.haunt(mint, WATCH_H)
                n += 1
    os.makedirs(DATA, exist_ok=True)
    with open(STATE, "w") as f:
        json.dump(st, f)
    return n


def report() -> list[str]:
    """Per horizon: n, mean and median net %, share of buys that paid, both halves."""
    import paths, chains
    try:
        with open(FILE, newline="") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return ["copylab : aucun achat enregistré pour l'instant"]
    import market
    first, last = [], {}
    for r in sorted(rows, key=lambda r: float(r["t"])):
        k = (r["who"], r["mint"])
        if float(r["t"]) - last.get(k, -1e18) >= REPEAT_S:
            first.append(r)
        last[k] = float(r["t"])
    try:
        info = market.pools(sorted({r["mint"] for r in first}))
    except Exception:
        info = {}
    def wave(m):
        p = info.get(m) or {}
        name = f"{p.get('name') or ''} {p.get('symbol') or ''}"
        return bool(p) and not NOT_WAVE.search(name) and (p.get("mcap") or 0) <= 3e8 and (p.get("liq_usd") or 0) <= 1e7
    kept = [r for r in first if wave(r["mint"])]
    skipped = len(rows) - len(kept)
    rows = kept
    out, res = [f"copylab : {skipped} achat(s) écarté(s) (rachats du même token en moins de 6 h, dollars, SOL staké, "
                 f"tokens trop gros pour une vague) · {len(rows)} premier(s) achat(s) de memecoins gardé(s)"], {h: [] for h in HORIZONS}
    trail = {k: [] for k in TRAILS}
    lags = []
    for r in rows:
        seen = float(r["seen"])
        pts = [p for p in paths.load(r["mint"], since=seen, until=seen + 3700) if p["price"] > 0]
        if len(pts) < 5:
            continue
        p0 = pts[0]
        lags.append(p0["t"] - float(r["t"]))
        c = chains.costs(r["mint"])
        impact = 100 * 25 / ((p0.get("liq") or 1e9) / 2)
        cost = 2 * (c["fee_pct"] + c.get("mev_pct", 0) + impact) + 2 * c["tx_usd"] / 25 * 100
        for h in HORIZONS:
            later = [p for p in pts if p["t"] >= p0["t"] + h * 60]
            if later:
                res[h].append(100 * (later[0]["price"] / p0["price"] - 1) - cost)
        win = [p for p in pts if p["t"] <= p0["t"] + 3600]       # follow the wave: out on the turn
        if len(win) >= 5 and win[-1]["t"] >= p0["t"] + 3000:
            for k in TRAILS:
                peak, sold = p0["price"], win[-1]["price"]
                for p in win[1:]:
                    peak = max(peak, p["price"])
                    if p["price"] <= peak * (1 - k / 100):
                        sold = p["price"]
                        break
                trail[k].append(100 * (sold / p0["price"] - 1) - cost)
    out.append(f"  délai médian entre leur achat et notre premier prix : {statistics.median(lags):.0f} s" if lags
               else "  pas encore de prix pour ces achats")
    for h in HORIZONS:
        xs = res[h]
        if len(xs) < 3:
            out.append(f"  revendu à {h:>2} min : {len(xs)} cas, trop peu")
            continue
        half = len(xs) // 2
        out.append(f"  revendu à {h:>2} min : n {len(xs):>3} · moyenne {statistics.mean(xs):+6.1f} % · médiane "
                   f"{statistics.median(xs):+6.1f} % · gagnants {100 * sum(x > 0 for x in xs) / len(xs):3.0f} % · "
                   f"moitiés {statistics.mean(xs[:half]):+.1f} / {statistics.mean(xs[half:]):+.1f}")
    for k in TRAILS:
        xs = trail[k]
        if len(xs) < 3:
            out.append(f"  vendu à {k} % sous le plus haut : {len(xs)} cas, trop peu")
            continue
        half = len(xs) // 2
        out.append(f"  vendu à {k:>2} % sous le plus haut (1 h max) : n {len(xs):>3} · moyenne {statistics.mean(xs):+6.1f} % · "
                   f"médiane {statistics.median(xs):+6.1f} % · gagnants {100 * sum(x > 0 for x in xs) / len(xs):3.0f} % · "
                   f"moitiés {statistics.mean(xs[:half]):+.1f} / {statistics.mean(xs[half:]):+.1f}")
    return out


if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["--trouver"] and len(sys.argv) in (4, 5):  # python3 copylab.py --trouver CATE 3.4 109267
        print("\n".join(find(sys.argv[2], float(sys.argv[3]), float(sys.argv[4]) if len(sys.argv) == 5 else None)))
    elif sys.argv[1:2] == ["--lot"]:
        # one line per trader on stdin: pseudo SYMBOLE quantité_en_millions valeur_en_dollars
        # added by itself when the closest holder is within 2% and the next one is not
        added = []
        for line in sys.stdin:
            parts = line.replace(",", ".").replace("$", "").split()
            if len(parts) != 4:
                continue
            who, sym, mil, usd = parts[0], parts[1], float(parts[2]), float(parts[3])
            try:
                res = find(sym, mil, usd)
            except Exception as e:
                print(f"{who} : erreur {type(e).__name__} ({str(e)[:80]})")
                continue
            cands = [(float(r.split("M")[0]), r.split("->")[1].strip()) for r in res[1:] if "->" in r]
            if not cands:
                print(f"{who} : {res[0]}")
                continue
            near = [c for c in cands if abs(c[0] - mil) <= 0.02 * mil]
            if len(near) == 1:
                w = {k: v for k, v in wallets().items() if k not in (COPYLAB.get("wallets") or {})}
                w[who] = near[0][1]
                with open(EXTRA, "w") as f:
                    json.dump(w, f, indent=1)
                added.append(who)
                print(f"{who} : ajouté -> {near[0][1]} ({near[0][0]:.2f} M {sym})")
            else:
                print(f"{who} : ambigu ou introuvable, à départager : " +
                      " · ".join(f"{m:.2f} M {a}" for m, a in cands[:3]))
        print(f"suivi : {', '.join(wallets())}")
    elif sys.argv[1:2] == ["--ajouter"] and len(sys.argv) == 4:    # python3 copylab.py --ajouter tjr <adresse>
        import re
        if not re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", sys.argv[3]):
            sys.exit("adresse Solana invalide")
        w = {k: v for k, v in wallets().items() if k not in (COPYLAB.get("wallets") or {})}
        w[sys.argv[2]] = sys.argv[3]
        os.makedirs(DATA, exist_ok=True)
        with open(EXTRA, "w") as f:
            json.dump(w, f, indent=1)
        print(f"suivi : {', '.join(wallets())} (le desk le prend en compte au prochain tick, sans redémarrer)")
    else:
        print("\n".join(report()))
