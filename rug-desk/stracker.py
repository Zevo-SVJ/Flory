# stracker.py
# Solana Tracker's Data API: who bought this token and how. it tags each early wallet as a sniper
# (bought in the first blocks), an insider (linked to the creator) or a bundler (bought inside the
# launch bundle), with the share of supply each group still holds, plus a "rugged" flag.
# that is the Bubblemaps-style read a script can't afford to rebuild for every token.
# free plan: 2,500 requests (https://www.solanatracker.io/data-api), key in .env as SOLANATRACKER_KEY.
# the desk calls it once per token, and only for tokens that already passed every other check.
# response shape from the official SDK (@solana-tracker/data-api 0.5.0, interfaces.d.ts: TokenRisk).
import requests
import env

BASE = "https://data.solanatracker.io"


def key() -> str | None:
    return env.get("SOLANATRACKER_KEY")


def fetch(mint: str) -> dict | None:
    """The risk block, normalized to percentages of supply. None without a key."""
    k = key()
    if not k:
        return None
    r = requests.get(f"{BASE}/tokens/{mint}", headers={"x-api-key": k}, timeout=15)
    r.raise_for_status()
    risk = (r.json() or {}).get("risk") or {}
    pct = lambda cat: ((risk.get(cat) or {}).get("totalPercentage"))
    bundlers = risk.get("bundlers")
    if bundlers is None:                  # the summary can be omitted: the dedicated endpoint has it
        try:
            b = requests.get(f"{BASE}/tokens/{mint}/bundlers", headers={"x-api-key": k}, timeout=15)
            b.raise_for_status()
            bj = b.json() or {}
            bundlers = {"totalPercentage": bj.get("percentage"), "totalInitialPercentage": bj.get("initialPercentage")}
        except Exception:
            bundlers = {}
    return {
        "rugged": bool(risk.get("rugged")),
        "snipers_pct": pct("snipers"),
        "insiders_pct": pct("insiders"),
        "bundlers_pct": bundlers.get("totalPercentage"),
        "bundlers_initial_pct": bundlers.get("totalInitialPercentage"),
        "dev_pct": (risk.get("dev") or {}).get("percentage"),
        "top10": risk.get("top10"),
        "risks": [f"{x.get('name')} ({x.get('level')})" for x in (risk.get("risks") or [])][:6],
    }


def kill(s: dict | None, thresholds: dict) -> str | None:
    if not s:
        return None
    if s["rugged"]:                                                            return "st_rugged"
    over = lambda v, k: isinstance(v, (int, float)) and v > thresholds[k]
    if over(s["bundlers_pct"], "max_bundlers_pct"):                            return "bundled"
    if over(s["insiders_pct"], "max_insiders_pct"):                            return "insiders"
    if over(s["snipers_pct"], "max_snipers_pct"):                              return "snipers"
    return None
