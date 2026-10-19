# jup.py
# Jupiter's token API (free, no key): its own read of a token, built from every swap routed through
# Jupiter. three things in it no other free source gives:
#   - organicScore (0-100): how much of the trading comes from real wallets rather than bots, snipers
#     and copy-trading tools. relative, not absolute: Jupiter advises the raw number over its label
#   - audit.isSus: Jupiter flagged the token as suspicious. the field is only present when flagged
#   - audit.devMints: how many tokens the creator wallet has launched (serial launchers)
# every field is read defensively: an absent field is unknown, and unknown never kills a token.
import requests

URL = "https://lite-api.jup.ag/tokens/v2/search"


def fetch(mint: str) -> dict | None:
    """Jupiter's view of the token, normalized. None if Jupiter doesn't know it or is down."""
    r = requests.get(URL, params={"query": mint}, timeout=10)
    r.raise_for_status()
    data = r.json()
    rows = data if isinstance(data, list) else (data.get("tokens") or data.get("data") or [])
    t = next((x for x in rows if isinstance(x, dict) and (x.get("id") or x.get("address")) == mint), None)
    if not t:
        return None
    audit = t.get("audit") or {}
    h1 = t.get("stats1h") or {}
    vol = (h1.get("buyVolume") or 0) + (h1.get("sellVolume") or 0)
    organic_vol = (h1.get("buyOrganicVolume") or 0) + (h1.get("sellOrganicVolume") or 0)
    num = lambda v: float(v) if isinstance(v, (int, float)) else None
    return {
        "organic": num(t.get("organicScore")),
        "sus": bool(audit.get("isSus")),
        "dev_mints": num(audit.get("devMints")),
        "top_holders_pct": num(audit.get("topHoldersPercentage")),
        "dev_pct": num(audit.get("devBalancePercentage")),
        "holders": num(t.get("holderCount")),
        # share of the last hour's volume Jupiter counts as organic. a bot farm sits near 0
        "organic_vol_share": round(organic_vol / vol * 100, 1) if vol and ("buyOrganicVolume" in h1) else None,
        "traders_1h": num(h1.get("numTraders")),
        "organic_buyers_1h": num(h1.get("numOrganicBuyers")),
        "verified": bool(t.get("isVerified")),
    }


def kill(j: dict | None, thresholds: dict) -> str | None:
    if not j:
        return None
    if j["sus"]:                                                              return "jup_sus"
    if j["dev_mints"] is not None and j["dev_mints"] >= thresholds["max_dev_mints"]:
        return "serial_dev"
    if (j["organic_vol_share"] is not None and (j["traders_1h"] or 0) >= 50
            and j["organic_vol_share"] < thresholds["min_organic_vol_share"]):
        return "inorganic_volume"
    if j["organic"] is not None and j["organic"] < thresholds["min_organic_score"]:
        return "low_organic"
    return None
