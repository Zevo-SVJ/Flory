# live.py
# REAL MONEY, one chain, small and capped. the paper desk keeps deciding everything: every paper buy and
# sale on a LIVE chain (config.py) is copied here into a dedicated wallet, through KyberSwap's aggregator.
#
#   LIVE=off|dry|on in .env     off: nothing. dry: every order is quoted on the real chain, nothing is sent,
#                               the would-be fills are logged. on: real transactions
#   LIVE_KEY in .env            the wallet's key, written there by `python3 live.py new-wallet`, never shown
#
# what can never happen, whatever a bug or an X post makes the desk believe (Grok/Bankrbot lost $150-200k
# on May 4 2026 to a prompt hidden in an X reply): the only transactions this file signs are a swap sent to
# KyberSwap's router and an approval of that same router, for the exact amount sold. no transfer to any
# address exists here. orders come from book.py only, as (token, buy or sell, share), never as text.
#
#   python3 live.py new-wallet     makes the wallet, writes its key into .env, prints its address only
#   python3 live.py test           every outside service answers? (RPC, BNB price, KyberSwap, honeypot.is)
#   python3 live.py status         wallet, positions, real vs paper on the same trades
#   python3 live.py sellall        sells every real position (the running desk does it within 30 s)
#   python3 live.py reset-start    the -30% stop counts from the wallet's value now (after a top-up)
#   touch data/STOP                no more real buys; sells go on. rm data/STOP to resume
import csv, json, os, queue, re, sys, threading, time
import requests
import atomic, env
from config import DATA, HERE, LIVE

ROUTER = "0x6131b5fae19ea4f9d964eac0408e4408b66337b5"   # KyberSwap MetaAggregationRouterV2: the only contract paid
NATIVE = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"   # KyberSwap's name for BNB itself
KYBER = "https://aggregator-api.kyberswap.com/bsc/api/v1"
CLIENT = "rug-desk"
RPC = "https://bsc-dataseed.bnbchain.org"               # reads (LIVE_RPC in .env to change it)
SEND_RPC = "https://bscrpc.pancakeswap.finance"         # PancakeSwap MEV Guard: no sandwich (LIVE_SEND_RPC)
CHAIN_ID = 56
HONEYPOT = "https://api.honeypot.is/v2/IsHoneypot"
CAKE = "0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82"     # a deep BSC token, for `live.py test` only
LOG = os.path.join(DATA, "live_trades.csv")
STATUS = os.path.join(DATA, "live_status.json")
STOP = os.path.join(DATA, "STOP")
SELLALL = os.path.join(DATA, "LIVE_SELLALL")
ADDR = re.compile(r"^0x[0-9a-f]{40}$")
APPROVE = "0x095ea7b3"
RUG = ("liquidity_pulled", "pool_gone", "x_scam", "contagion")
FIELDS = ["time", "mode", "side", "mint", "symbol", "usd", "tokens", "price", "paper_price", "gap_pct",
          "gas_usd", "reason", "tx", "status"]
_LOCK = threading.RLock()
_q: "queue.Queue[dict]" = queue.Queue()
_worker = {"th": None}
_said: dict[str, float] = {}
_px = {"t": 0.0, "v": None}
_dec: dict[str, int] = {}


def mode() -> str:
    if os.environ.get("RUG_DESK_DATA"):     # the tests, or a desk on other data: never real money
        return "off"
    m = (env.get("LIVE") or "off").strip().lower()
    return m if m in ("dry", "on") else "off"


def tag(m: str | None = None) -> str:
    return "RÉEL" if (m or mode()) == "on" else "SIMULÉ"


# ---------- state: one file per mode, so a dry run never mixes with real positions ----------

def _path(m: str | None = None) -> str:
    return os.path.join(DATA, f"live_{m or mode()}.json")


def load(m: str | None = None) -> dict:
    s = {"positions": {}, "closed": [], "buys": [], "start_usd": None, "stopped": False}
    try:
        with open(_path(m)) as f:
            s.update(json.load(f))
    except (OSError, ValueError):
        pass
    return s


