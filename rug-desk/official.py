# official.py
# the one case where an event coin is not a bet on a copy: the brand itself posts a contract address.
# $TRUMP, Jan 2025: the CA came from Trump's own accounts; the wallets that bought in its first hours under
# $1 and sold into the eve's euphoria (~$73) are the 58 that made $10M+ each (Chainalysis). a 20-60 min
# lag still made x10 to x70 there.
# ECHO checks @RockstarGames every pass and appends what the account itself posts to data/official_ca.txt
# (ECHO.md). this file only reads it: a new line sends Telegram the CA, its pool and the checks to make by
# hand, and SCOUT follows it as an event token on paper. it never buys for real: the live wallet's caps
# stay as they are, the decision and the size are Skide's.
import json, os, re, time
from config import DATA

FILE = os.path.join(DATA, "official_ca.txt")      # "YYYY-MM-DD HH:MM | event | chain | CA | post url"
SEEN = os.path.join(DATA, "official_seen.json")
EVM = re.compile(r"^0x[0-9a-fA-F]{40}$")
SOL = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


def parse(line: str) -> dict | None:
    """One ECHO line, or None when it is not one (a CA that is not an address is never relayed)."""
    parts = [p.strip() for p in line.split("|")]
    if len(parts) < 5 or line.lstrip().startswith("#"):
        return None
    when, event, chain, ca, url = parts[:5]
    chain = chain.lower()
    if not (EVM.match(ca) if chain != "solana" else SOL.match(ca)):
        return None
    if not url.startswith("https://x.com/RockstarGames/status/"):
        return None                                   # only the account itself: a quote, a "news" account, no
    return {"when": when, "event": event, "chain": chain, "ca": ca, "url": url}


def _seen() -> set[str]:
    try:
        with open(SEEN) as f:
            return set(json.load(f))
    except (OSError, ValueError):
        return set()


def text(o: dict, m: dict | None) -> str:
    pool = (f"pool ${m['liq_usd'] / 1e3:,.0f}k, cap ${(m.get('mcap') or 0) / 1e6:,.1f}M, "
            f"âge {m.get('age_min') or 0:.0f} min") if m else "pas encore de pool sur DexScreener"
    return (f"🚨 {o['event']} : CONTRAT PUBLIÉ PAR LE COMPTE OFFICIEL ? ({o['chain']})\n{o['ca']}\n{pool}\n"
            f"post : {o['url']}\n"
            f"https://dexscreener.com/{o['chain']}/{o['ca']}\n\n"
            "Avant d'acheter, à la main :\n"
            "1. Ouvre le post : compte @RockstarGames avec son badge, un post du compte (pas une réponse "
            "ni un repost d'un autre)\n"
            "2. Le CA du post = celui-ci, 6 premiers et 6 derniers caractères\n"
            "3. Confirmé ailleurs (rockstargames.com/newswire, Take-Two, presse jeu vidéo) ? Sinon le compte "
            "est peut-être piraté : un compte piraté qui poste un token est l'arnaque classique\n"
            "4. Taille : seulement ce que tu acceptes de perdre en entier\n"
            "5. Sortie : par tranches dans la montée, tout vendu avant la sortie du jeu (le 19, 6h)")


def tick() -> list[str]:
    """New official lines since the last call: Telegram hears each once. Returns the texts sent."""
    if not os.path.exists(FILE):
        return []
    import chains, market, notify, scan
    seen, out = _seen(), []
    with open(FILE) as f:
        lines = [l.strip() for l in f if l.strip()]
    for l in lines:
        o = parse(l)
        if not o or o["ca"] in seen:
            continue
        k = chains.key(o["chain"], o["ca"]) if chains.supported(o["chain"]) else None
        m = None
        if k:
            scan.event_mints[k] = o["event"]          # followed on paper like the event's other tokens
            try:
                m = market.pools([k]).get(k)
            except Exception:
                pass
        t = text(o, m)
        notify.post(t)
        out.append(t)
        seen.add(o["ca"])
    if out:
        with open(SEEN, "w") as f:
            json.dump(sorted(seen), f)
    return out
