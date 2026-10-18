# run.py
# the free replacement for Grok Bot routines. one process, three jobs, one log.
#   watch  every 10 min: silent unless an exit fires
#   scan   every 30 min: posts only PASS/BUY verdicts; a source that's down is said once
#   report daily at 21:30
# start it:  python run.py          stop it: Ctrl+C. state lives in data/, so restarting is safe.
import time, traceback
from config import SCHEDULE, PAPER, JUDGE
from notify import post
import watch, scan, report


def main():
    post(f"RUG DESK up. {'PAPER' if PAPER else 'LIVE'} mode, judge={JUDGE}. "
         f"watch every {SCHEDULE['watch_every_min']}m, scan every {SCHEDULE['scan_every_min']}m, "
         f"report at {SCHEDULE['report_at']}.")
    next_watch = next_scan = 0.0
    reported_on = None
    down = set()                       # sources already reported down, so we say it once

    while True:
        now = time.time()
        try:
            if now >= next_watch:
                next_watch = now + SCHEDULE["watch_every_min"] * 60
                for e in watch.watch():
                    post(e)

            if now >= next_scan:
                next_scan = now + SCHEDULE["scan_every_min"] * 60
                try:
                    results = scan.scan()
                    down.discard("dexscreener-profiles")
                except Exception as e:
                    if "dexscreener-profiles" not in down:
                        post(f"lead source down (DexScreener profiles): {e}")
                        down.add("dexscreener-profiles")
                    results = []
                for v in results:
                    reason = v.get("reason") or ""
                    for src in ("facts", "dexscreener", "grok"):
                        if reason.startswith(f"{src} failed"):
                            if src not in down:
                                post(f"{src} is down, skipping its tokens: {reason}")
                                down.add(src)
                            break
                    else:
                        if v["stage"] in ("facts", "pool"):
                            down.discard("facts")
                        if v["stage"] == "pool":
                            down.discard("dexscreener")
                    if v["verdict"] in ("BUY", "PASS"):
                        post(f"{v['verdict']} {v.get('symbol')} conf={v.get('confidence', '-')} "
                             f"x_read={v.get('x_read', 'none')} {v.get('url', '')}\n"
                             f"X by CA: {v.get('x_ca')}\nX by ticker: {v.get('x_ticker')}\n"
                             f"{v.get('action', '')}")

            today = time.strftime("%Y-%m-%d")
            if time.strftime("%H:%M") >= SCHEDULE["report_at"] and reported_on != today:
                reported_on = today
                post(report.report())
        except Exception:
            post("desk error, will retry next tick:\n" + traceback.format_exc(limit=3))
        time.sleep(30)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        post("RUG DESK stopped.")
