#!/usr/bin/env bash
# scripts/run_in_screen.sh
#
# Runs the web shipment suite inside a single canonical `screen` session on the
# remote Linux test-runner machine. This script is intended to be started from
# the project root with either:
#
#   bash scripts/run_in_screen.sh --suite web_shipment
#   ./scripts/run_in_screen.sh --suite web_shipment
#
# It does not require a manual ``chmod +x`` step because it self-heals its own
# executable bit before launching the detached screen session.

set -uo pipefail

SCREEN_NAME="web-test"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_PATH="$PROJECT_DIR/scripts/run_in_screen.sh"
cd "$PROJECT_DIR"

# Ensure the launcher is executable even on a fresh clone, so users do not need
# to remember a separate chmod step before running the project from the repo root.
chmod +x "$SCRIPT_PATH" 2>/dev/null || true

VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
if [ ! -x "$VENV_PYTHON" ]; then
    VENV_PYTHON="python3"
fi

mkdir -p logs/web
STAMP="$(date +%Y%m%d_%H%M%S)"
RUNNER_LOG="logs/web/runner_${STAMP}.log"

# Preserve argument quoting exactly as passed by the caller so expressions like
# --markers "network or storage" survive the round trip to the inner bash -lc.
ESCAPED_ARGS=()
for arg in "$@"; do
    ESCAPED_ARGS+=("$(printf '%q' "$arg")")
done
COMMAND_STRING="'${VENV_PYTHON}' run_tests.py ${ESCAPED_ARGS[*]}"

printf '%s\n' "==> Starting Bryck web test runner from ${PROJECT_DIR}"
printf '%s\n' "==> Target command: ${COMMAND_STRING}"
printf '%s\n' "==> Runner log   : ${RUNNER_LOG}"

echo "==> Checking for an existing '${SCREEN_NAME}' screen session..."
EXISTING="$(screen -ls 2>/dev/null | grep -oE "[0-9]+\.${SCREEN_NAME}[[:space:]]" | awk '{print $1}' || true)"
if [ -n "$EXISTING" ]; then
    echo "    Found existing session(s) - killing by exact pid.name to avoid ambiguity:"
    while IFS= read -r pidname; do
        [ -z "$pidname" ] && continue
        echo "      quitting ${pidname}"
        screen -S "$pidname" -X quit >/dev/null 2>&1 || true
        pid="${pidname%%.*}"
        if kill -0 "$pid" >/dev/null 2>&1; then
            kill -9 "$pid" >/dev/null 2>&1 || true
        fi
    done <<< "$EXISTING"
    sleep 1
    screen -wipe >/dev/null 2>&1 || true
fi

echo "==> Starting the suite in a new detached screen session named '${SCREEN_NAME}'"
echo "    Attach      : screen -r ${SCREEN_NAME}   (Ctrl+A then D to detach)"
echo "    Tail        : tail -f ${RUNNER_LOG}"

screen -dmS "$SCREEN_NAME" bash -lc "cd '$PROJECT_DIR' && exec ${COMMAND_STRING} 2>&1 | tee '$RUNNER_LOG'"
sleep 1

if screen -ls 2>/dev/null | grep -q "\.${SCREEN_NAME}[[:space:]]"; then
    echo "==> Session started."
else
    echo "==> WARNING: could not confirm the screen session started - check 'screen -ls' manually."
fi

printf '%s\n' "==> Detailed execution output is being streamed to the log file above."
printf '%s\n' "==> When ready, attach with: screen -r ${SCREEN_NAME}"
