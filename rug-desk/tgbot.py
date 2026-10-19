# tgbot.py
# GARDE as a product: a Telegram bot that answers "is this token a rug factory?" for any Solana CA.
# the one part of the desk with a value shown on data (AUDIT: most tokens it kills do crash), offered to
# other traders. it reads, it never trades: no book, no paper buy, no memory written, Solana Tracker's
# daily cap left to the desk.
#
# setup (2 minutes): Telegram -> @BotFather -> /newbot -> copy the token, then on the Mac:
#   read -rs T && echo "TELEGRAM_BOT_TOKEN=$T" >> .env && chmod 600 .env
# the desk starts the bot by itself when the token is there. optional in .env:
#   TELEGRAM_DAILY_CAP=200      checks a day for everyone together (each one costs RPC calls)
#   TELEGRAM_ALLOW=123,456      chat ids allowed; empty = anyone who finds the bot
import atomic
import csv, hashlib, json, os, random, re, threading, time
import requests
from config import DATA
import env

API = "https://api.telegram.org/bot{}/{}"
STATE = os.path.join(DATA, "tgbot.json")
LOG = os.path.join(DATA, "tgbot.csv")
CA = re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b")
PER_CHAT_HOUR = 15

LABELS = {
    "mint_open": "le créateur peut encore imprimer des tokens (mint authority ouverte)",
    "freeze_open": "le créateur peut geler ton wallet (freeze authority ouverte)",
    "lp_unlocked": "la liquidité n'est pas brûlée : elle peut être retirée",
    "dev_holds": "le dev garde plus de 5 % de l'offre",
    "dev_rugged_before": "ce dev a déjà un token effondré (liste noire)",
    "top10_heavy": "le top 10 des holders détient trop de l'offre",
    "whale": "un seul wallet détient plus de 5 %",
    "bundle_same_sol": "bundle : des holders avec exactement le même solde SOL",
    "bundle_ladder": "bundle : des sacs de tokens identiques",
    "holder_farm": "ferme de wallets : des centaines de sacs identiques",
    "fake_cap": "capitalisation gonflée face à une liquidité minuscule",
    "micro_trades": "volume de bots : trades moyens de quelques dollars",
    "nobody_can_sell": "honeypot probable : des achats, aucune vente",
    "serial_farm": "nom recyclé par une usine à rugs (homonymes morts)",
    "copycat": "copie d'un ticker plus gros et actif",
    "factory_wallets": "des wallets connus d'usines à rugs détiennent ce token",
    "jup_sus": "Jupiter le marque comme suspect",
    "serial_dev": "dev lanceur en série (des dizaines de tokens)",
    "inorganic_volume": "volume non organique selon Jupiter",
    "low_organic": "score organique Jupiter bas",
    "rug_funder": "les holders ont été financés par un wallet déjà lié à un rug",
    "funded_cluster": "un même wallet a financé une grosse part des holders",
    "fresh_wallets": "les holders sont surtout des wallets neufs",
    "lp_unverified": "liquidité non vérifiable",
    "dev_unknown": "créateur introuvable",
    "no_holders": "holders illisibles",
}
UNKNOWN = {"lp_unverified", "dev_unknown", "no_holders"}
# on a token a week old or more these say little: its liquidity sits in many pools and on exchanges, and
# exchange wallets hold big bags (BONK read as "fake cap" and "whale" on its best pool alone). noted, not red
CONTEXTUAL = {"fake_cap", "whale", "top10_heavy"}
ESTABLISHED_MIN = 7 * 24 * 60
NOTES = {"fake_cap": "capitalisation très au-dessus de la liquidité de son plus gros pool",
         "whale": "un wallet détient plus de 5 % (souvent un exchange)",
         "top10_heavy": "top 10 concentré (souvent des exchanges)"}

HELP = ("Colle l'adresse (CA) d'un token Solana : je lis la chaîne, les holders, qui les a financés, "
        "Jupiter, et je te dis si ça ressemble à une usine à rug.\n\n"
        "Lecture automatique, elle peut se tromper. Ce n'est pas un conseil financier.")


def token() -> str | None:
    return env.get("TELEGRAM_BOT_TOKEN")


