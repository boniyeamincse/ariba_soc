# UI-002: Navbar Items Overflow on Mobile Screens

- **Severity**: Medium
- **Priority**: P2 (next sprint)
- **Category**: UI/UX

## Current Problem
The top navbar (`templates/base.html:25-93`) has 7 nav items (Alerts, Board, My Alerts, Dashboard, Reports, Wazuh, Audit Logs) plus the Settings dropdown and user menu. On mobile (< 576px), the collapsed navbar displays these items as a vertical list. The items have `font-size: 0.8rem` which is legible, but:
- The Settings mega-menu (`dropdown-mega-menu`) does not collapse into a single-column on small screens (`col-md-3` classes are used without responsive stacking)
- The user badge displays the role text which truncates awkwardly
- No hamburger animation — the default Bootstrap toggler is used

## Expected Behavior
On mobile:
- Settings mega-menu should stack into a single column
- Role badge text should be abbreviated on small screens
- Navbar brand text should be visible without truncation

## Affected Files
- `templates/base.html:25-93`
- `static/css/ariba-soc.css` (responsive section, lines 439-567)

## Suggested Fix
In `ariba-soc.css`, add:
```css
@media (max-width: 576px) {
    .dropdown-mega-menu .row > div {
        flex: 0 0 100%;
        max-width: 100%;
    }
    .navbar-brand .brand-text {
        font-size: 0.85rem;
    }
}
```

## QA Verification
1. Open app on a 375px wide viewport (iPhone SE).
2. Toggle the navbar hamburger — all items must be readable.
3. Open the Settings dropdown — all 4 category columns must stack vertically.
