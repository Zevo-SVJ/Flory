# health.py
# did the desk really run all night? two kinds of hole, both written to data/pauses.csv:
#   - the main loop sleeps 1 s between turns. a turn that took minutes of wall time means the Mac slept
#   - at start, the last heartbeat says how long the desk was not running at all (stopped or crashed)
# macOS also keeps its own sleep log (pmset), read here so the reason is named, not guessed.
import json, os, subprocess, sys, time
from config import DATA

GAP_S = 120          # a 1 s sleep that lasted 2 min: the machine was not running us
PAUSES = os.path.join(DATA, "pauses.csv")


def record(start: float, end: float, kind: str):
    """kind: "sleep" (the process was frozen) or "stopped" (it was not running)."""
    os.makedirs(DATA, exist_ok=True)
    new = not os.path.exists(PAUSES)
    with open(PAUSES, "a") as f:
        if new:
            f.write("start,end,kind\n")
        f.write(f"{start:.0f},{end:.0f},{kind}\n")


def since_last_run() -> float | None:
    """At start: when the previous run last beat, if that was more than GAP_S ago."""
    try:
        with open(os.path.join(DATA, "heartbeat.json")) as f:
            t = json.load(f)["time"]
    except (OSError, ValueError, KeyError):
        return None
    return t if time.time() - t > GAP_S else None


def gaps(hours: float = 24) -> list[tuple[float, float, str]]:
    """(start, end, kind) of every pause that ended in the last N hours."""
    if not os.path.exists(PAUSES):
        return []
    since, out = time.time() - hours * 3600, []
    with open(PAUSES) as f:
        next(f, None)
        for line in f:
            try:
                a, b, kind = line.strip().split(",")
                a, b = float(a), float(b)
            except ValueError:
                continue
            if b >= since:
                out.append((a, b, kind))
    return out


def equity_holes(hours: float = 24, min_s: float = 300) -> list[tuple[float, float]]:
    """Holes of 5 min+ in the balance log (one point per VIGIE tick, ~20 s). Covers nights from
    before pauses.csv existed. A long SCOUT run can make a short one, so only 5 min+ count."""
    from config import EQUITY
    if not os.path.exists(EQUITY):
        return []
    since, out, prev = time.time() - hours * 3600, [], None
    with open(EQUITY) as f:
        next(f, None)
        for line in f:
            try:
                t = float(line.split(",", 1)[0])
            except ValueError:
                continue
            if t >= since and prev and t - prev > min_s:
                out.append((prev, t))
            prev = t
    return out


def mac_sleeps(hours: float = 24) -> list[str]:
    """Sleep and wake lines from macOS's own power log. Empty off a Mac."""
    if sys.platform != "darwin":
        return []
    try:
        log = subprocess.run(["pmset", "-g", "log"], capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return []
    since = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - hours * 3600))
    keep = []
    for line in log.splitlines():
        if line[:16] >= since and any(f" {k} " in line[19:45] for k in ("Sleep", "Wake", "DarkWake")):
            keep.append(" ".join(line.split()[:2])[:16] + " " + " ".join(line.split()[3:])[:110])
    return keep[-12:]


def summary(hours: float = 24) -> str | None:
    """One line for the journal, or None if the desk ran without a hole."""
    g = gaps(hours) or [(a, b, "hole") for a, b in equity_holes(hours)]
    sleeps = [s for s in mac_sleeps(hours) if " Sleep " in f" {s} "]
    if not g and not sleeps:
        return None
    if not g:
        return f"desk sans trou, mais macOS a noté {len(sleeps)} mise(s) en veille (dernière {sleeps[-1][:16]})"
    total = sum(b - a for a, b, _ in g) / 60
    worst = max(g, key=lambda x: x[1] - x[0])
    stopped = sum(1 for *_, k in g if k == "stopped")
    fmt = lambda t: time.strftime("%H:%M", time.localtime(t))
    why = (f"macOS dit : mise en veille ({len(sleeps)}x, dernière {sleeps[-1][:16]})" if sleeps
           else "aucune veille dans le journal macOS")
    if stopped:
        why += f", {stopped} arrêt(s) du desk lui-même"
    return (f"{len(g)} pause(s) sur {hours:.0f} h, {total:.0f} min au total, la plus longue "
            f"{fmt(worst[0])}→{fmt(worst[1])}. {why}")


if __name__ == "__main__":
    print(summary() or "aucune pause sur 24 h : le desk a tourné sans trou")
    for a, b, kind in gaps():
        print(time.strftime("%m-%d %H:%M", time.localtime(a)), "→", time.strftime("%H:%M", time.localtime(b)),
              f"({(b - a) / 60:.0f} min, {kind})")
    for a, b in equity_holes():
        print("trou dans le graphique:", time.strftime("%m-%d %H:%M", time.localtime(a)), "→",
              time.strftime("%H:%M", time.localtime(b)), f"({(b - a) / 60:.0f} min)")
    for s in mac_sleeps():
        print("macOS:", s)
