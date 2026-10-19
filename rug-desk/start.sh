#!/bin/bash
# start.sh: the desk and its dashboard, kept alive all night.
#   - each one restarts by itself 10 s after a crash (state lives in data/, so a restart is safe)
#   - the Mac stays awake while this runs (caffeinate), as long as the lid is open and it is on power
#   - Ctrl+C stops everything
# run it:  cd ~/Documents/rug-desk-run/rug-desk && ./start.sh
cd "$(dirname "$0")" || exit 1
mkdir -p data
trap 'echo; echo "stopping the desk..."; kill 0' INT TERM EXIT

caffeinate -ims -w $$ &

keep_alive() {   # name, script
  while true; do
    echo "[$(date '+%Y-%m-%d %H:%M')] $1 starting" | tee -a data/supervisor.log
    python3 "$2" 2>&1 | tee -a "data/$1.out"
    echo "[$(date '+%Y-%m-%d %H:%M')] $1 stopped (code ${PIPESTATUS[0]}), restarting in 10 s" | tee -a data/supervisor.log
    sleep 10
  done
}

keep_alive dashboard dashboard.py > /dev/null &
echo "dashboard: http://localhost:8765"
keep_alive desk run.py
