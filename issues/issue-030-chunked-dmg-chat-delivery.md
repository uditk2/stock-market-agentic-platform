# Issue: Chunked DMG delivery in Telegram chat

## Summary
Deliver the macOS DMG in Telegram chat by splitting into bot-safe chunk sizes.

## Scope
- Split DMG into <=49MB chunks.
- Send all chunks in sequence from CI macOS job.
- Send reconstruction instructions in chat.

## Acceptance Criteria
- Chunks are delivered in chat.
- CI remains non-blocking.
- User has clear command to reconstruct DMG locally.
