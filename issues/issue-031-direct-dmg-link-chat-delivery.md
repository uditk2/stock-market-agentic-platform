# Issue 031: Direct hosted macOS DMG link delivery in chat

## Summary
Replace chunked DMG file delivery with a direct hosted download link message in Telegram chat.

## Problem
Telegram bot upload limits make direct `.dmg` attachments unreliable for large files. Chunked upload is high-friction for users.

## Scope
- Update CI workflow to post stable release URL for macOS DMG in Telegram.
- Remove chunked DMG upload path from workflow.
- Verify push-triggered run posts link successfully.

## Acceptance Criteria
- `Build Installers` macOS push run completes and posts DMG URL message to Telegram chat.
- URL points to `smap-mac-latest` release asset.
- CI remains non-blocking if Telegram send fails.
