# W18 Direct Link Delivery Design

## Problem Statement
User prefers receiving a direct DMG link in chat; file attachment limits and chunk UX are undesirable.

## Constraints
- DMG already hosted by CI release step under tag `smap-mac-latest`.
- Link delivery must be reliable and non-blocking.

## Approach
- Post stable hosted URL to Telegram chat from CI macOS job.
- Keep step non-blocking.
- Use release asset URL that remains constant across builds.
