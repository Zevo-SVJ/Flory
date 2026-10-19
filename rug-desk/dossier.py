# dossier.py
# one file per token that went past SCOUT: every agent writes what it saw, in order, and reads what the
# others wrote. the shared context between agents (the blackboard): ECHO reads why GARDE bought, VIGIE's
# sale and AUDIT's 6 h price land next to the checks that let the token in, and the dashboard shows the
# whole story of a token on one page. a fact here is what an agent measured or read, never an order:
# an ECHO reason quoted from X stays a quote.
import json, os, threading, time
from config import DATA

DIR = os.path.join(DATA, "dossiers")
_LOCK = threading.Lock()
KEEP = 40          # entries per token at most (VIGIE writes only sales, so this is plenty)


def add(mint: str, agent: str, what: str, **facts):
    """Append one entry. Never raises: a dossier is a record, not a reason to stop an agent."""
    try:
        os.makedirs(DIR, exist_ok=True)
        path = os.path.join(DIR, f"{mint}.json")
        with _LOCK:
            d = load(mint)
            d["mint"] = mint
            d.setdefault("entries", []).append({"t": time.time(), "agent": agent, "what": what,
                                                **{k: v for k, v in facts.items() if v not in (None, "", [])}})
            d["entries"] = d["entries"][-KEEP:]
            tmp = path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(d, f)
            os.replace(tmp, path)
    except Exception:
        pass


def load(mint: str) -> dict:
    try:
        with open(os.path.join(DIR, f"{mint}.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"mint": mint, "entries": []}


def last(mint: str, agent: str) -> dict | None:
    return next((e for e in reversed(load(mint)["entries"]) if e["agent"] == agent), None)


def brief(mint: str) -> str:
    """GARDE's case for a token in one line, for ECHO's queue: what the code saw, so the X read can
    confirm or contradict it instead of starting blind."""
    g, s = {}, {}
    for e in load(mint)["entries"]:          # everything each agent said, the latest value winning
        {"GARDE": g, "SCOUT": s}.get(e["agent"], {}).update(e)
    parts = [f"source {s['source']}" if s.get("source") else None,
             f"voie {g['lane']}" if g.get("lane") else None,
             f"note {g['score']}" if g.get("score") is not None else None,
             f"mise {g['tier']}" if g.get("tier") else None,
             ("signaux " + "/".join(g["signals"])) if g.get("signals") else None,
             f"organique {g['organic']:.0f}" if isinstance(g.get("organic"), (int, float)) else None,
             f"cluster {g['cluster_pct']}%" if g.get("cluster_pct") else None,
             f"wallets neufs {g['fresh_pct']}%" if g.get("fresh_pct") else None]
    return " · ".join(p for p in parts if p)
