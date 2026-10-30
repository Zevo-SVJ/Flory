# atomic.py
# a temp-file name no other thread or process can share. the desk's threads (VIGIE, the Telegram bot),
# its backtest child and, by mistake, a second desk all write the same state files: with one shared
# "x.tmp" a writer renamed another's file away and the desk crashed (Oct 19, two desks running)
import os, threading


def tmp(path: str) -> str:
    return f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
