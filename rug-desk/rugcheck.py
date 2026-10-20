# rugcheck.py
# a second opinion on a Solana token from RugCheck (rugcheck.xyz), free, read-only: its risk score
# (0-100, higher = riskier), how many "danger" risks it lists, the share of the pool locked.
# GARDE logs it with every verdict, it kills nothing: learn.py finds out whether it foresees the
# losses better than the desk's own checks, and only then does it weigh in (the model decides).
# a key, a 429 or a format change: unknown, never a kill.
import requests
import sources

URL = "https://api.rugcheck.xyz/v1/tokens/{}/report/summary"


def fetch(mint: str) -> dict | None:
    try:
        r = requests.get(URL.format(mint), headers={"accept": "application/json"}, timeout=10)
        if r.status_code in (401, 403):
            sources.record("rugcheck", False, "RugCheck demande une clé : avis désactivé")
            return None
        r.raise_for_status()
        j = r.json()
    except Exception as e:
        sources.record("rugcheck", False, str(e)[:120])
        return None
    if not isinstance(j, dict) or "risks" not in j and "score_normalised" not in j:
        return None
    risks = [x for x in j.get("risks") or [] if isinstance(x, dict)]
    out = {"rc_score": j.get("score_normalised"),
           "rc_danger": sum(1 for x in risks if (x.get("level") or "").lower() == "danger"),
           "rc_lp_locked": j.get("lpLockedPct")}
    sources.record("rugcheck", True, f"score {out['rc_score']}, {out['rc_danger']} risque(s) danger")
    return out
