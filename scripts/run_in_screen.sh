#!/usr/bin/env bash
# scripts/run_in_screen.sh
#
# Runs the web shipment suite inside a single, canonical `screen` session on
# the remote Linux test-runner machine. Meant to be triggered either directly
# on that machine, or remotely via `python scripts/remote_control.py trigger`.
#
# Behavior:
#   1. Looks for an existing "web-test" screen session and kills it first, so
#      re-triggering a run never piles up duplicate/zombie sessions.
#   2. Starts a brand-new detached session that runs `run_tests.py` (which
#      itself archives the previous run's results/logs/screenshots/traces
#      before doing anything else - see web_shipment/services/allure_report.py).
#   3. Tees all console output to logs/web/runner_<timestamp>.log so you can
#      `tail -f` it even without attaching to screen, and so it survives even
#      if the session is later wiped.
#   4. The session exits naturally when the run completes (no `exec bash`
#      keeping it alive) - `screen -ls` simply won't show it anymore.
#
# Usage:
#   ./scripts/run_in_screen.sh                       # default markers=shipment
#   ./scripts/run_in_screen.sh --markers "shipment and network"
#
# Monitor:
#   screen -r web-test          # attach (Ctrl+A then D to detach)
#   tail -f logs/web/runner_*.log

set -uo pipefail

SCREEN_NAME="web-test"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
if [ ! -x "$VENV_PYTHON" ]; then
    VENV_PYTHON="python3"
fi

mkdir -p logs/web
STAMP="$(date +%Y%m%d_%H%M%S)"
RUNNER_LOG="logs/web/runner_${STAMP}.log"

echo "==> Checking for an existing '${SCREEN_NAME}' screen session..."
EXISTING="$(screen -ls 2>/dev/null | grep -oE "[0-9]+\.${SCREEN_NAME}[[:space:]]" | awk '{print $1}' || true)"
if [ -n "$EXISTING" ]; then
    echo "    Found existing session(s) - killing by exact pid.name to avoid ambiguity:"
    while IFS= read -r pidname; do
        [ -z "$pidname" ] && continue
        echo "      quitting ${pidname}"
        screen -S "$pidname" -X quit >/dev/null 2>&1 || true
        # Force-kill if the process is still alive after -X quit.
        pid="${pidname%%.*}"
        if kill -0 "$pid" >/dev/null 2>&1; then
            kill -9 "$pid" >/dev/null 2>&1 || true
        fi
    done <<< "$EXISTING"
    sleep 1
    screen -wipe >/dev/null 2>&1 || true
fi

echo "==> Starting the suite in a new detached screen session named '${SCREEN_NAME}'"
echo "    Console log : ${RUNNER_LOG}"
echo "    Attach      : screen -r ${SCREEN_NAME}   (Ctrl+A then D to detach)"
echo "    Tail        : tail -f ${RUNNER_LOG}"

screen -dmS "$SCREEN_NAME" bash -c "'${VENV_PYTHON}' run_tests.py $* 2>&1 | tee '${RUNNER_LOG}'; echo; echo RUN_DONE"
sleep 1

if screen -ls 2>/dev/null | grep -q "\.${SCREEN_NAME}[[:space:]]"; then
    echo "==> Session started."
else
    echo "==> WARNING: could not confirm the screen session started - check 'screen -ls' manually."
fi
