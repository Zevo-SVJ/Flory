# scan.py
# SCOUT's lead sources, all free DexScreener reads:
#   - tokens that paid for a profile or a boost (paying is not a quality signal, the dev spent money)
#   - the DexScreener search, a rotating set of words, kept to PumpSwap pools in the age window.
#     it finds survivors the paid lists miss (6 vs 3 on the first live test)
# the filter decides the rest.
import csv, json, os, random, time
import requests
from config import LOG, SCHEDULE, FACTS
import check, market, grads, sources, chains, evmnew, gt
from market import market_kill

SOURCES = ["token-profiles/latest/v1", "token-boosts/latest/v1", "token-boosts/top/v1",
           "token-profiles/recent-updates/v1", "community-takeovers/latest/v1", "ads/latest/v1"]
SEARCH = "https://api.dexscreener.com/latest/dex/search"
WORDS = ["pump", "sol", "cat", "dog", "ai", "meme", "pepe", "inu", "moon", "coin", "frog", "baby",
         "gm", "based", "wif", "bonk", "agent", "cto", "degen", "sigma", "trump", "elon", "chill",
         "king", "god", "super", "core", "luke", "gato", "gold", "the", "one", "x", "bull", "bear"]
WORDS_PER_RUN = 4           # every 3 minutes. the search mostly returns old pools: the graduations feed matters more
_turn = 0
grad_error = None           # the on-chain graduation feed's last failure, shown by SCOUT
last_lanes = {"early": 0, "momentum": 0}
last_funnel = {}
# kills that can change with time: a pool grows up, a source comes back. retried after this long
RETRY_AFTER_MIN = 30
RETRYABLE = ("too_fresh", "thin_pool", "no_pool", "no_price", "no_holders", "below_graduation")


def _done(events: set[str] = frozenset(), now_retry: bool = False) -> set[str]:
    """Mints we never need to look at again: a final verdict, or a retryable kill that's still recent.
    events: the tokens of an open event, also retried after a kill that can mend or a pass not bought
    (config EVENT_RETRY), every EVENT_RETRY_MIN, or at once when the event heats up (now_retry)."""
    from config import EVENT_RETRY, EVENT_RETRY_MIN
    if not os.path.exists(LOG):
        return set()
    last = {}
    with open(LOG, newline="") as f:
        for r in csv.DictReader(f):
            last[r["mint"]] = r
    cutoff = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - RETRY_AFTER_MIN * 60))
    ev_cut = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - EVENT_RETRY_MIN * 60))
    done = set()
    for mint, r in last.items():
        reason = r["reason"] or ""
        retry = reason in RETRYABLE or " failed" in reason or r["stage"] == "limits"
        if mint in events and (reason in EVENT_RETRY or (r.get("verdict") in ("PASS", "BUY")
                                                         and (r.get("action") or "").startswith("not bought"))):
            if now_retry or r["time"] <= ev_cut:
                continue
        if not retry or r["time"] > cutoff:
            done.add(mint)
    return done


NARRATIVES = os.path.join(os.path.dirname(LOG), "narratives.txt")   # written by ECHO from X, 1 word a line


def narratives() -> list[str]:
    """ECHO's narrative scan: what X is about to turn into memecoins. Fresh words only (6 h)."""
    if not os.path.exists(NARRATIVES) or time.time() - os.path.getmtime(NARRATIVES) > 6 * 3600:
        return []
    with open(NARRATIVES) as f:
        return [w.strip().lstrip("$").lower() for w in f if w.strip() and not w.startswith("#")][:10]


