# UI-003: Settings Sidebar Duplicates Navbar Mega-Menu

- **Severity**: Low
- **Priority**: P3 (backlog)
- **Category**: UI/UX

## Current Problem
`settings_manager/templates/settings_manager/settings_base.html` renders a full left sidebar with the same 16 links (15 settings + Django admin) that are already available in the top navbar's Settings mega-menu (`templates/base.html:34-72`). This creates:
- Redundant navigation that doubles the markup
- Two places to maintain the same links
- Visual inconsistency — the sidebar uses `var(--bg-dark)` while the mega-menu uses `var(--bg-card)`
- Reduced content width on settings pages due to the 260px sidebar

## Expected Behavior
Since the top navbar already provides access to all settings pages, the settings sidebar should be removed. The settings pages should use the full width of the content area, with a breadcrumb or page title for context.

## Affected Files
- `settings_manager/templates/settings_manager/settings_base.html` (entire sidebar `<div class="settings-sidebar">` section)
- `settings_manager/templates/settings_manager/settings_base.html:38` (`.settings-main` flex correction)

## Suggested Fix
Remove the sidebar `<div class="d-flex">` wrapper and the `.settings-sidebar` div. Change `settings_base.html` to be a simple wrapper that extends `base.html` and defines the `{% block settings_content %}` area without the sidebar.

## QA Verification
1. Navigate to any settings page — the left sidebar must be gone.
2. Settings content must now span the full available width.
3. All internal links within settings pages must still work.
