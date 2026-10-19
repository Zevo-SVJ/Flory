# run.py
# start the desk:  python3 run.py      stop it: Ctrl+C. state lives in data/, so restarting is safe.
# the work itself is split between agents: see agents.py.
from agents import main
from events import emit
from notify import post

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        emit("DESK", "info", "Claude Bot stopped")
        post("CLAUDE BOT stopped.")
