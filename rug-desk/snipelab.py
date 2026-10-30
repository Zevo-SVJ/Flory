# snipelab.py
# the dry sniper. would a pump.fun sniper make money, at the speed THIS desk can reach? nothing is ever
# bought: every new launch is seen live, the desk's launch-time filters run, and for a sample of the ones
# that pass, the price the desk could really have paid is recorded (the first trade after its delay, never
# block 0: that belongs to the creator's own bundle and to the paid snipers), then the token is followed for
# 30 minutes and replayed with the Solana exits, the curve fee and a Jito tip on each side.
#
# why: the evidence (Oct 28) says snipers as a whole netted 3.5-7% of what they spent, creators' bundles 20x
# more (Bitquery). this measures our own case before any server, tip or real SOL is paid for.
# the rule, fixed before the data: 300 entries, mean net > 0 with its 95% interval above 0 and both halves
# positive -> a real sniper is worth discussing. otherwise it is not.
#
#   python3 snipelab.py run        in a Terminal tab of its own, leave it open (it reconnects by itself)
#   python3 snipelab.py report     the result so far
#   python3 snipelab.py sonde      90 s: do the prices of the launches we follow come in?
#
# data: PumpPortal's free public websocket for the launches. its trade stream needs an API key funded with
# 0.02 SOL (Oct 30: 4,334 launches followed, 0 trades received), so the price comes from the chain instead:
# each followed launch's bonding-curve account, watched on the Helius websocket (SOLANA_RPC in .env). the
# account changes on every buy and sell, and its reserves are the curve's price, the same numbers
# PumpPortal's trades carried.
import asyncio, base64, json, os, random, statistics, struct, sys, time
from config import DATA, SNIPE
import ruggers

URL = "wss://pumpportal.fun/api/data"
OUT = os.path.join(DATA, "snipe.jsonl")


def price(ev: dict) -> float | None:
    """SOL per token on the bonding curve after this event."""
    s, t = ev.get("vSolInBondingCurve"), ev.get("vTokensInBondingCurve")
    try:
        if s and t:
            return float(s) / float(t)
        if ev.get("marketCapSol"):
            return float(ev["marketCapSol"]) / 1e9
    except (TypeError, ValueError):
        pass
    return None


def curve(data_b64: str) -> dict | None:
    """A pump.fun bonding-curve account -> the reserves PumpPortal's trade events carried (SOL and whole
    tokens, 6 decimals). layout: 8-byte discriminator, then u64 virtual token reserves, virtual SOL
    reserves, real token reserves, real SOL reserves, total supply, then the bool "complete"."""
    try:
        raw = base64.b64decode(data_b64)
        vtok, vsol = struct.unpack_from("<QQ", raw, 8)
        complete = bool(raw[48]) if len(raw) > 48 else False
    except Exception:
        return None
    if not vtok or not vsol:
        return None
    return {"vSolInBondingCurve": vsol / 1e9, "vTokensInBondingCurve": vtok / 1e6, "complete": complete}


def ws_url() -> str | None:
    """The Helius websocket, from the RPC URL in .env. None without Helius: the public RPC drops sockets."""
    import facts
    u = facts.RPC_URL or ""
    return u.replace("https://", "wss://", 1) if "helius" in u else None


def launch_kill(ev: dict, blacklist: set) -> str | None:
    """The checks a sniper can run in the launch block: who made it, and how much it kept."""
    dev = ev.get("traderPublicKey")
    if dev and dev in blacklist:
        return "dev_rugged_before"
    try:
        dev_pct = 100 * float(ev.get("initialBuy") or 0) / 1e9
    except (TypeError, ValueError):
        dev_pct = 0
    if dev_pct > SNIPE["max_dev_buy_pct"]:
        return "dev_buy_heavy"
    if price(ev) is None:
        return "no_price"
    return None