def searched(trending: list[str] = ()) -> list[str]:
    """PumpSwap pools from the DexScreener search: today's trending tickers (narratives breed
    look-alikes) plus a rotating set of generic WORDS, run after run."""
    global _turn
    words = list(dict.fromkeys([w for w in narratives() if len(w) >= 3]
                               + [w.lower() for w in trending if w and len(w) >= 3]))[:max(3, WORDS_PER_RUN * 2 // 3)]
    words += [WORDS[(_turn + i) % len(WORDS)] for i in range(max(0, WORDS_PER_RUN - len(words)))]
    _turn = (_turn + WORDS_PER_RUN) % len(WORDS)
    now_ms, out = time.time() * 1000, []
    for w in words:
        try:
            r = requests.get(SEARCH, params={"q": w}, timeout=15)
            r.raise_for_status()
        except Exception:
            continue                          # one failed word is not an outage; the next run retries
        data = r.json()
        for p in (data.get("pairs") if isinstance(data, dict) else None) or []:
            age_h = (now_ms - (p.get("pairCreatedAt") or 0)) / 3.6e6
            a = (p.get("baseToken") or {}).get("address")
            chain = p.get("chainId")
            # Solana: PumpSwap only, the one pool whose LP the desk reads on chain. EVM: any DEX, GoPlus reads it
            ok_dex = p.get("dexId") == "pumpswap" if chain == "solana" else chains.supported(chain)
            k = chains.key(chain, a) if a and chains.supported(chain) else None
            if (ok_dex and k and k not in out
                    and FACTS["min_age_min"] / 60 <= age_h <= FACTS["max_age_hours"]
                    and ((p.get("liquidity") or {}).get("usd") or 0) >= FACTS["min_liquidity_usd"]):
                out.append(k)
    return out


event_mints: dict[str, str] = {}       # tokens found by an open event's search: {key: event}, read by check.run


def event_due(mint: str, now: float | None = None, pos: dict | None = None) -> str | None:
    """The event name if `mint` was bought for an event whose sell_by time (local) has come, else None.
    pos: the open position, which carries its event across a restart."""
    from config import EVENT_WATCH
    name = event_mints.get(mint) or (pos or {}).get("event")
    ev = EVENT_WATCH.get(name or "")
    if not ev or not ev.get("sell_by"):
        return None
    due = time.mktime(time.strptime(ev["sell_by"], "%Y-%m-%d %H:%M"))
    return name if (now or time.time()) >= due else None


def event_leads(today: str | None = None) -> dict[str, str]:
    """{token key: event name} for the events whose window is open (config EVENT_WATCH): the same DexScreener
    search and the same age, pool and DEX limits as searched()."""
    from config import EVENT_WATCH
    today = today or time.strftime("%Y-%m-%d")
    out, now_ms = {}, time.time() * 1000
    for name, ev in EVENT_WATCH.items():
        if not ev["from"] <= today <= ev["to"]:
            continue
        seen = {}                                  # pair -> (1 h volume, created): the event's heat
        for w in ev["words"]:
            try:
                r = requests.get(SEARCH, params={"q": w}, timeout=15)
                r.raise_for_status()
                pairs = (r.json() or {}).get("pairs") or []
            except Exception:
                continue
            for p in pairs:
                a, chain = (p.get("baseToken") or {}).get("address"), p.get("chainId")
                if not a or not chains.supported(chain):
                    continue
                seen[p.get("pairAddress") or a] = (float((p.get("volume") or {}).get("h1") or 0),
                                                   p.get("pairCreatedAt") or 0)
                age_h = (now_ms - (p.get("pairCreatedAt") or 0)) / 3.6e6
                ok_dex = p.get("dexId") == "pumpswap" if chain == "solana" else True
                if (ok_dex and FACTS["min_age_min"] / 60 <= age_h
                        and ((p.get("liquidity") or {}).get("usd") or 0) >= FACTS["min_liquidity_usd"]):
                    out.setdefault(chains.key(chain, a), name)
        if seen:
            heat_note(name, sum(v for v, _ in seen.values()),
                      sum(1 for _, t in seen.values() if now_ms - t < 3.6e6))
    return out


HEAT = os.path.join(os.path.dirname(LOG), "event_heat.jsonl")
EVENT_NEWS = os.path.join(os.path.dirname(LOG), "event_news.txt")    # ECHO: a Rockstar post, a trailer (ECHO.md)
_heat_alert: dict[str, float] = {}


def heat_note(name: str, vol1h: float, new1h: int, now: float | None = None):
    """One reading of an event's heat (data/event_heat.jsonl)."""
    with open(HEAT, "a") as f:
        f.write(json.dumps({"t": now or time.time(), "event": name, "vol1h": round(vol1h), "new1h": new1h}) + "\n")


def event_burst(name: str, now: float | None = None) -> str | None:
    """Why the event is heating up now, or None: its 1 h volume ratio x its 24 h median (config EVENT_HEAT),
    or a news ECHO wrote in the last 2 hours."""
    from config import EVENT_HEAT as H
    now = now or time.time()
    if os.path.exists(EVENT_NEWS) and now - os.path.getmtime(EVENT_NEWS) < 7200:
        with open(EVENT_NEWS) as f:
            last = [l.strip() for l in f if l.strip()]
        if last:
            return f"news X : {last[-1][:160]}"
    if not os.path.exists(HEAT):
        return None
    rows = []
    with open(HEAT) as f:
        for l in f:
            try:
                r = json.loads(l)
            except ValueError:
                continue
            if r.get("event") == name and now - r["t"] < 86400:
                rows.append(r)
    if len(rows) < H["min_readings"] + 1:
        return None
    vols = sorted(r["vol1h"] for r in rows[:-1])
    med, cur = vols[len(vols) // 2], rows[-1]["vol1h"]
    if cur >= H["min_usd"] and med > 0 and cur >= H["ratio"] * med:
        return f"volume 1 h ${cur / 1e3:,.0f}k = x{cur / med:.1f} la médiane 24 h, {rows[-1]['new1h']} nouvelles paires"
    return None


def event_alert(now: float | None = None) -> list[str]:
    """The events heating up now; Telegram hears of each at most every alert_every_h."""
    from config import EVENT_WATCH, EVENT_HEAT
    now, out = now or time.time(), []
    today = time.strftime("%Y-%m-%d", time.localtime(now))
    for name, ev in EVENT_WATCH.items():
        if not ev["from"] <= today <= ev["to"]:
            continue
        why = event_burst(name, now)
        if not why:
            continue
        out.append(name)
        if now - _heat_alert.get(name, 0) >= EVENT_HEAT["alert_every_h"] * 3600:
            _heat_alert[name] = now
            try:
                import notify
                notify.post(f"🔥 {name} chauffe : {why}. SCOUT revoit tous ses tokens maintenant.")
            except Exception:
                pass
    return out


GT = "https://api.geckoterminal.com/api/v2/networks/trending_pools"     # every network at once
NOT_MEMES = {"So11111111111111111111111111111111111111112", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
             "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"}      # SOL, USDC, USDT
gt_error = None


def gt_trending() -> list[str]:
    """GeckoTerminal's trending pools over 5 min and 1 h (free, no key, ~10 calls a minute):
    the tokens moving now, whatever their age. a read that fails costs only its own list."""
    global gt_error
    out, failed = [], []
    for d in ("5m", "1h"):
        try:
            r = gt.get(GT, params={"duration": d, "page": 1})          # the shared budget (gt.py)
            r.raise_for_status()
            rows = r.json().get("data") or []
        except Exception as e:
            failed.append(f"{d}: {str(e)[:90]}")
            continue
        for p in rows:
            rel = p.get("relationships") or {}
            net = ((rel.get("network") or {}).get("data") or {}).get("id") or ""
            bid = ((rel.get("base_token") or {}).get("data") or {}).get("id") or ""
            chain = chains.GT_TO_CHAIN.get(net)
            name = ((p.get("attributes") or {}).get("name") or "").split(" / ")[0].strip().lower()
            if not chain or not bid.startswith(net + "_") or name in chains.NOT_MEMES:
                continue
            k = chains.key(chain, bid[len(net) + 1:])
            if k not in NOT_MEMES and k not in out:
                out.append(k)
    gt_error = f"GeckoTerminal trending unreadable: {'; '.join(failed)}"[:200] if len(failed) == 2 else None
    sources.record("geckoterminal", len(failed) < 2,
                   f"{len(out)} tokens en tendance" + (f" (raté {failed[0]})" if len(failed) == 1 else "")
                   if len(failed) < 2 else "; ".join(failed))
    return out


FUNNEL = os.path.join(os.path.dirname(LOG), "funnel.jsonl")   # one line per SCOUT run: python3 diag.py --entonnoir


study_next: list[str] = []      # this run's shadowed pool kills, for GARDE's study (agents.scout)


def sample_shadow(live: dict, waived: set) -> int:
    """Launches killed by a soft pool rule never reach GARDE, so nothing said whether those rules protect.
    a few per run are followed 6 h in shadow like GARDE's kills: the shadow book judges each rule, and
    one that clearly cost money stops applying by itself (shadow.waived). nothing is bought."""
    import shadow, paths
    if len(paths.ghosts()) >= FACTS["shadow_max_ghosts"]:
        return 0
    done = {r["mint"] for r in shadow._rows()}
    by = {}                                  # per rule, so thin pools (most of the kills) don't take every slot
    for m, p in live.items():
        k = market_kill(p, waived) if p else None
        if (m not in done and k in market.SOFT_POOL and market.lane(p) == "early"
                and (p.get("age_min") or 0) >= FACTS["min_age_min"] and (p.get("liq_usd") or 0) >= FACTS["soft_liq_floor_usd"]):
            by.setdefault(k, []).append(m)
    for ms in by.values():
        random.shuffle(ms)
    n, turn = 0, []
    while any(by.values()):
        for k in list(by):
            if by[k]:
                turn.append((k, by[k].pop()))
    # entering earlier, where the bots are fewer: launches under min_age_min on the EVM chains where the
    # shadow book pays (FACTS fresh_chains), followed apart under "too_fresh". data only: the age rule stays
    fresh = [m for m, p in live.items() if p and m not in done and market_kill(p, waived) == "too_fresh"
             and p.get("chain") in FACTS["fresh_chains"] and (p.get("age_min") or 0) >= 5
             and (p.get("liq_usd") or 0) >= FACTS["soft_liq_floor_usd"] and (p.get("price") or 0) > 0]
    random.shuffle(fresh)
    for m in fresh[:FACTS["shadow_fresh_per_run"]]:
        p = live[m]
        n += shadow.note(m, {"verdict": "SKIP", "stage": "pool", "reason": "too_fresh", "symbol": p.get("symbol"),
                             "price": p.get("price"), "liq_usd": p.get("liq_usd")})
    soft = 0
    for k, m in turn:
        if soft >= FACTS["shadow_pool_per_run"]:
            break
        p = live[m]
        if shadow.note(m, {"verdict": "SKIP", "stage": "pool", "reason": k, "symbol": p.get("symbol"),
                           "price": p.get("price"), "liq_usd": p.get("liq_usd")}):
            n += 1
            soft += 1
            study_next.append(m)
    return n


def leads() -> list[str]:
    import shadow
    hot = event_alert()                        # an event heating up: its tokens are all checked again now
    done, out, errors, waived = _done(set(event_mints), now_retry=bool(hot)), [], [], shadow.waived()
    for src in SOURCES:
        try:
            r = requests.get(f"https://api.dexscreener.com/{src}", timeout=15)
            r.raise_for_status()
        except Exception as e:
            errors.append(f"{src}: {e}")
            continue
        for t in r.json():
            a, chain = t.get("tokenAddress"), t.get("chainId")
            k = chains.key(chain, a) if a and chains.supported(chain) else None
            if k and k not in done and k not in out:
                out.append(k)
    live = market.pools(out)
    trending = [(live[m] or {}).get("symbol") for m in out if live.get(m) and not market_kill(live[m], waived)]
    found = searched(trending)
    if len(errors) == len(SOURCES) and not found:
        raise RuntimeError("; ".join(errors))
    out += [a for a in found if a not in done and a not in out]
    # every pump.fun graduation, read on chain: the one source that sees each new PumpSwap pool
    global grad_error
    try:
        grads.fetch()
        grad_error = None
    except Exception as e:
        grad_error = f"pump.fun graduations unreadable: {e}"[:200]
    graduates = [a for a in grads.recent() if a not in done and a not in out]
    out += graduates
    evmnew.fetch()                             # the newest pools on the EVM chains, the same role
    fresh_evm = [k for k in evmnew.recent() if k not in done and k not in out]
    out += fresh_evm
    n_feeds_search_grads = len(out)
    src = {m: "graduation pump.fun" for m in graduates}
    src.update({m: f"nouveau pool {chains.split(m)[0]}" for m in fresh_evm})
    trend = [a for a in gt_trending() if a not in done and a not in out]
    out += trend
    import jup                                 # the most organic trading of the hour, per Jupiter
    top = [a for a in jup.top_organic("1h") if a not in done and a not in out and a not in NOT_MEMES]
    out += top
    found_ev = event_leads()
    event_mints.update(found_ev)
    events = {k: n for k, n in found_ev.items() if k not in done and k not in out}
    out += list(events)
    src.update({m: f"événement {n}" for m, n in events.items()})
    src.update({m: "tendance GeckoTerminal" for m in trend})
    src.update({m: "top organique Jupiter" for m in top})
    # one batched pool read for every lead: most are bonding-curve tokens with no real pool yet.
    # they are not logged, they just come back next run, so the slots go to tokens that can pass
    live.update(market.pools([m for m in out if m not in live]))
    import mbacktest                           # every momentum pool seen, for the momentum backtest
    mbacktest.note(live)
    # a graduate whose pool stayed under $10k two hours after graduating is dead: stop pricing it
    born = grads.load()["mints"]
    grads.forget([m for m in graduates if time.time() - born.get(m, time.time()) > 7200
                  and ((live.get(m) or {}).get("liq_usd") or 0) < 10000])
    seen_evm = evmnew.load()
    evmnew.forget([m for m in fresh_evm if time.time() - seen_evm.get(m, time.time()) > 7200
                   and ((live.get(m) or {}).get("liq_usd") or 0) < 10000])
    # the funnel of this run: where every lead died before GARDE, per lane. shown in SCOUT's panel
    global last_funnel
    funnel = {"early": {}, "momentum": {}}
    for m in out:
        p = live.get(m)
        k = market_kill(p, waived) or "→ GARDE"
        f = funnel[market.lane(p) if p else "early"]
        f[k] = f.get(k, 0) + 1
    by_chain = {}
    for m in out:
        by_chain[chains.split(m)[0]] = by_chain.get(chains.split(m)[0], 0) + 1
    last_funnel = {"leads": len(out), "graduates": len(graduates), "evm_new": len(fresh_evm), "chains": by_chain,
                   "trending": len(trend), "jupiter_top": len(top),
                   "feeds_and_search": n_feeds_search_grads - len(graduates) - len(fresh_evm), **funnel}
    study_next.clear()
    try:
        shadowed = sample_shadow({m: live.get(m) for m in out}, waived)
    except Exception:
        shadowed = 0                           # the sample is a bonus: SCOUT never fails for it
    last_funnel["shadowed"] = shadowed
    try:
        with open(FUNNEL, "a") as f:
            f.write(json.dumps({"t": round(time.time()), **last_funnel}) + "\n")
    except OSError:
        pass
    ok = [m for m in out if not market_kill(live[m], waived)]
    # best pools first, and the two lanes take turns, so momentum's big volumes never crowd out launches
    # SCOUT's self-review ranks its sources by what their tokens earned (coach source_rank, guarded):
    # the best sources first, then by volume. a source is never dropped, only looked at later
    import coach
    rank = {s: i for i, s in enumerate(coach.get("source_rank") or [])}
    ok.sort(key=lambda m: (rank.get(src.get(m, "listes DexScreener"), len(rank)), -(live[m].get("vol_1h") or 0)))
    early = [m for m in ok if market.lane(live[m]) == "early"]
    mom = [m for m in ok if market.lane(live[m]) == "momentum"]
    mixed = [m for pair in zip(early, mom) for m in pair] + early[len(mom):] + mom[len(early):]
    global last_lanes
    last_lanes = {"early": len(early), "momentum": len(mom)}
    from config import EVENT_PER_RUN           # an open event's tokens go first, a few per run
    ev_first = [m for m in mixed if m in event_mints][:EVENT_PER_RUN]
    picked = ev_first + [m for m in mixed if m not in ev_first][:SCHEDULE["scan_per_run"] - len(ev_first)]
    import dossier
    for m in picked:
        dossier.add(m, "SCOUT", "repéré", source=src.get(m, "listes DexScreener"), lane=market.lane(live[m]),
                    liq_usd=round(live[m]["liq_usd"]), age_min=live[m].get("age_min"),
                    chg_1h=live[m].get("chg_1h"), avg_trade=round(live[m].get("avg_trade_1h") or 0, 1))
    return picked


def scan() -> list[dict]:
    return [{"mint": m, **check.run(m)} for m in leads()]


if __name__ == "__main__":
    for v in scan():
        print(json.dumps(v))
