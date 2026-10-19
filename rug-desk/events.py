# events.py
# the desk's shared memory between agents and the dashboard: one line per thing that happened.
import json, os, threading, time
from config import DATA, EVENTS, AGENTS

_LOCK = threading.Lock()      # VIGIE has its own thread: one writer at a time on these two files


def emit(agent: str, kind: str, text: str, **extra) -> dict:
    """kind: scan, kill, pass, buy, sell, x, audit, report, error, info"""
    os.makedirs(DATA, exist_ok=True)
    e = {"id": time.time_ns(), "t": time.time(), "agent": agent, "kind": kind, "text": text, **extra}
    with _LOCK, open(EVENTS, "a") as f:
        f.write(json.dumps(e) + "\n")
    return e


def recent(n: int = 40, after: int = 0) -> list[dict]:
    """The last n events, newest first. Reads only the tail, so a week of events stays cheap."""
    if not os.path.exists(EVENTS):
        return []
    with open(EVENTS, "rb") as f:
        f.seek(0, 2)
        size = f.seek(max(0, f.tell() - 200_000))
        lines = f.read().decode(errors="ignore").splitlines()[1 if size else 0:]
    out = []
    for line in reversed(lines):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e["id"] <= after:
            break
        out.append(e)
        if len(out) >= n:
            break
    return out


def count() -> int:
    if not os.path.exists(EVENTS):
        return 0
    with open(EVENTS, "rb") as f:
        return sum(1 for _ in f)


def set_agent(name: str, **fields):
    """Each agent's live status: what it's doing, when it last ran, how often it failed."""
    os.makedirs(DATA, exist_ok=True)
    with _LOCK:
        state = agents()
        a = state.setdefault(name, {"runs": 0, "errors": 0})
        a.update(fields)
        a["t"] = time.time()
        tmp = AGENTS + f".{threading.get_ident()}.tmp"
        with open(tmp, "w") as f:
            json.dump(state, f)
        os.replace(tmp, AGENTS)


def agents() -> dict:
    if not os.path.exists(AGENTS):
        return {}
    try:
        with open(AGENTS) as f:
            return json.load(f)
    except ValueError:
        return {}
