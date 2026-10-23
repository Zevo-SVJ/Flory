# env.py
# reads .env next to the desk. secrets never live in config.py or in a chat.
import os
from config import HERE


def get(name: str) -> str | None:
    if os.environ.get(name):
        return os.environ[name]
    path = os.path.join(HERE, ".env")
    if os.path.exists(path):
        for line in open(path):
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"') or None
    return None
