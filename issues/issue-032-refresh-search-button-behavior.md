# Issue 032: Refresh/Search buttons show no clear action feedback

## Summary
Users report highlighted `Refresh Data` and `Search` controls appear to do nothing.

## Problem
- `Search` triggers data fetch but gives no explicit success/failure/result feedback.
- Error paths for search are not consistently surfaced to the user.
- Perceived no-op behavior degrades trust in UI actions.

## Scope
- Add deterministic loading state for search/refresh interactions.
- Add user-visible success/error feedback for search action.
- Ensure click and Enter-key search paths share the same guarded execution flow.

## Acceptance Criteria
- `Search` always shows visible action feedback (`loading`, then `N results` or `0 results`).
- Search API failures show toast/error text instead of silent failures.
- `Refresh Data` keeps clear status feedback and disables while running.
