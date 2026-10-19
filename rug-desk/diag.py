# diag.py
# why did the desk buy nothing? every stage of the last hours, from the desk's own files, in one page.
#   python3 diag.py        (last 6 h)      python3 diag.py 24      (last 24 h)
# reads only: no network call, nothing written.
import csv, json, os, sys, time
from collections import Counter
from config import LOG, TRADES, EVENTS, DATA, MIN_SCORE, DAILY_LOSS_HALT_USD, FACTS
import book

H = float(sys.argv[1]) if len(sys.argv) > 1 else 6
since = time.time() - H * 3600
cut = time.strftime("%Y-%m-%d %H:%M", time.localtime(since))


def rows(path):
    try:
        with open(path, newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


print(f"== les {H:.0f} dernières heures (depuis {cut})")

# SCOUT: how many leads reached GARDE, run by run
ev = []
try:
    with open(EVENTS) as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("t", 0) >= since:
                ev.append(e)
except OSError:
    pass
scans = [e for e in ev if e.get("agent") == "SCOUT" and e.get("kind") == "scan"]
handed = sum(int(e["text"].split(" token")[0]) for e in scans if e["text"][:1].isdigit())
print(f"SCOUT : {len(scans)} passages, {handed} token(s) envoyés à GARDE")
errs = Counter(e["text"][:90] for e in ev if e.get("kind") == "error")
for t, n in errs.most_common(5):
    print(f"  erreur x{n} : {t}")

# GARDE: every verdict, by stage and reason
ch = [r for r in rows(LOG) if r["time"] >= cut]
print(f"GARDE : {len(ch)} verdict(s)")
for (stage, reason), n in Counter((r["stage"], r["reason"]) for r in ch if r["verdict"] == "SKIP").most_common(15):
    print(f"  {n:3d} x {stage:7s} {reason}")
passes = [r for r in ch if r["verdict"] in ("PASS", "BUY")]
low = [r for r in passes if r.get("score") and int(float(r["score"])) < MIN_SCORE]
print(f"  PASS : {len(passes)}, dont {len(low)} sous la note minimale {MIN_SCORE} (non achetés)")
for r in passes:
    print(f"     {r['time']} ${r['symbol']} note {r.get('score')} {r.get('flags') or ''}")

# holders: where they were read from (no_holders was the big killer)
nh = sum(1 for r in ch if r["reason"] == "no_holders")
print(f"  holders illisibles : {nh}/{len(ch)}")
try:
    src = json.load(open(os.path.join(DATA, "sources.json")))
    for k in ("helius_das", "goplus", "jupiter", "stracker"):
        if k in src:
            s = src[k]
            print(f"  source {k}: {'OK' if s.get('ok') else 'EN PANNE'} il y a {(time.time() - s['t']) / 60:.0f} min · {s.get('detail', '')[:70]}")
except (OSError, ValueError):
    pass
import facts
print(f"  RPC : {'Helius' if 'helius' in facts.RPC_URL else 'PUBLIC (pas de Helius dans .env)'}")

# the book's limits: one of them blocks every buy when it trips
b = book.load()
print(f"LIMITES : perte du jour {book.today_pnl():+.2f} $ (arrêt à -{DAILY_LOSS_HALT_USD}) · "
      f"{len(b)} position(s) ouverte(s) · cash {book.cash(b):.0f} $")
tr = [t for t in rows(TRADES) if t["time"] >= cut]
print(f"ACHATS : {sum(1 for t in tr if t['action'] == 'open')} · ventes : {sum(1 for t in tr if t['action'] != 'open')}")
print(f"RÈGLES D'ENTRÉE : âge min {FACTS['min_age_min']} min, pool min {FACTS['min_liquidity_usd']} $, "
      f"top 10 max {FACTS['max_top10_pct']} %, prix >= {FACTS.get('min_vs_graduation')} x graduation")
