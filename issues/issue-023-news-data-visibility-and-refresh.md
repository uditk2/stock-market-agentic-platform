# Issue 023 - News and market data visibility and refresh workflow

## Problem
Users complete setup but do not clearly see where live news/data status comes from, whether ingestion is running, or why recommendations/news tabs are empty.

## Scope
- Add a visible data status panel in desktop home view.
- Add explicit actions to refresh recommendations and connector diagnostics.
- Improve empty/error states for recommendations/news tabs with actionable guidance.
- Surface latest ingestion run status and counts from service diagnostics endpoints.

## Acceptance Criteria
- Home view shows connector/ingestion status (market + news) without opening developer tools.
- User can trigger refresh and see updated recommendation list or a clear reason when empty.
- Recommendation detail area explains empty news/technicals/strategy states clearly.
- Desktop tests pass.

## Out of Scope
- New broker integrations.
- Strategy model logic changes.
- Real-time websocket streaming.
