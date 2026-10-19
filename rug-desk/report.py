# report.py
# the evening report. everything in it comes from checks.csv and trades.csv, nothing from memory.
import csv, json, os, time
from collections import Counter
from config import LOG, PAPER, JUDGE
import book, audit


def report() -> str:
    day = time.strftime("%Y-%m-%d")
    checks = []
    if os.path.exists(LOG):
        with open(LOG, newline="") as f:
            checks = [r for r in csv.DictReader(f) if r["time"].startswith(day)]
    done = [t for t in book.trades() if t["time"].startswith(day) and t["action"] != "open"]

    by_stage = Counter(r["stage"] for r in checks if r["verdict"] == "SKIP")
    passed = [r for r in checks if r["verdict"] in ("BUY", "PASS")]
    wins = [t for t in done if float(t["pnl"]) > 0]
    reasons = Counter(r["reason"] for r in checks if r["stage"] in ("facts", "pool"))

    lines = [f"EVENING REPORT {day} {'(PAPER)' if PAPER else '(LIVE)'} judge={JUDGE}",
             f"checked: {len(checks)}",
             f"killed by rug filter: {by_stage['facts']} | by pool: {by_stage['pool']} | "
             f"by judge: {by_stage['judge']} | by limits: {by_stage['limits']}",
             f"passed: {len(passed)} | open now: {len(book.load())}",
             f"realized pnl today: ${book.today_pnl():+.2f}"]
    if done:
        lines.append(f"green exits: {len(wins)}/{len(done)}")
        best = max(done, key=lambda t: float(t["pnl"]))
        worst = min(done, key=lambda t: float(t["pnl"]))
        lines.append(f"best: {best['symbol']} ${float(best['pnl']):+.2f} | "
                     f"worst: {worst['symbol']} ${float(worst['pnl']):+.2f}")
    for reason, n in reasons.most_common(3):
        lines.append(f"kill reason: {reason} ({n}x)")
    # the article's two closing lines: one thing that worked, one number to question. from data, not taste
    stats = audit.by_reason()
    if stats:
        best = max(stats, key=lambda o: o["crashed"] / o["n"])
        lines.append(f"worked: '{best['reason']}' killed {best['n']} audited tokens, "
                     f"{best['crashed']} of them crashed below {audit.CRASH_PCT}% within hours")
        worst = max(stats, key=lambda o: o["ran"] / o["n"])
        if worst["ran"] / worst["n"] >= 0.3:
            lines.append(f"question: {audit.KNOB.get(worst['reason'], worst['reason'])} in config.py: "
                         f"'{worst['reason']}' killed {worst['n']} tokens and {worst['ran']} still did +100%. "
                         f"look at them before you move it, and write down why")
    lab = {}
    lab_path = os.path.join(os.path.dirname(LOG), "exitlab.json")
    if os.path.exists(lab_path):
        with open(lab_path) as f:
            lab = json.load(f)
    if lab.get("trades"):
        top = lab["results"][0]
        act = next(r for r in lab["results"] if r["name"] == "actif")
        lines.append(f"exit lab on {lab['trades']} trades: best '{top['name']}' {top['pnl']:+.2f}$, "
                     f"active profile '{lab['active']}' {act['pnl']:+.2f}$")
    a = audit.summary()
    up, down = a["regime"]["SOL up"], a["regime"]["SOL down"]
    if up["n"] or down["n"]:
        lines.append(f"regime: passes crashed {up['crashed']}/{up['n']} with SOL up over 24h, "
                     f"{down['crashed']}/{down['n']} with SOL down")
    xb, xs = a["x"]["BUY"], a["x"]["SKIP"]
    if xb["n"] or xs["n"]:
        lines.append(f"ECHO: {xs['crashed']}/{xs['n']} tokens it skipped crashed later, "
                     f"{xb['crashed']}/{xb['n']} it approved crashed later")
    k, p = a["killed"], a["passed"]
    if k["n"] or p["n"]:
        lines.append(f"audit: {k['crashed']}/{k['n']} killed tokens crashed later, "
                     f"{p['crashed']}/{p['n']} passed tokens crashed later")
    return "\n".join(lines)


if __name__ == "__main__":
    print(report())