def save(s: dict, m: str | None = None):
    os.makedirs(DATA, exist_ok=True)
    p = _path(m)
    tmp = atomic.tmp(p)
    with open(tmp, "w") as f:
        json.dump(s, f, indent=1)
    os.replace(tmp, p)


def log(**row):
    os.makedirs(DATA, exist_ok=True)
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({"time": time.strftime("%Y-%m-%d %H:%M"), "mode": mode(), **{k: row.get(k, "") for k in FIELDS
                                                                               if k not in ("time", "mode")}})


def say(text: str, key: str | None = None, every: int = 3600, agent: str = "VIGIE", kind: str = "info"):
    """Page and Telegram. a repeated problem (same key) is said once an hour, not every 30 s."""
    if key and time.time() - _said.get(key, 0) < every:
        return
    if key:
        _said[key] = time.time()
    from events import emit
    from notify import post
    emit(agent, kind, text)
    post(text)


# ---------- the chain ----------

def rpc(method: str, params: list, url: str | None = None):
    r = requests.post(url or env.get("LIVE_RPC") or RPC, json={"jsonrpc": "2.0", "id": 1, "method": method,
                                                               "params": params}, timeout=20)
    r.raise_for_status()
    j = r.json()
    if j.get("error"):
        e = j["error"]
        raise RuntimeError(f"{method}: {e.get('message', e) if isinstance(e, dict) else e}")
    return j.get("result")


def _int(h) -> int:
    return int(h, 16) if isinstance(h, str) and h not in ("", "0x") else 0


def _word(x) -> str:
    """One 32-byte ABI word: an address or an amount."""
    if isinstance(x, str):
        return x.lower().replace("0x", "").rjust(64, "0")
    return format(int(x), "x").rjust(64, "0")


def call(to: str, data: str) -> str:
    return rpc("eth_call", [{"to": to, "data": data}, "latest"])


def balance_of(token: str, owner: str) -> int:
    return _int(call(token, "0x70a08231" + _word(owner)))


def allowance(token: str, owner: str, spender: str) -> int:
    return _int(call(token, "0xdd62ed3e" + _word(owner) + _word(spender)))


def decimals(token: str) -> int:
    if token not in _dec:
        _dec[token] = _int(call(token, "0x313ce567")) or 18
    return _dec[token]


def bnb_balance(addr: str) -> int:
    return _int(rpc("eth_getBalance", [addr, "latest"]))


def bnb_usd() -> float:
    if _px["v"] and time.time() - _px["t"] < 60:
        return _px["v"]
    for url, keys in (("https://api.binance.com/api/v3/ticker/price?symbol=BNBUSDT", ("price",)),
                      ("https://api.coinbase.com/v2/prices/BNB-USD/spot", ("data", "amount"))):
        try:
            v = requests.get(url, timeout=10).json()
            for k in keys:
                v = v[k]
            v = float(v)
            if v > 0:
                _px.update(t=time.time(), v=v)
                return v
        except Exception:
            continue
    raise RuntimeError("prix du BNB indisponible (Binance et Coinbase)")


def account():
    key = env.get("LIVE_KEY")
    if not key:
        raise RuntimeError("LIVE_KEY absent de .env : lance `python3 live.py new-wallet`")
    from eth_account import Account
    return Account.from_key(key)


# ---------- KyberSwap and honeypot.is ----------

def route(token_in: str, token_out: str, amount: int) -> dict:
    r = requests.get(f"{KYBER}/routes", params={"tokenIn": token_in, "tokenOut": token_out, "amountIn": str(amount)},
                     headers={"x-client-id": CLIENT}, timeout=20)
    j = r.json()
    d = j.get("data") or {}
    if not d.get("routeSummary"):
        raise RuntimeError(f"KyberSwap : pas de route ({j.get('message') or r.status_code})")
    if (d.get("routerAddress") or "").lower() != ROUTER:
        raise RuntimeError(f"KyberSwap : routeur inattendu {d.get('routerAddress')}, refusé")
    return d["routeSummary"]


