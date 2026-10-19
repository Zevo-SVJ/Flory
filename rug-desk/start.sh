#!/bin/bash
# start.sh: the desk and its dashboard, kept alive all night.
#   - each one restarts by itself 10 s after a crash (state lives in data/, so a restart is safe)
#   - the Mac stays awake while this runs (caffeinate), as long as the lid is open and it is on power
#   - if the dashboard can't start, the reason is printed here, not hidden
#   - Ctrl+C stops everything
# run it:  cd ~/Documents/rug-desk-run/rug-desk && ./start.sh
cd "$(dirname "$0")" || exit 1
mkdir -p data
trap 'echo; echo "stopping the desk..."; kill 0' INT TERM EXIT

command -v caffeinate > /dev/null && caffeinate -ims -w $$ &

# a dashboard or desk left over from an older terminal would hold the port or run twice
if lsof -nP -iTCP:8765 -sTCP:LISTEN > /dev/null 2>&1; then
  echo "port 8765 already taken by an old process, stopping it:"
  lsof -nP -iTCP:8765 -sTCP:LISTEN | tail -n +2
  kill $(lsof -t -iTCP:8765 -sTCP:LISTEN) 2> /dev/null; sleep 1
fi
pkill -f "^python3 run\.py$" 2> /dev/null && echo "an old desk was still running: stopped" && sleep 1

keep_alive() {   # name, script
  while true; do
    echo "[$(date '+%Y-%m-%d %H:%M')] $1 starting" | tee -a data/supervisor.log
    python3 "$2" >> "data/$1.out" 2>&1
    code=$?
    echo "[$(date '+%Y-%m-%d %H:%M')] $1 stopped (code $code), restarting in 10 s. last lines:" | tee -a data/supervisor.log
    tail -n 8 "data/$1.out"
    sleep 10
  done
}

keep_alive dashboard dashboard.py &
( sleep 4
  if curl -s -o /dev/null http://localhost:8765/; then
    echo ">>> dashboard OK: http://localhost:8765"
  else
    echo ">>> dashboard NOT reachable. its last lines:"; tail -n 15 data/dashboard.out
  fi ) &
keep_alive desk run.py &
tail -n 0 -F data/desk.out
