# W17 Chunked Telegram DMG Delivery Design

## Problem Statement
User requires DMG delivered directly in Telegram chat, but bot upload limit rejects full DMG (`HTTP 413`).

## Constraints
- Telegram bot file size limit applies per upload.
- DMG is ~123MB.
- Delivery must happen from CI macOS job.

## Approach
- Split DMG into <=49MB chunks.
- Send each chunk as a Telegram document in sequence.
- Send reconstruction instructions in chat.
- Keep step non-blocking for CI stability.
