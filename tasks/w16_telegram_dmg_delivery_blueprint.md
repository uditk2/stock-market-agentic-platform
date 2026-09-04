# W16 Telegram DMG Delivery Blueprint

## Problem Statement
Need direct DMG delivery in chat despite Actions artifact quota issues.

## Constraints And Assumptions
- DMG built only on macOS job.
- Telegram secrets exist in repo.
- Delivery should be best-effort and not fail build.

## Alternatives Considered
1. Continue artifact upload only (blocked by quota).
2. Publish only GitHub release links.
3. Direct Telegram DMG upload from CI job.

## Chosen Architecture
Implement (3) with best-effort behavior and fallback message.

## Interfaces / Modules
- File: `.github/workflows/build-installers.yml`
- Step: `Send macOS DMG to Telegram`
- API: `https://api.telegram.org/bot<TOKEN>/sendDocument`

## Delivery Plan
1. Add workflow step for DMG upload to Telegram.
2. Validate YAML and push.
3. Verify in next pipeline run and report chat delivery result.

## Risks And Open Questions
- Telegram bot file size limits may reject large DMG.
- Network/API transient failures may interrupt delivery.
