# UI-001: No Loading / Busy States on Long-Running Operations

- **Severity**: Medium
- **Priority**: P2 (next sprint)
- **Category**: UI/UX

## Current Problem
The following operations have no loading indicator, spinner, or disabled button state, causing the user to think the app is frozen:
- Wazuh sync button (`wazuh_integration/views.py:76-85`) — can take 30+ seconds
- CSV/Excel exports (`reports/views.py:32-65`) — no progress feedback for large datasets
- Alert board drag-and-drop (`alert_move_api`) — no visual feedback during the request
- Search operations — no "searching..." indicator

## Expected Behavior
Every button that triggers a backend operation should:
1. Show a spinner/loading icon
2. Be disabled during the request (prevent double-submit)
3. Show success/failure feedback when complete

## Affected Files
- `templates/ariba_soc/wazuh_status.html` (sync button)
- `templates/ariba_soc/reports_home.html` (export buttons)
- `templates/ariba_soc/alert_board.html` (drag-and-drop)
- `static/js/ariba-soc.js` (needs loading state helpers)

## Suggested Fix
Add a global JS helper in `ariba-soc.js`:
```javascript
function withLoading(btnSelector, promiseFn) {
    const btn = document.querySelector(btnSelector);
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Loading...';
    return promiseFn().finally(() => {
        btn.disabled = false;
        btn.innerHTML = orig;
    });
}
```
Apply to all async operations and replace inline `onclick` handlers.

## QA Verification
1. Click "Sync Wazuh" — button must immediately show spinner and become disabled.
2. Click "Export CSV" with 5000 alerts — button must show loading state until file download starts.
3. Drag alert card — the card must show a brief "moving..." overlay or the receiving column must pulse.
