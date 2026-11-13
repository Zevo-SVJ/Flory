# local.py
# where this bot lives: its own folder, its own .env and data. the desk's code (../rug-desk) is imported
# read-only for the analysis; the desk's data (its blacklist of rug devs, its known factory wallets) is
# read through it, and nothing of the desk is changed.
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DESK = os.environ.get("RUG_DESK_DIR") or os.path.join(os.path.dirname(HERE), "rug-desk")
DATA = os.environ.get("ANTIRUG_DATA") or os.path.join(HERE, "data")
if DESK not in sys.path:
    sys.path.insert(0, DESK)


def get(name: str) -> str | None:
    """This bot's settings: the environment, then antirug-bot/.env (never the desk's .env)."""
    if os.environ.get(name):
        return os.environ[name]
    path = os.path.join(HERE, ".env")
    if os.path.exists(path):
        for line in open(path):
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"') or None
    return None


def num(name: str, default: int) -> int:
    try:
        return int(get(name) or default)
    except ValueError:
        return default
