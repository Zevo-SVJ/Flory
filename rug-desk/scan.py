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


def _done() -> set[str]:
    """Mints we never need to look at again: a final verdict, or a retryable kill that's still recent."""
    if not os.path.exists(LOG):
        return set()
    last = {}
    with open(LOG, newline="") as f:
        for r in csv.DictReader(f):
            last[r["mint"]] = r
    cutoff = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - RETRY_AFTER_MIN * 60))
    done = set()
    for mint, r in last.items():
        reason = r["reason"] or ""
        retry = reason in RETRYABLE or " failed" in reason or r["stage"] == "limits"
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


GT = "https://api.geckoterminal.com/api/v2/networks/trending_pools"     # every network at once
NOT_MEMES = {"So11111111111111111111111111111111111111112", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
             "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"}      # SOL, USDC, USDT
gt_error = None


def gt_trending() -> list[str]:
    """GeckoTerminal's trending Solana pools over 5 min and 1 h (free, no key, ~10 calls a minute):
    the tokens moving now, whatever their age. the momentum lane's main source."""
    global gt_error
    out = []
    try:
        for d in ("5m", "1h"):
            r = gt.get(GT, params={"duration": d, "page": 1})          # the shared budget (gt.py)
            r.raise_for_status()
            for p in r.json().get("data") or []:
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
        gt_error = None
        sources.record("geckoterminal", True, f"{len(out)} tokens en tendance")
    except Exception as e:
        gt_error = f"GeckoTerminal trending unreadable: {e}"[:200]
        sources.record("geckoterminal", False, str(e))
    return out


FUNNEL = os.path.join(os.path.dirname(LOG), "funnel.jsonl")   # one line per SCOUT run: python3 diag.py --entonnoir


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
    for k, m in turn:
        if n >= FACTS["shadow_pool_per_run"]:
            break
        p = live[m]
        n += shadow.note(m, {"verdict": "SKIP", "stage": "pool", "reason": k, "symbol": p.get("symbol"),
                             "price": p.get("price"), "liq_usd": p.get("liq_usd")})
    return n


def leads() -> list[str]:
    import shadow
    done, out, errors, waived = _done(), [], [], shadow.waived()
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
    picked = mixed[:SCHEDULE["scan_per_run"]]
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