class Lab:
    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self.tracked: dict[str, dict] = {}
        self.blacklist = ruggers.known()
        self.counts: dict[str, int] = {}
        self.msgs: dict[str, int] = {}       # every message by type: 0 trades means the trade stream is not coming

    def on_create(self, ev: dict, now: float) -> str | None:
        """Returns the mint to subscribe to, or None."""
        mint = ev.get("mint")
        if not mint or mint in self.tracked:
            return None
        why = launch_kill(ev, self.blacklist)
        self.counts[why or "pass"] = self.counts.get(why or "pass", 0) + 1
        if why or len(self.tracked) >= SNIPE["max_tracked"] or self.rng.random() > 1 / SNIPE["sample_every"]:
            return None
        self.tracked[mint] = {"mint": mint, "symbol": ev.get("symbol"), "dev": ev.get("traderPublicKey"),
                              "curve": ev.get("bondingCurveKey"), "t0": now, "launch_px": price(ev),
                              "entry": None, "pts": []}
        return mint

    def on_trade(self, ev: dict, now: float):
        tr = self.tracked.get(ev.get("mint"))
        p = price(ev)
        if not tr or p is None:
            return
        vsol = float(ev.get("vSolInBondingCurve") or 0) or None
        if tr["entry"] is None:
            if now < tr["t0"] + SNIPE["latency_s"]:
                return
            tr["entry"] = {"t": now, "price": p, "vsol": vsol}     # the first trade after our delay
        tr["pts"].append({"t": now, "price": p, "liq": None, "b5": None, "s5": None, "v5": None})

    def due(self, now: float) -> list[str]:
        return [m for m, tr in self.tracked.items() if now >= tr["t0"] + SNIPE["follow_min"] * 60]

    def finish(self, mint: str) -> dict:
        tr = self.tracked.pop(mint)
        row = {k: tr[k] for k in ("mint", "symbol", "dev", "t0", "launch_px")}
        e = tr["entry"]
        if not e or len(tr["pts"]) < 2:
            return {**row, "entered": False}
        import exits, exitlab
        gross = exitlab.simulate(exits.features(tr["pts"]), exits.for_mint(mint))
        if gross is None:
            return {**row, "entered": False}
        gross_pct = gross / exitlab.TICKET_USD * 100
        ticket = SNIPE["ticket_sol"]
        impact = 100 * ticket / e["vsol"] if e.get("vsol") else 1.0
        cost = 2 * (SNIPE["curve_fee_pct"] + impact) + 2 * 100 * SNIPE["tip_sol"] / ticket
        peak = max(p["price"] for p in tr["pts"]) / e["price"] - 1
        return {**row, "entered": True, "delay_s": round(e["t"] - tr["t0"], 1),
                "vs_launch_pct": round((e["price"] / tr["launch_px"] - 1) * 100, 1) if tr["launch_px"] else None,
                "gross_pct": round(gross_pct, 1), "cost_pct": round(cost, 2), "net_pct": round(gross_pct - cost, 1),
                "peak_pct": round(peak * 100, 1), "trades": len(tr["pts"])}


def save(row: dict):
    os.makedirs(DATA, exist_ok=True)
    with open(OUT, "a") as f:
        f.write(json.dumps(row) + "\n")


def rows() -> list[dict]:
    try:
        with open(OUT) as f:
            return [json.loads(x) for x in f if x.strip()]
    except OSError:
        return []


