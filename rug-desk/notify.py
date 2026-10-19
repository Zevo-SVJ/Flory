# notify.py
# where the desk "posts". always the terminal and data/desk.log.
# optional: a free Telegram bot, so alerts reach your phone. put both values in .env:
#   TELEGRAM_BOT_TOKEN=...   (from @BotFather)
#   TELEGRAM_CHAT_ID=...     (optional: or send the bot "/lier <code>", the code is in GARDE's panel)
import os, time
import requests
from config import DATA
import env


def post(text: str):
    stamp = time.strftime("%Y-%m-%d %H:%M")
    print(f"[{stamp}] {text}", flush=True)
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "desk.log"), "a") as f:
        f.write(f"[{stamp}] {text}\n")
    import tgbot                     # TELEGRAM_CHAT_ID in .env, or the chat paired with /lier in the bot
    token, chat = env.get("TELEGRAM_BOT_TOKEN"), tgbot.owner()
    if token and chat:
        try:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          json={"chat_id": chat, "text": text[:4000]}, timeout=15)
        except Exception as e:
            print(f"telegram down: {e}", flush=True)
