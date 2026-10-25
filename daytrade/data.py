# data.py
# SPY minute bars from Alpaca (free data plan), cached by month in data/bars/. regular session only.
#   python3 data.py fetch 2016-01-01 2026-10-23
import csv, json, os, sys, time
import datetime as dt
from zoneinfo import ZoneInfo
from config import DATA, SYMBOL, TZ

URL = "https://data.alpaca.markets/v2/stocks/bars"
BARS = os.path.join(DATA, "bars")
ET = ZoneInfo(TZ)
FIELDS = ["t", "o", "h", "l", "c", "v", "vw"]


def env(name: str) -> str | None:
    if os.environ.get(name):
        return os.environ[name]
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(path):
        for line in open(path):
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"') or None
    return None


def _get(params: dict) -> dict:
    import requests
    for attempt in range(5):
        r = requests.get(URL, params=params, timeout=30, headers={
            "APCA-API-KEY-ID": env("ALPACA_KEY_ID") or "", "APCA-API-SECRET-KEY": env("ALPACA_SECRET_KEY") or ""})
        if r.status_code == 429:
            time.sleep(2 + 3 * attempt)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("Alpaca: too many 429s")


def session(t_utc: str) -> tuple[str, int] | None:
    """(ET date, minute since 09:30) for a regular-session bar, else None."""
    t = dt.datetime.fromisoformat(t_utc.replace("Z", "+00:00")).astimezone(ET)
    m = (t.hour * 60 + t.minute) - (9 * 60 + 30)
    return (t.date().isoformat(), m) if 0 <= m < 390 else None


def fetch_month(year: int, month: int, feed: str = "sip") -> int:
    start = dt.date(year, month, 1)
    end = dt.date(year + (month == 12), month % 12 + 1, 1)
    rows, token = [], None
    while True:
        p = {"symbols": SYMBOL, "timeframe": "1Min", "start": f"{start}T00:00:00Z", "end": f"{end}T00:00:00Z",
             "limit": 10000, "adjustment": "all", "feed": feed, "sort": "asc"}
        if token:
            p["page_token"] = token
        j = _get(p)
        for b in (j.get("bars") or {}).get(SYMBOL, []):
            if session(b["t"]):
                rows.append({k: b.get(k) for k in FIELDS})
        token = j.get("next_page_token")
        if not token:
            break
    if rows:
        os.makedirs(BARS, exist_ok=True)
        with open(os.path.join(BARS, f"{SYMBOL}_{year}-{month:02d}.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
    return len(rows)


def fetch(start: str, end: str):
    d, last = dt.date.fromisoformat(start).replace(day=1), dt.date.fromisoformat(end)
    while d <= last:
        path = os.path.join(BARS, f"{SYMBOL}_{d.year}-{d.month:02d}.csv")
        current = d.year == last.year and d.month == last.month
        if not os.path.exists(path) or current:          # past months are cached for good
            n = fetch_month(d.year, d.month)
            print(f"{d.year}-{d.month:02d}: {n} bars", flush=True)
        d = dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1)


def days(start: str | None = None, end: str | None = None) -> list[tuple[str, list[dict]]]:
    """[(date, bars)] in order; each bar {m, o, h, l, c, v, vw} with m = minute since 09:30."""
    by = {}
    if not os.path.isdir(BARS):
        return []
    for name in sorted(os.listdir(BARS)):
        if not name.endswith(".csv"):
            continue
        with open(os.path.join(BARS, name), newline="") as f:
            for r in csv.DictReader(f):
                s = session(r["t"])
                if not s:
                    continue
                day, m = s
                if (start and day < start) or (end and day > end):
                    continue
                v = float(r["v"] or 0)
                c = float(r["c"])
                by.setdefault(day, []).append({"m": m, "o": float(r["o"]), "h": float(r["h"]), "l": float(r["l"]),
                                               "c": c, "v": v, "vw": float(r["vw"] or c)})
    return [(d, sorted(b, key=lambda x: x["m"])) for d, b in sorted(by.items())]


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "fetch":
        fetch(sys.argv[2], sys.argv[3])
    else:
        print("usage: python3 data.py fetch START END   (dates YYYY-MM-DD)")