def report(rs: list[dict] | None = None) -> dict:
    rs = rows() if rs is None else rs
    ins = [r for r in rs if r.get("entered")]
    xs = [r["net_pct"] for r in ins]
    out = {"followed": len(rs), "entered": len(ins)}
    if len(xs) < 2:
        return {**out, "verdict": f"pas encore assez d'entrées ({len(xs)}/{SNIPE['min_n']})"}
    rng = random.Random(5)
    boots = sorted(statistics.mean(rng.choice(xs) for _ in xs) for _ in range(1000))
    half = len(xs) // 2
    h1, h2 = statistics.mean(xs[:half]), statistics.mean(xs[half:])
    mean = statistics.mean(xs)
    ok = len(xs) >= SNIPE["min_n"] and boots[25] > 0 and h1 > 0 and h2 > 0
    verdict = ("OUI : un vrai sniper mérite d'être étudié" if ok else
               f"pas encore ({len(xs)}/{SNIPE['min_n']} entrées)" if len(xs) < SNIPE["min_n"] else
               "NON : à notre vitesse, sniper pump.fun ne rapporte pas")
    return {**out, "mean_net_pct": round(mean, 1), "ci95": [round(boots[25], 1), round(boots[974], 1)],
            "half1": round(h1, 1), "half2": round(h2, 1),
            "win_pct": round(100 * sum(x > 0 for x in xs) / len(xs)),
            "median_net_pct": round(statistics.median(xs), 1),
            "mean_without_best": round(statistics.mean(sorted(xs)[:-1]), 1),
            "mean_delay_s": round(statistics.mean(r["delay_s"] for r in ins), 1),
            "mean_vs_launch_pct": round(statistics.mean(r["vs_launch_pct"] or 0 for r in ins), 1),
            "verdict": verdict}


async def run():
    """Two sockets: PumpPortal says what launches, Helius says what each followed curve does."""
    import websockets
    hel = ws_url()
    if not hel:
        print("pas de Helius dans .env (SOLANA_RPC) : le sniper à blanc ne peut pas lire les prix", flush=True)
        return
    lab, backoff = Lab(), 2
    while True:
        try:
            async with websockets.connect(URL, ping_interval=20, ping_timeout=20, max_size=2 ** 22) as pp, \
                    websockets.connect(hel, ping_interval=20, ping_timeout=20, max_size=2 ** 22) as hs:
                await pp.send(json.dumps({"method": "subscribeNewToken"}))
                lab.tracked.clear()               # their curves were watched on the old socket: start over
                pending, subs, mints, req = {}, {}, {}, [0]

                async def watch(mint):
                    req[0] += 1
                    pending[req[0]] = mint
                    await hs.send(json.dumps({"jsonrpc": "2.0", "id": req[0], "method": "accountSubscribe",
                                              "params": [lab.tracked[mint]["curve"],
                                                         {"encoding": "base64", "commitment": "confirmed"}]}))

                async def launches():
                    async for msg in pp:
                        try:
                            ev = json.loads(msg)
                        except ValueError:
                            continue
                        kind = ev.get("txType") or "message"
                        lab.msgs[kind] = lab.msgs.get(kind, 0) + 1
                        if kind == "create":
                            m = lab.on_create(ev, time.time())
                            if m and lab.tracked[m].get("curve"):
                                await watch(m)
                            elif m:
                                lab.tracked.pop(m, None)

                async def curves():
                    async for msg in hs:
                        try:
                            ev = json.loads(msg)
                        except ValueError:
                            continue
                        if "id" in ev and ev["id"] in pending:
                            m = pending.pop(ev["id"])
                            if "result" in ev and m in lab.tracked:
                                subs[ev["result"]], mints[m] = m, ev["result"]
                            elif "error" in ev and lab.msgs.get("helius_error", 0) < 3:
                                print(f"[{time.strftime('%H:%M:%S')}] Helius dit : {str(ev['error'])[:160]}", flush=True)
                            lab.msgs["helius_error" if "error" in ev else "subscribed"] = \
                                lab.msgs.get("helius_error" if "error" in ev else "subscribed", 0) + 1
                            continue
                        p = ev.get("params") or {}
                        m = subs.get(p.get("subscription"))
                        data = (((p.get("result") or {}).get("value") or {}).get("data") or [None])[0]
                        c = curve(data) if m and data else None
                        if c:
                            lab.msgs["curve"] = lab.msgs.get("curve", 0) + 1
                            lab.on_trade({"mint": m, **c}, time.time())

                async def clock():
                    last_note = time.time()
                    while True:
                        await asyncio.sleep(1)
                        now = time.time()
                        for m in lab.due(now):
                            save(lab.finish(m))
                            sid = mints.pop(m, None)
                            if sid is not None:
                                subs.pop(sid, None)
                                req[0] += 1
                                await hs.send(json.dumps({"jsonrpc": "2.0", "id": req[0], "method": "accountUnsubscribe",
                                                          "params": [sid]}))
                        if now - last_note > 600:
                            r = report()
                            print(f"[{time.strftime('%H:%M:%S')}] {r['entered']} entrées · {r.get('mean_net_pct', '-')} % net moyen · "
                                  f"{r['verdict']} · lancements vus : {lab.counts} · messages : {lab.msgs}", flush=True)
                            last_note = now

                print(f"[{time.strftime('%H:%M:%S')}] connecté à PumpPortal (lancements) et Helius (prix)", flush=True)
                backoff = 2
                tasks = [asyncio.create_task(x()) for x in (launches, curves, clock)]
                done, rest = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
                for t in rest:
                    t.cancel()
                for t in done:
                    if t.exception():
                        raise t.exception()
                raise RuntimeError("un flux s'est fermé")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] flux coupé ({str(e)[:100]}), reconnexion dans {backoff} s", flush=True)
            await asyncio.sleep(backoff)
            backoff = min(60, backoff * 2)


