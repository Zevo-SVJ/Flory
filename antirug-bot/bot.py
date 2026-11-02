# bot.py
# Anti-Rug, the paid Telegram bot: paste a token address, get the desk's rug checks in seconds.
# its own Telegram bot and its own process, apart from the desk (rug-desk/tgbot.py stays the desk's).
#
# setup, once, on the Mac:
#   1. Telegram -> @BotFather -> /newbot (a NEW bot, not the desk's) -> copy its token
#   2. cd ~/Documents/rug-desk-run/antirug-bot && read -rs T && echo "ANTIRUG_BOT_TOKEN=$T" >> .env && chmod 600 .env
#   3. python3 bot.py            (a Terminal tab of its own, left open)
#   4. in Telegram, send /owner <the code printed at start> to your new bot: that chat gets /stats
# antirug-bot/.env, optional: ANTIRUG_DAILY_CAP=500  ANTIRUG_PER_HOUR=50  TG_FREE_PER_DAY=3  TG_PRO_STARS=500
import csv, hashlib, json, os, random, re, sys, threading, time
import local                                    # puts ../rug-desk on the path, reads antirug-bot/.env
import requests
import tgpro, texts

API = "https://api.telegram.org/bot{}/{}"
STATE = os.path.join(local.DATA, "bot.json")
USAGE = os.path.join(local.DATA, "usage.csv")
CA = re.compile(r"\b0x[0-9a-fA-F]{40}\b|\b[1-9A-HJ-NP-Za-km-z]{32,44}\b")


def token() -> str | None:
    return local.get("ANTIRUG_BOT_TOKEN")


