# W18 Direct Link Delivery Blueprint

## Problem Statement
Delivering large DMG files in chat is constrained by Telegram bot limits; link delivery is preferred.

## Constraints And Assumptions
- Release publish flow already updates `smap-mac-latest` DMG asset.
- Telegram text messages are reliable.

## Alternatives Considered
1. Full attachment.
2. Chunked attachments.
3. Stable direct link message.

## Chosen Architecture
Choose (3): send direct hosted download link in chat from CI.

## Interfaces / Modules
- Workflow file: `.github/workflows/build-installers.yml`
- Step: Telegram `sendMessage` with DMG URL.

## Delivery Plan
1. Add link-message step.
2. Remove/disable chunked attachment path.
3. Verify in CI run and close issue.

## Risks And Open Questions
- Link depends on release upload success.