def build(summary: dict, me: str, slippage_bps: int) -> dict:
    r = requests.post(f"{KYBER}/route/build", json={
        "routeSummary": summary, "sender": me, "recipient": me, "slippageTolerance": int(min(slippage_bps, 2000)),
        "deadline": int(time.time()) + 300, "source": CLIENT}, headers={"x-client-id": CLIENT}, timeout=20)
    j = r.json()
    d = j.get("data") or {}
    if not d.get("data"):
        raise RuntimeError(f"KyberSwap build : {j.get('message') or r.status_code}")
    if (d.get("routerAddress") or "").lower() != ROUTER:
        raise RuntimeError(f"KyberSwap build : routeur inattendu {d.get('routerAddress')}, refusé")
    return d


def honeypot(token: str) -> str | None:
    """A real buy-then-sell simulation on the token. None = can be sold. fails closed: no answer, no buy."""
    try:
        j = requests.get(HONEYPOT, params={"address": token, "chainID": CHAIN_ID}, timeout=20).json()
    except Exception as e:
        return f"honeypot.is injoignable ({type(e).__name__})"
    if (j.get("honeypotResult") or {}).get("isHoneypot"):
        return "honeypot : la revente échoue en simulation"
    if j.get("simulationSuccess") is False:
        return "simulation achat-revente impossible"
    tax = float((j.get("simulationResult") or {}).get("sellTax") or 0)
    if tax > LIVE["max_sell_tax_pct"]:
        return f"taxe à la revente {tax:.0f} %"
    return None


# ---------- signing: two kinds of transaction, nothing else ----------

def check_tx(to: str, value: int, data: str, cap_wei: int):
    """The wall. a swap to the router, at most cap_wei of BNB; or an approval of the router, no BNB."""
    to = to.lower()
    if to == ROUTER:
        if value > cap_wei:
            raise RuntimeError(f"transaction refusée : {value / 1e18:.4f} BNB dépasse le plafond")
        return
    if value == 0 and data.lower().startswith(APPROVE) and data[10:74].lower() == _word(ROUTER):
        return
    raise RuntimeError("transaction refusée : seul le routeur KyberSwap peut recevoir des fonds ou une approbation")


def send(acct, to: str, value: int, data: str, cap_wei: int) -> tuple[str, bool, int]:
    """Signs and sends one checked transaction, waits for its receipt. (hash, succeeded, fee in wei)."""
    check_tx(to, value, data, cap_wei)
    from eth_account import Account
    from eth_utils import to_checksum_address
    me = acct.address
    nonce = _int(rpc("eth_getTransactionCount", [me, "pending"]))
    gas_price = _int(rpc("eth_gasPrice", []))
    tx = {"from": me, "to": to_checksum_address(to), "value": hex(value), "data": data}
    gas = int(_int(rpc("eth_estimateGas", [tx])) * 1.3) + 10_000     # a revert shows here, before any signature
    signed = Account.sign_transaction({"nonce": nonce, "gasPrice": gas_price, "gas": gas, "to": tx["to"],
                                       "value": value, "data": data, "chainId": CHAIN_ID}, acct.key)
    raw = signed.raw_transaction.hex()
    raw = raw if raw.startswith("0x") else "0x" + raw
    h = signed.hash.hex()
    h = h if h.startswith("0x") else "0x" + h
    try:
        rpc("eth_sendRawTransaction", [raw], url=env.get("LIVE_SEND_RPC") or SEND_RPC)
    except Exception:
        try:                                   # the private relay down: the public mempool, the slippage cap holds
            rpc("eth_sendRawTransaction", [raw])
        except Exception as e:
            if "known" not in str(e).lower():
                raise
    for _ in range(60):
        time.sleep(2)
        rc = rpc("eth_getTransactionReceipt", [h])
        if rc:
            fee = _int(rc.get("gasUsed")) * (_int(rc.get("effectiveGasPrice")) or gas_price)
            return h, rc.get("status") == "0x1", fee
    raise RuntimeError(f"transaction {h[:12]}… sans reçu après 2 min")


# ---------- orders from book.py ----------

def submit(order: dict):
    """book.py calls this on every paper open and sale. never blocks, never raises."""
    if mode() == "off":
        return
    import chains
    chain, addr = chains.split(order.get("mint", ""))
    if chain not in LIVE["chains"] or not ADDR.match(addr.lower()):
        return
    _q.put({**order, "t": time.time()})
    start()


