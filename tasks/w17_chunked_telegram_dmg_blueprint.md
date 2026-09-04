# W17 Chunked Telegram DMG Delivery Blueprint

## Problem Statement
Direct DMG send fails due to per-file Telegram bot size limit.

## Constraints And Assumptions
- User prefers in-chat delivery over external link.
- Receiving multiple part-files in chat is acceptable.

## Design Alternatives Considered
1. Release-link only.
2. External hosting only.
3. Chunked in-chat delivery.

## Chosen Architecture
Choose (3): split and send DMG chunks from CI.

## Interfaces / Modules
- Workflow: `.github/workflows/build-installers.yml`
- macOS step: split + send chunks via `sendDocument`.

## Delivery Plan
1. Add chunking/send logic.
2. Validate and push.
3. Verify run and chat delivery.

## Risks And Open Questions
- Many chunks may hit rate limits; add short pacing.
- User needs reconstruction command.
