#!/usr/bin/env bash
set -euo pipefail

X_INTERVAL_SECONDS="${X_INTERVAL_SECONDS:-30}"
DAMAI_INTERVAL_SECONDS="${DAMAI_INTERVAL_SECONDS:-15}"
ENABLE_X_WATCH="${ENABLE_X_WATCH:-1}"
ENABLE_DAMAI_WATCH="${ENABLE_DAMAI_WATCH:-1}"

run_forever() {
  local name="$1"
  local interval="$2"
  shift 2

  while true; do
    echo "[$(date -Is)] running $name"
    "$@" || true
    sleep "$interval"
  done
}

children=()

if [[ "$ENABLE_X_WATCH" == "1" ]]; then
  run_forever "x-watch" "$X_INTERVAL_SECONDS" python3 src/x_watch.py &
  children+=("$!")
fi

if [[ "$ENABLE_DAMAI_WATCH" == "1" ]]; then
  run_forever "damai-watch" "$DAMAI_INTERVAL_SECONDS" python3 src/damai_watch.py &
  children+=("$!")
fi

if [[ "${#children[@]}" -eq 0 ]]; then
  echo "No monitor enabled. Set ENABLE_X_WATCH=1 or ENABLE_DAMAI_WATCH=1."
  exit 1
fi

wait "${children[@]}"
