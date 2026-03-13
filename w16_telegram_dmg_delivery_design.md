# W16 Telegram DMG Delivery Design

## Problem Statement
User wants macOS DMG delivered directly in Telegram chat instead of relying on GitHub Actions artifact storage.

## Constraints
- DMG is generated on macOS runner.
- GitHub artifact upload quota is exhausted.
- Telegram delivery should not fail the CI build.

## Assumptions
- Repository secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are available.
- Telegram Bot API accepts the DMG file size (attempt required to confirm).

## Approach
- Add a post-build step on `macos-latest` that sends the generated `.dmg` via Telegram `sendDocument`.
- Mark step `continue-on-error: true` so CI remains non-blocking.
- Include a fallback text message if DMG send fails.
