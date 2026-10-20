# gt.py
# GeckoTerminal without a key allows about 10 calls a minute, per IP, shared by everything on the Mac:
# the desk (SCOUT's trending and new pools) and the backtest child (its candles). past that, everyone
# gets 429 and SCOUT goes blind on the momentum lane and the EVM chains: what happened on Oct 20 at
# 03:42, the backtest child taking 20 calls a minute. one budget for all processes, in a file:
# SCOUT's live reads come first, the backtest only takes what is left and waits for the rest.
import fcntl, json, os, time
import requests
from config import DATA

BUDGET = 9                  # calls per rolling minute, every process together (10 is the wall)
BACKGROUND = 4              # the backtest never takes more: SCOUT always has 5 a minute
COOL_S = 60                 # one 429 and nobody calls for a minute
FILE = os.path.join(DATA, "gt_calls.json")


def _slot(background: bool, wait_max: float) -> bool:
    deadline = time.time() + wait_max
    os.makedirs(DATA, exist_ok=True)
    while True:
        with open(FILE + ".lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                with open(FILE) as f:
                    st = json.load(f)
            except (OSError, ValueError):
                st = {}
            now = time.time()
            calls = [c for c in st.get("calls", []) if now - c[0] < 60]
            free = (now >= st.get("cool", 0) and len(calls) < BUDGET
                    and (not background or sum(1 for c in calls if c[1]) < BACKGROUND))
            if free:
                calls.append([now, background])
            with open(FILE, "w") as f:
                json.dump({"calls": calls, "cool": st.get("cool", 0)}, f)
        if free:
            return True
        if time.time() >= deadline:
            return False
        time.sleep(3 if background else 1)


def cool(seconds: float = COOL_S):
    with open(FILE + ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            with open(FILE) as f:
                st = json.load(f)
        except (OSError, ValueError):
            st = {}
        st["cool"] = max(st.get("cool", 0), time.time() + seconds)
        with open(FILE, "w") as f:
            json.dump(st, f)


def get(url: str, params: dict | None = None, background: bool = False, wait_max: float | None = None,
        timeout: float = 15):
    """requests.get on GeckoTerminal inside the shared budget. Raises if no slot frees up in time."""
    if wait_max is None:
        wait_max = 300 if background else 30
    if not _slot(background, wait_max):
        raise RuntimeError("budget GeckoTerminal de la minute pris (10 appels/min sans clé) : réessai au prochain passage")
    r = requests.get(url, params=params, headers={"accept": "application/json"}, timeout=timeout)
    if r.status_code == 429:
        cool()
    return r


def state() -> dict:
    try:
        with open(FILE) as f:
            st = json.load(f)
    except (OSError, ValueError):
        return {"last_min": 0, "cooling": False}
    now = time.time()
    return {"last_min": sum(1 for c in st.get("calls", []) if now - c[0] < 60), "cooling": now < st.get("cool", 0)}
