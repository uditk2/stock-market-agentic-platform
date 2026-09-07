# Issue: Deliver macOS DMG directly in Telegram chat

## Summary
Send the built macOS DMG directly to user chat from CI so delivery does not depend on Actions artifacts.

## Scope
- Add macOS-only Telegram sendDocument step.
- Keep step non-blocking.
- Add fallback message on failure.

## Acceptance Criteria
- CI attempts Telegram DMG delivery on macOS builds.
- CI does not fail solely because Telegram delivery fails.
- User receives DMG or fallback notification in chat.
