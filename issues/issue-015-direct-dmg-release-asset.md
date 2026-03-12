# Issue 015: Publish direct macOS DMG via GitHub Release asset

## Problem
GitHub Actions artifacts are always ZIP-wrapped. Users requested a direct downloadable DMG URL.

## Scope
- Add release publish step in installer workflow for macOS build leg.
- Publish/overwrite stable asset under `smap-mac-latest` tag.
- Document direct release URL in README.

## Acceptance Criteria
- Workflow publishes `SMAP-Desktop-macOS-latest.dmg` to `smap-mac-latest` release tag on push to master/main.
- Existing artifact uploads continue to work.
- README includes direct release link.