def start():
    if mode() == "off" or (_worker["th"] and _worker["th"].is_alive()):
        return
    th = threading.Thread(target=_loop, name="LIVE", daemon=True)
    th.start()
    _worker["th"] = th


def _loop():
    last = 0.0
    while True:
        try:
            o = _q.get(timeout=30)
        except queue.Empty:
            o = None
        try:
            if o:
                handle(o)
            if os.path.exists(SELLALL):
                os.remove(SELLALL)
                for mint in list(load()["positions"]):
                    sell(mint, 1.0, "sellall")
            if time.time() - last > 300:
                last = time.time()
                tick()
        except Exception as e:
            say(f"ALERTE · {tag()} : {type(e).__name__}: {str(e)[:200]}", key="loop:" + str(e)[:60], kind="error")


def handle(o: dict):
    with _LOCK:
        if o.get("side") == "buy":
            buy(o)
        elif o.get("side") == "sell":
            sell(o["mint"], float(o.get("share") or 1.0), o.get("reason") or "?")


def refuse_buy(s: dict, mint: str) -> str | None:
    now = time.time()
    if os.path.exists(STOP):                                         return "fichier data/STOP présent"
    if s["stopped"]:                                                 return f"arrêt à {LIVE['stop_pct']} % atteint"
    if mint in s["positions"]:                                       return "déjà en portefeuille"
    if len(s["positions"]) >= LIVE["max_open"]:                      return f"{LIVE['max_open']} positions déjà ouvertes"
    if sum(t > now - 86400 for t in s["buys"]) >= LIVE["max_buys_day"]:
        return f"{LIVE['max_buys_day']} achats en 24 h"
    if any(c["mint"] == mint and c["closed"] > now - 86400 for c in s["closed"]):
        return "déjà tradé il y a moins de 24 h"
    if LIVE["ticket_usd"] > LIVE["max_tx_usd"]:                      return "ticket au-dessus du plafond"
    return None


def buy(o: dict):
    import chains
    m, mint, sym = mode(), o["mint"], o.get("symbol") or "?"
    token = chains.split(mint)[1].lower()
    s = load()
    why = refuse_buy(s, mint) or honeypot(token)
    px = bnb_usd() if not why else 0
    usd = LIVE["ticket_usd"]
    wei = int(usd / px * 1e18) if px else 0
    acct = me = None
    if not why and m == "on":
        acct = account()
        me = acct.address.lower()
        bal = bnb_balance(me)
        if bal < wei + int(LIVE["gas_reserve_usd"] / px * 1e18):
            why = f"pas assez de BNB ({bal / 1e18 * px:.2f} $ dans le wallet)"
        elif s["start_usd"] is None:
            s["start_usd"] = round(equity(s, me, px), 2)     # the -30% stop counts from the first real buy
            save(s)
    if why:
        log(side="skip", mint=mint, symbol=sym, reason=why)
        say(f"{tag(m)} · ${sym} pas acheté : {why}", agent="GARDE")
        return
    summary = route(NATIVE, token, wei)
    dec = decimals(token)
    if m == "dry":
        tokens, fee, tx = int(summary.get("amountOut") or 0), float(summary.get("gasUsd") or 0), "-"
    else:
        before = balance_of(token, me)
        b = build(summary, me, LIVE["slippage_bps"])
        cap = int(LIVE["max_tx_usd"] / px * 1e18)
        try:
            tx, ok, fee_wei = send(acct, b["routerAddress"], wei, b["data"], cap)
        except Exception:
            if balance_of(token, me) <= before:   # no receipt in time, yet the tokens may be there: the wallet decides
                raise
            tx, ok, fee_wei = "?", True, 0
        fee = fee_wei / 1e18 * px
        if not ok:
            log(side="buy", mint=mint, symbol=sym, gas_usd=round(fee, 3), tx=tx, status="échec")
            say(f"{tag(m)} · achat de ${sym} annulé sur la chaîne (gas perdu {fee:.2f} $) · tx {tx}", agent="GARDE")
            return
        tokens = balance_of(token, me) - before
    if tokens <= 0:
        say(f"ALERTE · {tag(m)} · ${sym} : aucun token reçu", agent="GARDE", kind="error")
        return
    usd_in = usd + fee
    price = usd_in / (tokens / 10 ** dec)
    paper = o.get("price") or None
    gap = (price / paper - 1) * 100 if paper else None
    s["positions"][mint] = {"symbol": sym, "tokens": tokens, "dec": dec, "usd_in": round(usd_in, 4), "usd_out": 0.0,
                            "opened": time.time(), "price": price, "paper_price": paper, "fails": 0}
    s["buys"] = [t for t in s["buys"] if t > time.time() - 86400] + [time.time()]
    save(s)
    log(side="buy", mint=mint, symbol=sym, usd=round(usd_in, 2), tokens=tokens, price=f"{price:.10g}",
        paper_price=f"{paper:.10g}" if paper else "", gap_pct=f"{gap:+.1f}" if gap is not None else "",
        gas_usd=round(fee, 3), tx=tx, status="ok")
    said_gap = f" · prix {gap:+.1f} % vs paper" if gap is not None else ""
    say(f"{tag(m)} · acheté ${sym} pour {usd_in:.2f} ${said_gap}" + (f" · tx {tx}" if m == "on" else ""),
        agent="GARDE")


