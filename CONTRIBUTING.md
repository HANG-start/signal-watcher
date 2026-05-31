# Contributing

Thanks for helping improve Signal Watcher.

This project aims to stay small, practical, and easy to run on a low-cost VPS. Good contributions usually make monitoring more reliable, make deployment simpler, or make the project safer for ordinary users.

## Ways To Contribute

- Report a broken RSS source or monitoring API.
- Add a new monitor module for a useful public signal.
- Add a notification provider.
- Improve Docker, cron, or systemd deployment docs.
- Add tests for parsers, state handling, and notification formatting.
- Improve safety docs around credentials, cookies, and rate limits.

## Development Setup

```bash
git clone https://github.com/HANG939/signal-watcher.git
cd signal-watcher
cp .env.example .env
bash scripts/check.sh
```

The project currently uses only the Python standard library.

## Pull Request Checklist

- Keep secrets out of commits.
- Run `bash scripts/check.sh`.
- Update `.env.example` when adding configuration.
- Update `README.md` when changing user-facing behavior.
- Keep monitor behavior respectful of source websites and public APIs.

## Project Boundaries

Please do not contribute captcha bypasses, credential scraping, payment automation, or code that submits paid orders automatically. Signal Watcher is for monitoring and notifications.