def _state() -> dict:
    try:
        with open(STATE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(s: dict):
    os.makedirs(local.DATA, exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(s, f)
    os.replace(tmp, STATE)


def owner() -> str | None:
    return local.get("ANTIRUG_OWNER") or _state().get("owner")


def owner_code() -> str:
    s = _state()
    if not s.get("code"):
        s["code"] = f"{random.SystemRandom().randrange(10**6):06d}"
        _save(s)
    return s["code"]


def call(method: str, **params):
    r = requests.post(API.format(token(), method), json=params, timeout=30)
    return r.json() if r.ok else {"ok": False, "description": r.text[:200]}


def send(chat: int, msg: str):
    call("sendMessage", chat_id=chat, text=msg[:4000], disable_web_page_preview=True)


def log_use(user: int, mint: str, result: str, lang: str):
    os.makedirs(local.DATA, exist_ok=True)
    new = not os.path.exists(USAGE)
    with open(USAGE, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "user", "mint", "result", "lang", "pro"])
        # who asked is kept as a short hash: enough to count people and returns, not to know them
        w.writerow([round(time.time()), hashlib.sha1(str(user).encode()).hexdigest()[:10], mint, result, lang,
                    int(tgpro.is_pro(user))])


def usage_stats() -> dict:
    try:
        with open(USAGE, newline="") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        rows = []
    now = time.time()
    day0 = time.mktime(time.strptime(time.strftime("%Y-%m-%d"), "%Y-%m-%d"))
    week = [r for r in rows if float(r["time"]) > now - 7 * 86400]
    days = {}
    for r in week:
        days.setdefault(r["user"], set()).add(time.strftime("%Y-%m-%d", time.localtime(float(r["time"]))))
    return {"today": sum(1 for r in rows if float(r["time"]) >= day0), "checks_7d": len(week),
            "users_7d": len(days), "returning_7d": sum(1 for d in days.values() if len(d) >= 2),
            "users_all": len({r["user"] for r in rows})}


def render(mint: str, r: dict, lang: str) -> str:
    """The desk's verdict (tgbot.verdict), written in the user's language."""
    import tgbot, chains
    t = texts.S[lang]
    v = tgbot.verdict(r)
    labels = tgbot.LABELS if lang == "fr" else texts.EN
    notes = tgbot.NOTES if lang == "fr" else texts.NOTES_EN
    lines = [f"${r['symbol']} · {t['head'][v]}"]
    k = r.get("key") or mint
    if chains.is_evm(k):
        lines.append(t["chain"].format(chains.split(k)[0]))
    lines += ["• " + (labels.get(f) or f.replace("danger:", "Token-2022: ")) for f in r["flags"]]
    c, facts_ = r["context"], []
    if c.get("liq"):
        facts_.append(t["pool"].format(f"{c['liq'] / 1000:.0f}"))
    if c.get("age_min") is not None:
        a = c["age_min"]
        facts_.append(t["age_m"].format(f"{a:.0f}") if a < 120 else t["age_h"].format(f"{a / 60:.0f}")
                      if a < 72 * 60 else t["age_d"].format(f"{a / 1440:.0f}"))
    if c.get("top10") is not None:
        facts_.append(t["top10"].format(f"{c['top10']:.0f}"))
    if facts_:
        lines.append(" · ".join(facts_))
    if c.get("notes"):
        lines.append(t["notes"] + " ; ".join(notes[f] for f in c["notes"]))
    if v == "green":
        lines.append(t["green_note"])
    lines.append(chains.link(k).replace("https://", ""))
    return "\n".join(lines)


_recent: dict = {}


def check(chat: int, user: int, body: str, lang: str):
    t = texts.S[lang]
    mints = list(dict.fromkeys(CA.findall(body)))[:3]
    if not mints:
        send(chat, t["start"].format(free=tgpro.free_per_day()))
        return
    now = time.time()
    _recent[user] = [x for x in _recent.get(user, []) if now - x < 3600]
    per_hour = local.num("ANTIRUG_PER_HOUR", 50)
    for mint in mints:
        if not tgpro.allow(user, owner()):
            send(chat, t["quota"].format(free=tgpro.free_per_day(), days=tgpro.days()))
            return
        if len(_recent[user]) >= per_hour:
            send(chat, t["rate"].format(n=per_hour))
            return
        if usage_stats()["today"] >= local.num("ANTIRUG_DAILY_CAP", 500):
            send(chat, t["cap"])
            return
        _recent[user].append(now)
        import tgbot
        try:
            r = tgbot.inspect(mint)                # the desk's checks, read-only (tgbot.py is not changed)
            msg = render(mint, r, lang)
            result = tgbot.verdict(r)
        except Exception as e:
            msg, result = t["error"].format(ca=mint[:6], e=str(e)[:80]), "error"
        tgpro.count(user)
        if result != "error" and not tgpro.is_pro(user) and str(user) != str(owner()):
            msg += t["left"].format(n=max(0, tgpro.free_per_day() - tgpro.used_today(user)))
        send(chat, msg)
        log_use(user, mint, result, lang)


def handle(update: dict):
    if (q := update.get("pre_checkout_query")):           # Telegram asks before taking the Stars: say yes
        call("answerPreCheckoutQuery", pre_checkout_query_id=q["id"], ok=True)
        return
    m = update.get("message") or {}
    chat = (m.get("chat") or {}).get("id")
    frm = m.get("from") or {}
    user = frm.get("id") or chat
    lang = texts.lang(frm.get("language_code"))
    t = texts.S[lang]
    if not chat:
        return
    if (p := m.get("successful_payment")):
        until = tgpro.grant(user, p.get("telegram_payment_charge_id", ""), int(p.get("total_amount") or 0))
        send(chat, t["thanks"].format(until=time.strftime("%d/%m/%Y", time.localtime(until))))
        if owner():
            send(int(owner()), f"💰 Pro payé : {p.get('total_amount')} Stars · {tgpro.stats()['pro_now']} Pro actifs")
        return
    body = (m.get("text") or "").strip()
    if not body:
        return
    cmd = body.split()[0].split("@")[0].lower()
    if cmd == "/owner" and body.split()[-1] == owner_code():
        s = _state()
        s["owner"] = str(chat)
        _save(s)
        send(chat, "Ce chat est maintenant le propriétaire : /stats, et les paiements te sont signalés.")
    elif cmd == "/stats" and str(chat) == str(owner()):
        u, p = usage_stats(), tgpro.stats()
        send(chat, f"Aujourd'hui : {u['today']} lectures\n7 jours : {u['checks_7d']} lectures, {u['users_7d']} "
                   f"utilisateurs, {u['returning_7d']} revenus un autre jour\nTotal : {u['users_all']} utilisateurs\n"
                   f"Pro actifs : {p['pro_now']} · paiements : {p['payments']} · Stars : {p['stars']} "
                   f"(30 j : {p['stars_30d']})")
    elif cmd in ("/start", "/help", "/aide"):
        send(chat, t["start"].format(free=tgpro.free_per_day()))
    elif cmd == "/pro":
        r = call("sendInvoice", chat_id=chat, **tgpro.invoice(lang))
        if not r.get("ok"):
            send(chat, "Paiement indisponible pour le moment." if lang == "fr" else "Payment unavailable right now.")
    elif cmd in ("/status", "/statut"):
        if tgpro.is_pro(user):
            send(chat, t["status_pro"].format(until=time.strftime("%d/%m/%Y", time.localtime(tgpro.pro_until(user)))))
        else:
            send(chat, t["status_free"].format(used=tgpro.used_today(user), free=tgpro.free_per_day()))
    elif cmd == "/terms":
        send(chat, t["terms"].format(days=tgpro.days()))
    elif cmd == "/paysupport":
        _state_support = _state()
        _state_support.setdefault("support", []).append({"t": round(time.time()), "chat": chat})
        _save(_state_support)
        send(chat, t["support"])
    else:
        s = _state()
        recent_support = [x for x in s.get("support", []) if x["chat"] == chat and time.time() - x["t"] < 3600]
        if recent_support and not CA.search(body) and owner():
            send(int(owner()), f"📩 /paysupport de {chat} : {body[:500]}")
            s["support"] = [x for x in s["support"] if x not in recent_support]
            _save(s)
            send(chat, t["support_ok"])
            return
        check(chat, user, body, lang)


COMMANDS = {"fr": [("start", "Comment ça marche"), ("pro", "Lectures illimitées"), ("status", "Mon abonnement"),
                   ("terms", "Conditions"), ("paysupport", "Problème de paiement")],
            "en": [("start", "How it works"), ("pro", "Unlimited checks"), ("status", "My plan"),
                   ("terms", "Terms"), ("paysupport", "Payment issue")]}


def setup():
    """The command menu in both languages."""
    for lang, cmds in COMMANDS.items():
        params = {"commands": [{"command": c, "description": d} for c, d in cmds]}
        if lang == "fr":
            params["language_code"] = "fr"
        call("setMyCommands", **params)


def loop(stop: threading.Event | None = None):
    stop = stop or threading.Event()
    while not stop.is_set():
        try:
            r = requests.get(API.format(token(), "getUpdates"), timeout=65,
                             params={"timeout": 50, "offset": _state().get("offset"),
                                     "allowed_updates": '["message","pre_checkout_query"]'})
            r.raise_for_status()
            for u in r.json().get("result") or []:
                s = _state()
                s["offset"] = u["update_id"] + 1
                _save(s)                               # saved before handling: a crash never answers twice
                try:
                    handle(u)
                except Exception as e:
                    print(f"[{time.strftime('%H:%M:%S')}] erreur : {str(e)[:200]}", flush=True)
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Telegram injoignable ({str(e)[:100]}), nouvel essai dans 15 s", flush=True)
            stop.wait(15)


if __name__ == "__main__":
    if len(sys.argv) > 1:                               # python3 bot.py <CA> [en]: the answer, without Telegram
        import tgbot
        print(render(sys.argv[1], tgbot.inspect(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "fr"))
        sys.exit(0)
    if not token():
        print("pas de ANTIRUG_BOT_TOKEN dans antirug-bot/.env : voir l'en-tête de bot.py")
        sys.exit(1)
    setup()
    print(f"Anti-Rug en route. Pour devenir propriétaire, envoie au bot : /owner {owner_code()}\nCtrl+C pour arrêter.",
          flush=True)
    try:
        loop()
    except KeyboardInterrupt:
        pass