def sell(mint: str, share: float, reason: str):
    import chains
    m = mode()
    s = load()
    pos = s["positions"].get(mint)
    if not pos:
        return
    sym, token = pos["symbol"], chains.split(mint)[1].lower()
    whole = share >= 0.999
    acct = me = None
    if m == "on":
        acct = account()
        me = acct.address.lower()
        held = balance_of(token, me)
    else:
        held = int(pos["tokens"])
    amount = held if whole else int(held * share)
    if amount <= 0:
        if whole:
            _close(s, mint, pos, reason)
        return
    px = bnb_usd()
    err, got, tx, fee = None, 0.0, "-", 0.0
    for bps in ((2000,) if reason in RUG else (LIVE["sell_slippage_bps"], 2000)):
        try:
            summary = route(token, NATIVE, amount)
            if m == "dry":
                got = int(summary.get("amountOut") or 0) / 1e18 * px - float(summary.get("gasUsd") or 0)
                err = None
                break
            if allowance(token, me, ROUTER) < amount:
                h, ok, f = send(acct, token, 0, APPROVE + _word(ROUTER) + _word(amount), 0)
                fee += f / 1e18 * px
                if not ok:
                    raise RuntimeError("le token refuse l'approbation")
            b0 = bnb_balance(me)
            b = build(summary, me, bps)
            tx, ok, f = send(acct, b["routerAddress"], 0, b["data"], 0)
            if not ok:
                fee += f / 1e18 * px
                raise RuntimeError(f"vente annulée sur la chaîne (slippage {bps / 100:.0f} %)")
            got = (bnb_balance(me) - b0) / 1e18 * px - fee        # BNB in, net of the swap's and the approval's gas
            err = None
            break
        except Exception as e:
            err = e
    if err is not None:
        pos["fails"] = pos.get("fails", 0) + 1
        pos["last_fail"] = time.time()
        save(s)
        log(side="sell", mint=mint, symbol=sym, reason=reason, status=f"échec: {str(err)[:80]}")
        say(f"ALERTE · {tag(m)} · vente de ${sym} impossible ({reason}) : {str(err)[:160]}", key="sell:" + mint,
            kind="error")
        return
    pos["usd_out"] = round(pos.get("usd_out", 0) + got, 4)
    pos["tokens"] = (balance_of(token, me) if m == "on" else held - amount)
    log(side="sell", mint=mint, symbol=sym, usd=round(got, 2), tokens=amount, gas_usd=round(fee, 3), reason=reason,
        tx=tx, status="ok")
    part = "tout" if whole else f"{share * 100:.0f} % du reste"
    if whole or pos["tokens"] <= 0:
        c = _close(s, mint, pos, reason)
        paper = f" · paper {c['paper_pct']:+.0f} %" if c["paper_pct"] is not None else ""
        say(f"{tag(m)} · vendu {part} de ${sym} ({reason}) · {c['usd_out']:.2f} $ pour {c['usd_in']:.2f} $ "
            f"→ {c['real_pct']:+.0f} %{paper}" + (f" · tx {tx}" if m == "on" else ""))
    else:
        save(s)
        say(f"{tag(m)} · vendu {part} de ${sym} ({reason}) · {got:.2f} $" + (f" · tx {tx}" if m == "on" else ""))


