#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile src/x_watch.py src/damai_watch.py
bash -n scripts/run_loop.sh
bash -n scripts/install_x_cron.sh
bash -n scripts/install_damai_cron.sh

if grep -RInE 'sctp[[:alnum:]]+|OPENAI_API_KEY|sk-[[:alnum:]]|_m_h5_tk=[[:alnum:]]|3347133198@qq.com' \
  --exclude-dir=.git \
  --exclude=check.sh \
  .; then
  echo "Potential secret or private identifier found." >&2
  exit 1
fi

echo "All checks passed."
