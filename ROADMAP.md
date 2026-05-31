# Roadmap

Signal Watcher is moving toward a small, composable monitoring framework.

## Near Term

- Add tests for RSS parsing, state updates, and notification formatting.
- Add systemd service examples for long-running VPS deployments.
- Add more notification providers.
- Improve structured logging and failure visibility.
- Document common deployment recipes.

## Monitor Ideas

- Generic webpage keyword/status monitor.
- Generic JSON endpoint monitor.
- More ticketing and stock availability sources.
- Learning platform assignment, exam, and sign-in reminders where public or user-authorized APIs are available.

## Maintainer Automation

- Use Codex for pull request review assistance.
- Generate release notes from merged changes.
- Maintain issue triage labels and templates.
- Run safety checks that prevent secrets or state files from being committed.

## Non-Goals

- Captcha bypassing.
- Scraping private accounts or protected data.
- Automatic paid checkout or payment submission.
- Sharing cookies, tokens, or browser session data.
