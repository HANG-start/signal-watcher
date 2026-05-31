# Signal Watcher

[![CI](https://github.com/HANG939/signal-watcher/actions/workflows/ci.yml/badge.svg)](https://github.com/HANG939/signal-watcher/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Signal Watcher is a lightweight monitoring toolkit for VPS deployments.

It currently includes:

- Twitter/X post monitoring through public RSS mirrors or the official X API
- Damai project status monitoring for ticket availability signals
- WeChat notifications through ServerChan, plus WeCom, Telegram, or generic webhook support
- Cron and Docker deployment examples

The project is designed for personal reminders. It does not include credential scraping, captcha bypassing, or automatic paid order submission.

## Use Cases

- Follow public posts from a Twitter/X account and receive near-real-time notifications.
- Watch a Damai project page for public status changes and ticket availability signals.
- Run low-cost monitors on a VPS with cron, Docker, or a process supervisor.
- Build custom signal monitors using the existing notification and state-file patterns.

## How It Works

### Twitter/X

`src/x_watch.py` checks a target account and stores the latest seen post id in `.state/x-watch.json`.

Default mode uses RSS mirrors, so it can run without paying for X API access. RSS mirrors may occasionally fail or lag, so the script tries multiple sources and rejects known block/placeholder feeds.

Set `SOURCE_MODE=api` and `X_BEARER_TOKEN` if you want to use the official X API instead.

### Damai

`src/damai_watch.py` calls Damai H5 public detail APIs and stores the last seen project fingerprint in `.state/damai-watch.json`.

Damai may hide exact ticket-grade inventory behind app-side flows and anti-bot checks. This watcher therefore focuses on public project status changes, buy button text, price range, and performance date signals. Treat notifications as a "go check now" reminder, not a guaranteed purchase signal.

## Quick Start

```bash
git clone https://github.com/HANG939/signal-watcher.git
cd signal-watcher
cp .env.example .env
```

Edit `.env`:

```bash
SOURCE_MODE=rss
X_USERNAME=example_user
SERVERCHAN_SENDKEY=your_serverchan_sendkey
DAMAI_ITEM_ID=replace_with_damai_item_id
DAMAI_TARGET_TEXT=replace_with_target_ticket_tier
DAMAI_TARGET_DATES=replace_with_target_dates
```

Run a single check:

```bash
set -a
. ./.env
set +a
python3 src/x_watch.py
python3 src/damai_watch.py
```

The first run initializes local state and usually does not send a notification. Later runs notify when a new tweet or Damai status change is detected.

## VPS Cron Deployment

Install the Twitter/X watcher at 30-second intervals:

```bash
bash scripts/install_x_cron.sh
```

Install the Damai watcher at 15-second intervals:

```bash
bash scripts/install_damai_cron.sh
```

Logs are written to:

- `x-watch.log`
- `damai-watch.log`

Local state is written under `.state/`.

## Docker Deployment

```bash
docker compose up -d --build
```

Useful `.env` options:

```bash
ENABLE_X_WATCH=1
ENABLE_DAMAI_WATCH=1
X_INTERVAL_SECONDS=30
DAMAI_INTERVAL_SECONDS=15
```

## Notification Options

Use one of these:

- `SERVERCHAN_SENDKEY`
- `WECOM_WEBHOOK_URL`
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
- `WEBHOOK_URL`

ServerChan is the easiest route for personal WeChat notifications.

## Configuration

See `.env.example` for all supported environment variables.

Important files:

- `src/x_watch.py`: Twitter/X monitor
- `src/damai_watch.py`: Damai monitor
- `scripts/install_x_cron.sh`: cron installer for Twitter/X
- `scripts/install_damai_cron.sh`: cron installer for Damai
- `.state/`: local state, ignored by git

## Development

Run the same basic checks used by CI:

```bash
bash scripts/check.sh
```

The project currently uses only the Python standard library, so a virtual environment is optional.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned work. Contributions are welcome, especially new monitor modules, notification providers, tests, and documentation improvements.

## Safety

Never commit:

- `.env`
- ServerChan keys, X bearer tokens, webhook URLs, cookies, or browser exports
- `.state/`
- local logs or debug JSON files

If a key leaks, rotate it immediately.

## License

MIT
