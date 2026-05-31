#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
SCHEDULE="${SCHEDULE:-* * * * *}"
CRON_LINE="$SCHEDULE cd $APP_DIR && set -a && . ./.env && set +a && flock -n /tmp/x-watch.lock $PYTHON_BIN src/x_watch.py >> x-watch.log 2>&1"
CRON_LINE_30="$SCHEDULE sleep 30; cd $APP_DIR && set -a && . ./.env && set +a && flock -n /tmp/x-watch.lock $PYTHON_BIN src/x_watch.py >> x-watch.log 2>&1"

if ! command -v crontab >/dev/null 2>&1; then
  echo "crontab is not available on this VPS"
  exit 1
fi

tmp_file="$(mktemp)"
crontab -l 2>/dev/null | grep -v "src/x_watch.py" | grep -v "watch_x.py" > "$tmp_file" || true
printf "%s\n" "$CRON_LINE" >> "$tmp_file"
printf "%s\n" "$CRON_LINE_30" >> "$tmp_file"
crontab "$tmp_file"
rm -f "$tmp_file"

echo "Installed cron job:"
echo "$CRON_LINE"
echo "$CRON_LINE_30"