def _close(s: dict, mint: str, pos: dict, reason: str) -> dict:
    c = {"mint": mint, "symbol": pos["symbol"], "opened": pos["opened"], "closed": time.time(), "reason": reason,
         "usd_in": pos["usd_in"], "usd_out": round(pos.get("usd_out", 0), 2),
         "real_pct": round((pos.get("usd_out", 0) / pos["usd_in"] - 1) * 100, 1) if pos["usd_in"] else 0.0,
         "paper_pct": paper_pct(mint, pos["opened"])}
    s["closed"].append(c)
    s["positions"].pop(mint, None)
    save(s)
    return c


def paper_pct(mint: str, opened: float) -> float | None:
    """What the paper book made on the same token over the same holding: the number real money is judged by."""
    import book
    since = time.strftime("%Y-%m-%d %H:%M", time.localtime(opened - 120))
    rows = [t for t in book.trades() if t["mint"] == mint and t["time"] >= since]
    opens = [t for t in rows if t["action"] == "open"]
    if not opens or not float(opens[0]["usd"] or 0):
        return None
    return round(sum(float(t["pnl"]) for t in rows) / float(opens[0]["usd"]) * 100, 1)


# ---------- the 5-minute check: reconcile, value, stop ----------

def equity(s: dict, me: str | None, px: float) -> float:
    """The wallet's BNB plus its open positions at today's pool prices, in $."""
    import market
    total = bnb_balance(me) / 1e18 * px if me else 0.0
    for mint, pos in s["positions"].items():
        p = (market.pool(mint) or {}).get("price") or 0
        tokens = balance_of(mint.split(":", 1)[1], me) if me else int(pos["tokens"])
        total += tokens / 10 ** pos["dec"] * p
    return total


def tick():
    m = mode()
    if m == "off":
        return
    import book
    with _LOCK:
        paper = book.load()
        for mint, pos in list(load()["positions"].items()):
            # the paper desk closed it while the order was lost (a restart): out now, retried every 10 min
            if mint not in paper and pos.get("fails", 0) < 6 and time.time() - pos.get("last_fail", 0) > 600:
                sell(mint, 1.0, "réconciliation")
        status()


def status() -> dict:
    m = mode()
    s = load(m)
    out = {"t": time.time(), "mode": m, "address": None, "bnb_usd": None, "bnb": None, "equity_usd": None,
           "start_usd": s["start_usd"], "stopped": s["stopped"], "stop_file": os.path.exists(STOP),
           "positions": [], "compare": compare(s)}
    try:
        px = bnb_usd()
        out["bnb_usd"] = px
        me = None
        if m == "on":
            me = account().address.lower()
            out["address"] = me
            out["bnb"] = round(bnb_balance(me) / 1e18, 6)
        import market
        for mint, pos in s["positions"].items():
            p = (market.pool(mint) or {}).get("price") or 0
            value = int(pos["tokens"]) / 10 ** pos["dec"] * p
            out["positions"].append({"symbol": pos["symbol"], "mint": mint, "usd_in": pos["usd_in"],
                                     "value_usd": round(value, 2), "pct": round((value + pos.get("usd_out", 0))
                                                                                / pos["usd_in"] * 100 - 100, 1)})
        if m == "on":
            out["equity_usd"] = round(out["bnb"] * px + sum(p["value_usd"] for p in out["positions"]), 2)
            floor = (s["start_usd"] or 0) * (1 + LIVE["stop_pct"] / 100)
            if s["start_usd"] and out["equity_usd"] < floor and not s["stopped"]:
                s["stopped"] = True
                save(s, m)
                out["stopped"] = True
                say(f"ALERTE · RÉEL · arrêt à {LIVE['stop_pct']} % : le wallet vaut {out['equity_usd']:.2f} $ pour "
                    f"{s['start_usd']:.2f} $ au départ. plus aucun achat réel, les ventes continuent", kind="error")
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {str(e)[:160]}"
    tmp = atomic.tmp(STATUS)
    with open(tmp, "w") as f:
        json.dump(out, f)
    os.replace(tmp, STATUS)
    return out