def inspect(mint: str) -> dict:
    """Every rug signal the desk knows for one token, whatever its market looks like today.
    returns {symbol, flags: [codes], context: {...}}: the desk's own checks, run read-only."""
    import market, facts, check
    from score import score
    m = market.pool(mint)
    flags = []
    if m:
        k = market.market_kill(m)
        if k in LABELS:
            flags.append(k)
        try:
            c = market.copycat(m, mint)
        except Exception:
            c = None
        if c:
            flags.append(c)
    t = facts.report(mint, m or {})
    k = facts.fact_kill(t, market.lane(m) if m else "early")
    if k:
        flags.append(k)
    deep = check.deep_read(mint, t, desk=False)
    if deep["kill"]:
        flags.append(deep["kill"])
    d = deep["logged"]
    ctx = {"liq": (m or {}).get("liq_usd"), "age_min": (m or {}).get("age_min"), "mcap": (m or {}).get("mcap"),
           "top10": t.get("top10_pct"), "holders": t.get("holders"), "cluster": d.get("cluster_pct"),
           "fresh": d.get("fresh_pct"), "organic": d.get("organic"), "score": score(m, t)["score"] if m else None}
    flags = list(dict.fromkeys(flags))
    if (ctx["age_min"] or 0) >= ESTABLISHED_MIN:
        ctx["notes"] = [f for f in flags if f in CONTEXTUAL]
        flags = [f for f in flags if f not in CONTEXTUAL]
    return {"symbol": (m or {}).get("symbol") or t.get("symbol") or mint[:6], "flags": flags, "context": ctx}


def verdict(r: dict) -> str:
    danger = [f for f in r["flags"] if f not in UNKNOWN]
    if danger:
        return "red"
    return "yellow" if r["flags"] else "green"


def text(mint: str, r: dict) -> str:
    v = verdict(r)
    head = {"red": "🔴 RISQUE ÉLEVÉ", "yellow": "🟡 INCERTAIN", "green": "🟢 aucun signal d'usine à rug détecté"}[v]
    lines = [f"${r['symbol']} · {head}"]
    lines += ["• " + (LABELS.get(f) or f.replace("danger:", "piège Token-2022 : ")) for f in r["flags"]]
    c = r["context"]
    facts_ = []
    if c.get("liq"):
        facts_.append(f"pool {c['liq'] / 1000:.0f} k$")
    if c.get("age_min") is not None:
        a = c["age_min"]
        facts_.append(f"âge {a:.0f} min" if a < 120 else f"âge {a / 60:.0f} h" if a < 72 * 60 else f"âge {a / 1440:.0f} j")
    if c.get("top10") is not None:
        facts_.append(f"top 10 {c['top10']:.0f} %")
    if c.get("cluster"):
        facts_.append(f"cluster financé {float(c['cluster']):.0f} %")
    if c.get("fresh"):
        facts_.append(f"wallets neufs {float(c['fresh']):.0f} %")
    if c.get("organic") is not None:
        facts_.append(f"organique {c['organic']:.0f}")
    if facts_:
        lines.append(" · ".join(facts_))
    if c.get("notes"):
        lines.append("À savoir (token établi, pas un signal de rug) : " + " ; ".join(NOTES[f] for f in c["notes"]))
    if v == "green":
        lines.append("Pas de piège trouvé : ça ne dit rien du prix de demain.")
    lines.append(f"dexscreener.com/solana/{mint}")
    return "\n".join(lines)


def _state() -> dict:
    try:
        with open(STATE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(s: dict):
    os.makedirs(DATA, exist_ok=True)
    tmp = atomic.tmp(STATE)
    with open(tmp, "w") as f:
        json.dump(s, f)
    os.replace(tmp, STATE)


def owner() -> str | None:
    """The chat that gets the desk's alerts and whose CAs GARDE checks as leads: TELEGRAM_CHAT_ID in .env,
    or the chat that sent the pairing code shown in the dashboard."""
    return env.get("TELEGRAM_CHAT_ID") or _state().get("owner")


def pair_code() -> str:
    """Six digits shown in GARDE's panel. Sending /lier <code> to the bot makes that chat the owner:
    only someone who can see the dashboard (you, on the Mac) can pair."""
    s = _state()
    if not s.get("pair_code"):
        s["pair_code"] = f"{random.SystemRandom().randrange(10**6):06d}"
        _save(s)
    return s["pair_code"]


def _log(chat: int, mint: str, result: str):
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "user", "mint", "result"])
        # who asked is kept as a short hash: enough to count users, not to know them
        w.writerow([round(time.time()), hashlib.sha1(str(chat).encode()).hexdigest()[:10], mint, result])


