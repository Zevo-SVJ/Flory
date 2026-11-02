# posts.py
# drafts for X, from what the desk's anti-rug engine really did: every token it flagged is re-priced 6 h later
# (rug-desk/data/audit.csv). nothing is posted: you read, pick, post yourself. numbers are what the file says,
# with their denominators, and the examples are real tokens with the reason they were flagged.
#   python3 posts.py          last 24 h        python3 posts.py 168      last 7 days
import csv, sys, time
import local                                    # ../rug-desk on the path
import texts

def rows(hours: float) -> list[dict]:
    import config
    try:
        with open(config.AUDIT, newline="") as f:
            rs = list(csv.DictReader(f))
    except OSError:
        return []
    cut = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - hours * 3600))
    return [r for r in rs if r["time"] >= cut]


# reasons a reader feels at once, shown first in the examples: a trap, a dev or a bundle, not "unverified"
STRONG = ["danger:honeypot", "nobody_can_sell", "danger:high_tax", "danger:cannot_sell_all", "dev_rugged_before",
          "serial_farm", "factory_wallets", "rug_funder", "bundle_same_sol", "bundle_ladder", "holder_farm",
          "dev_holds", "mint_open", "freeze_open", "lp_unlocked", "whale", "top10_heavy", "copycat", "fake_cap"]


def link() -> str:
    """t.me/<the bot>, from Telegram (getMe) with the bot's token, or ANTIRUG_BOT_LINK in .env."""
    if local.get("ANTIRUG_BOT_LINK"):
        return local.get("ANTIRUG_BOT_LINK")
    tok = local.get("ANTIRUG_BOT_TOKEN")
    if tok:
        try:
            import requests
            u = requests.get(f"https://api.telegram.org/bot{tok}/getMe", timeout=10).json()["result"]["username"]
            return f"t.me/{u}"
        except Exception:
            pass
    return ""


def label(reason: str, lang: str) -> str:
    import tgbot
    return (tgbot.LABELS if lang == "fr" else texts.EN).get(reason) or reason


def drafts(hours: float = 24) -> dict[str, list[str]]:
    rs = rows(hours)
    killed = []
    for r in rs:
        try:
            ch = float(r["change_pct"])
        except (TypeError, ValueError):
            continue
        if r["verdict"] == "SKIP" and " failed" not in (r["reason"] or "") and r["reason"] in texts.EN:
            killed.append((ch, r))
    seen = set()                                                    # one line per token: its latest verdict
    killed = [(ch, r) for ch, r in sorted(killed, key=lambda x: x[1]["time"], reverse=True)
              if not (r["mint"] in seen or seen.add(r["mint"]))]
    moved = [(ch, r) for ch, r in killed if abs(ch) >= 1]           # still traded: a price that moved
    rank = lambda r: STRONG.index(r["reason"]) if r["reason"] in STRONG else len(STRONG)
    crashed = sorted([(ch, r) for ch, r in moved if ch <= -50], key=lambda x: (rank(x[1]), x[0]))
    span = {"fr": "ces dernières 24 h" if hours <= 24 else f"ces {hours / 24:.0f} derniers jours",
            "en": "in the last 24h" if hours <= 24 else f"in the last {hours / 24:.0f} days"}
    out = {"fr": [], "en": []}
    if not moved:
        return out
    share = 100 * len(crashed) / len(moved)
    ex, syms = [], set()                                             # three different tickers
    for ch, r in crashed:
        if r["symbol"] not in syms:
            ex.append((ch, r))
            syms.add(r["symbol"])
        if len(ex) == 3:
            break
    url = link()
    for lang in ("fr", "en"):
        lines = [f"${r['symbol']} {ch:+.0f}%" + (" · " if lang == "en" else " · ") + label(r["reason"], lang)
                 for ch, r in ex]
        if lang == "fr":
            out[lang].append(f"Mon bot anti-rug a signalé {len(killed)} tokens {span[lang]}.\n\n"
                             f"Sur les {len(moved)} qui tradaient encore, {len(crashed)} ont perdu plus de 50 % "
                             f"dans les 6 h ({share:.0f} %).\n\nQuelques-uns :\n" + "\n".join(lines) +
                             "\n\nColle n'importe quel CA, réponse en quelques secondes 👇")
            if ex:
                ch, r = ex[0]
                out[lang].append(f"${r['symbol']} : signalé par le bot pour « {label(r['reason'], lang)} ».\n\n"
                                 f"6 h plus tard : {ch:+.0f} %.\n\nAvant d'acheter un memecoin, 5 secondes de vérif.")
        else:
            out[lang].append(f"My anti-rug bot flagged {len(killed)} tokens {span[lang]}.\n\n"
                             f"Of the {len(moved)} still trading, {len(crashed)} lost 50%+ within 6h "
                             f"({share:.0f}%).\n\nA few:\n" + "\n".join(lines) +
                             "\n\nPaste any CA, answer in seconds 👇" + (f"\n{url}" if url else ""))
            if ex:
                ch, r = ex[0]
                out[lang].append(f"${r['symbol']} got flagged by the bot: {label(r['reason'], lang)}.\n\n"
                                 f"6h later: {ch:+.0f}%.\n\nBefore you ape a memecoin, 5 seconds of checking."
                                 + (f"\n{url}" if url else ""))
    return out


if __name__ == "__main__":
    h = float(sys.argv[1]) if len(sys.argv) > 1 else 24
    d = drafts(h)
    if not d["en"]:
        print("pas encore de données sur cette période (rug-desk/data/audit.csv)")
    for i, p in enumerate(d["en"], 1):                  # English only: X's memecoin crowd reads English
        print(f"===== draft {i} ({len(p)} characters)\n{p}\n")