def compare(s: dict) -> dict:
    c = [x for x in s["closed"] if x.get("paper_pct") is not None]
    if not c:
        return {"n": 0}
    real = sum(x["real_pct"] for x in c) / len(c)
    paper = sum(x["paper_pct"] for x in c) / len(c)
    return {"n": len(c), "real_avg": round(real, 1), "paper_avg": round(paper, 1), "gap": round(real - paper, 1)}


def summary() -> dict:
    """For the dashboard: the last status written, no network."""
    try:
        with open(STATUS) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"mode": mode()}


# ---------- the command line ----------

def new_wallet():
    if env.get("LIVE_KEY"):
        print("un wallet existe déjà dans .env (LIVE_KEY). rien n'est changé. son adresse :")
        print(account().address)
        return
    from eth_account import Account
    a = Account.create()
    k = a.key.hex()
    k = k if k.startswith("0x") else "0x" + k
    path = os.path.join(HERE, ".env")
    lead = ""
    if os.path.exists(path) and os.path.getsize(path):
        with open(path, "rb") as f:
            f.seek(-1, 2)
            lead = "" if f.read(1) == b"\n" else "\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a") as f:
        f.write(f"{lead}LIVE_KEY={k}\n")
    os.chmod(path, 0o600)
    print("wallet créé. sa clé est dans .env (lisible par toi seul), elle ne s'affiche jamais.")
    print("adresse à donner à Binance, réseau BNB Smart Chain (BEP20) :")
    print(a.address)


def test():
    def line(name, fn):
        try:
            print(f"OK    {name} : {fn()}")
        except Exception as e:
            print(f"ÉCHEC {name} : {type(e).__name__}: {str(e)[:160]}")
    line("mode", lambda: f"LIVE={mode()}" + (" (rien ne part tant que ce n'est pas dry ou on)" if mode() == "off" else ""))
    line("RPC BNB Chain", lambda: f"bloc {_int(rpc('eth_blockNumber', []))}")
    line("relais anti-sandwich", lambda: f"chaîne {_int(rpc('eth_chainId', [], url=env.get('LIVE_SEND_RPC') or SEND_RPC))}")
    line("prix du BNB", lambda: f"{bnb_usd():.2f} $")
    line("KyberSwap", lambda: f"{LIVE['ticket_usd']} $ de BNB → "
                              f"{int(route(NATIVE, CAKE, int(LIVE['ticket_usd'] / bnb_usd() * 1e18))['amountOut']) / 1e18:.2f} CAKE")
    line("honeypot.is", lambda: honeypot(CAKE) or "CAKE revendable")
    if env.get("LIVE_KEY"):
        line("wallet", lambda: f"{account().address} · {bnb_balance(account().address.lower()) / 1e18:.5f} BNB")
    else:
        print("—     wallet : pas encore créé (python3 live.py new-wallet)")


def show():
    st = status()
    print(json.dumps({k: v for k, v in st.items() if k != "positions"}, indent=1, ensure_ascii=False))
    for p in st["positions"]:
        print(f"  ${p['symbol']} : {p['usd_in']:.2f} $ investis · vaut {p['value_usd']:.2f} $ · {p['pct']:+.1f} %")
    for c in load()["closed"][-15:]:
        print(f"  fermé ${c['symbol']} {c['reason']} : réel {c['real_pct']:+.1f} % · paper {c['paper_pct']} %")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "new-wallet":
        new_wallet()
    elif cmd == "test":
        test()
    elif cmd == "sellall":
        open(SELLALL, "w").close()
        open(STOP, "w").close()
        print("demandé : le desk vend toutes les positions réelles d'ici 30 s et n'achète plus (data/STOP).")
    elif cmd == "reset-start":
        s = load()
        me = account().address.lower() if mode() == "on" else None
        s["start_usd"], s["stopped"] = round(equity(s, me, bnb_usd()), 2), False
        save(s)
        print(f"le stop de {LIVE['stop_pct']} % compte maintenant depuis {s['start_usd']:.2f} $")
    else:
        show()