async def probe(seconds: int = 90):
    """Do the prices come? follows the first 3 launches' bonding curves on Helius for `seconds` and prints
    every update. a few per token within a minute is normal; nothing means no prices."""
    import websockets
    hel = ws_url()
    if not hel:
        print("VERDICT : pas de Helius dans .env (SOLANA_RPC), le sniper ne peut pas lire les prix")
        return
    n, subs, t_end = {}, {}, time.time() + seconds
    async with websockets.connect(URL, ping_interval=20, ping_timeout=20, max_size=2 ** 22) as pp, \
            websockets.connect(hel, ping_interval=20, ping_timeout=20, max_size=2 ** 22) as hs:
        await pp.send(json.dumps({"method": "subscribeNewToken"}))
        while time.time() < t_end:
            for ws in (pp, hs):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue
                ev = json.loads(msg)
                if ev.get("txType") == "create" and len(subs) < 3 and ev.get("bondingCurveKey"):
                    subs[len(subs) + 1] = ev.get("symbol")
                    await hs.send(json.dumps({"jsonrpc": "2.0", "id": len(subs), "method": "accountSubscribe",
                                              "params": [ev["bondingCurveKey"], {"encoding": "base64", "commitment": "confirmed"}]}))
                    print(f"suivi de {ev.get('symbol')} (courbe {ev['bondingCurveKey'][:8]}…)", flush=True)
                elif "error" in ev:
                    print("Helius dit :", str(ev["error"])[:200], flush=True)
                elif ev.get("method") == "accountNotification":
                    c = curve(ev["params"]["result"]["value"]["data"][0])
                    n["prix"] = n.get("prix", 0) + 1
                    if c:
                        print(f"  prix {c['vSolInBondingCurve'] / c['vTokensInBondingCurve']:.3e} SOL · courbe {c['vSolInBondingCurve']:.1f} SOL", flush=True)
    print(f"en {seconds} s : {n.get('prix', 0)} mises à jour de prix pour {len(subs)} lancements suivis")
    print("VERDICT :", "les prix arrivent : relance  python3 snipelab.py run" if n.get("prix") else
          "AUCUN prix reçu (voir les messages ci-dessus)")


if __name__ == "__main__":
    if sys.argv[1:] == ["sonde"]:
        asyncio.run(probe())
    elif sys.argv[1:] == ["run"]:
        print("sniper à blanc : rien n'est jamais acheté. Ctrl+C pour arrêter.", flush=True)
        try:
            asyncio.run(run())
        except KeyboardInterrupt:
            pass
    else:
        print(json.dumps(report(), indent=1, ensure_ascii=False))
