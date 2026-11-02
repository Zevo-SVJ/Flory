# tgpro.py
# the anti-rug bot as a product: a free tier that shows what it does, a Pro pass paid in Telegram Stars.
# Stars are Telegram's own currency for digital goods in bots (no card processor, no KYC on our side): the
# user pays inside Telegram, the bot gets a successful_payment, the pass runs PRO_DAYS from then.
#   .env (all optional): TG_FREE_PER_DAY=3   TG_PRO_STARS=500   TG_PRO_DAYS=30
# Telegram requires a bot that takes payments to answer /paysupport and to show its terms (/terms).
import json, os, time
from config import DATA
import atomic, env

FILE = os.path.join(DATA, "tgpro.json")       # {user id: {"until": epoch, "paid": [charges]}, "_used": {...}}


def _cfg(k: str, d: int) -> int:
    try:
        return int(env.get(k) or d)
    except ValueError:
        return d


def free_per_day() -> int:
    return _cfg("TG_FREE_PER_DAY", 3)


def price() -> int:
    return _cfg("TG_PRO_STARS", 500)


def days() -> int:
    return _cfg("TG_PRO_DAYS", 30)


def _load() -> dict:
    try:
        with open(FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(s: dict):
    os.makedirs(DATA, exist_ok=True)
    tmp = atomic.tmp(FILE)
    with open(tmp, "w") as f:
        json.dump(s, f)
    os.replace(tmp, FILE)


def pro_until(user: int | str) -> float:
    return float((_load().get(str(user)) or {}).get("until") or 0)


def is_pro(user: int | str) -> bool:
    return pro_until(user) > time.time()


def used_today(user: int | str) -> int:
    u = (_load().get("_used") or {}).get(str(user)) or {}
    return u.get("n", 0) if u.get("day") == time.strftime("%Y-%m-%d") else 0


def allow(user: int | str, owner: str | None) -> bool:
    """Can this user run one more check now? the owner and Pro users always; others free_per_day a day."""
    if owner and str(user) == str(owner):
        return True
    return is_pro(user) or used_today(user) < free_per_day()


def count(user: int | str):
    s = _load()
    used = s.setdefault("_used", {})
    today = time.strftime("%Y-%m-%d")
    u = used.get(str(user)) or {}
    used[str(user)] = {"day": today, "n": (u.get("n", 0) if u.get("day") == today else 0) + 1}
    _save(s)


def grant(user: int | str, charge_id: str, stars: int) -> float:
    """A paid pass: PRO_DAYS from now, or from the end of the current one. Returns the new end."""
    s = _load()
    u = s.setdefault(str(user), {})
    start = max(time.time(), float(u.get("until") or 0))
    u["until"] = start + days() * 86400
    u.setdefault("paid", []).append({"t": round(time.time()), "charge": charge_id, "stars": stars})
    _save(s)
    return u["until"]


def stats() -> dict:
    s = _load()
    now = time.time()
    users = {k: v for k, v in s.items() if not k.startswith("_")}
    paid = [p for v in users.values() for p in v.get("paid", [])]
    return {"pro_now": sum(1 for v in users.values() if float(v.get("until") or 0) > now),
            "payments": len(paid), "stars": sum(p.get("stars", 0) for p in paid),
            "stars_30d": sum(p.get("stars", 0) for p in paid if now - p["t"] < 30 * 86400)}


def invoice(lang: str) -> dict:
    """sendInvoice parameters for one Pro pass (currency XTR = Telegram Stars, no provider token)."""
    fr = lang == "fr"
    return {"title": "Anti-Rug Pro" + (f" · {days()} jours" if fr else f" · {days()} days"),
            "description": (f"Lectures illimitées pendant {days()} jours (50 par heure au plus). "
                            "Contrat, holders, bundles, liquidité, sur 7 chaînes." if fr else
                            f"Unlimited checks for {days()} days (50 an hour at most). "
                            "Contract, holders, bundles, liquidity, on 7 chains."),
            "payload": f"pro{days()}", "currency": "XTR",
            "prices": [{"label": f"Pro {days()} j" if fr else f"Pro {days()} d", "amount": price()}]}
