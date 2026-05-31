#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
SCHEDULE="${SCHEDULE:-* * * * *}"
CRON_LINE="$SCHEDULE cd $APP_DIR && set -a && . ./.env && set +a && flock -n /tmp/damai-watch.lock bash -c 'for i in {1..4}; do $PYTHON_BIN src/damai_watch.py >> damai-watch.log 2>&1; sleep 15; done'"

tmp_file="$(mktemp)"
crontab -l 2>/dev/null | grep -v "src/damai_watch.py" | grep -v "damai_watch.py" > "$tmp_file" || true
printf "%s\n" "$CRON_LINE" >> "$tmp_file"
crontab "$tmp_file"
rm -f "$tmp_file"

echo "Installed Damai cron job:"
echo "$CRON_LINE"