def stats() -> dict:
    """For the dashboard: is the bot on, how many checks today, how many people in 7 days."""
    out = {"on": bool(token()), "today": 0, "users_7d": 0, "checks_7d": 0, "paired": bool(owner()),
           "code": pair_code() if token() and not owner() else None}
    try:
        with open(LOG, newline="") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return out
    day0 = time.mktime(time.strptime(time.strftime("%Y-%m-%d"), "%Y-%m-%d"))
    week = [r for r in rows if float(r["time"]) > time.time() - 7 * 86400]
    days = {}                                # the product test: people who came back another day
    for r in week:
        days.setdefault(r["user"], set()).add(time.strftime("%Y-%m-%d", time.localtime(float(r["time"]))))
    out.update(today=sum(1 for r in rows if float(r["time"]) >= day0), checks_7d=len(week),
               users_7d=len(days), returning_7d=sum(1 for d in days.values() if len(d) >= 2))
    return out


def send(tok: str, chat: int, msg: str):
    requests.post(API.format(tok, "sendMessage"), timeout=20,
                  json={"chat_id": chat, "text": msg[:4000], "disable_web_page_preview": True})


_recent = {}       # chat -> times of its last checks


def handle(tok: str, message: dict):
    chat = (message.get("chat") or {}).get("id")
    body = (message.get("text") or "").strip()
    if not chat or not body:
        return
    allow = [a.strip() for a in (env.get("TELEGRAM_ALLOW") or "").split(",") if a.strip()]
    if allow and str(chat) not in allow:
        return
    if body.startswith("/lier"):
        if body.split()[-1] == pair_code():
            s = _state()
            s["owner"] = str(chat)
            _save(s)
            send(tok, chat, "Lié. Ce chat reçoit maintenant les alertes du desk (achats, ventes, rapports), "
                            "et chaque CA que tu envoies passe aussi par GARDE dans le desk.")
        else:
            send(tok, chat, "Code incorrect. Le bon code est affiché dans le panneau GARDE du tableau de bord.")
        return
    if body.startswith("/etat") and str(chat) == owner():     # the chief of staff: five lines, the last hour
        import report
        h = body.split()[-1]
        send(tok, chat, report.status(float(h) if h.replace(".", "", 1).isdigit() else 1))
        return
    mints = list(dict.fromkeys(CA.findall(body)))[:3]
    if body.startswith("/") or not mints:
        send(tok, chat, HELP)
        return
    now = time.time()
    _recent[chat] = [t for t in _recent.get(chat, []) if now - t < 3600]
    if len(_recent[chat]) >= PER_CHAT_HOUR:
        send(tok, chat, f"Limite atteinte : {PER_CHAT_HOUR} lectures par heure. Réessaie plus tard.")
        return
    cap = int(env.get("TELEGRAM_DAILY_CAP") or 200)
    if stats()["today"] >= cap:
        send(tok, chat, "Le bot a atteint sa limite du jour. Réessaie demain.")
        return
    if str(chat) == owner():                 # your CAs are leads for the desk too: GARDE checks, may paper-buy
        import agents
        with open(agents.INBOX, "a") as f:
            f.writelines(m + "\n" for m in mints)
    for mint in mints:
        _recent[chat].append(now)
        try:
            r = inspect(mint)
            send(tok, chat, text(mint, r))
            _log(chat, mint, verdict(r))
        except Exception as e:
            send(tok, chat, f"{mint[:6]}… : lecture impossible ({str(e)[:80]}). Est-ce bien un token Solana ?")
            _log(chat, mint, "error")


def loop(stop: threading.Event):
    """Long polling: one open request at a time, no server, no port to open on the Mac."""
    tok = token()
    if not tok:
        return
    while not stop.is_set():
        try:
            r = requests.get(API.format(tok, "getUpdates"), timeout=65,
                             params={"timeout": 50, "offset": _state().get("offset"), "allowed_updates": '["message"]'})
            r.raise_for_status()
            for u in r.json().get("result") or []:
                # read, change one key, write: the dashboard writes the pairing code into the same file, and
                # a copy kept across the loop wiped it (Oct 19: every /lier answered "code incorrect")
                st = _state()
                st["offset"] = u["update_id"] + 1
                _save(st)                      # saved before handling: a crash never answers twice
                try:
                    handle(tok, u.get("message") or {})
                except Exception:
                    pass
        except Exception:
            stop.wait(15)


def start(stop: threading.Event) -> threading.Thread | None:
    if not token():
        return None
    th = threading.Thread(target=loop, args=(stop,), name="TGBOT", daemon=True)
    th.start()
    return th


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:                       # python3 tgbot.py <CA>: the answer the bot would send
        print(text(sys.argv[1], inspect(sys.argv[1])))
    else:
        print("bot running, Ctrl-C to stop" if token() else "no TELEGRAM_BOT_TOKEN in .env")
        loop(threading.Event())
