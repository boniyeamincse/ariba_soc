# UI-006: Inconsistent Empty States Across List Pages

- **Severity**: Low
- **Priority**: P3 (backlog)
- **Category**: UI/UX

## Current Problem
Some list templates show a simple "No X found." text row when empty (e.g., `user_management.html:72-74`, `analyst_profile.html:58-60`). Others may not handle empty states at all or only render an empty table. No empty state includes an illustration, helpful message, or call-to-action button.

Examples:
- `my_alerts` view (`alerts/views.py:246-247`) handles empty state with a `no_alerts` flag but the template just shows text
- Settings list pages like `alert_source_settings.html` may show empty tables without guidance
- `wazuh_agents` page has no empty state at all — it just renders an empty list

## Expected Behavior
Every list page should have a consistent empty state component:
- An icon (e.g., `bi-inbox` or `bi-search`)
- A friendly message explaining why the list might be empty
- A primary action button (e.g., "Create First Alert Source", "Sync Wazuh Now")
- Matching the SOC dark theme

## Affected Files
- `templates/ariba_soc/my_alerts.html`
- `templates/ariba_soc/wazuh_agents.html`
- `templates/ariba_soc/sync_logs.html`
- All `settings_manager` list templates

## Suggested Fix
Create a reusable partial `templates/_empty_state.html`:
```html
<div class="text-center py-5">
    <i class="bi {{ icon|default:'bi-inbox' }}" style="font-size: 3rem; color: var(--text-muted);"></i>
    <h5 class="mt-3 text-muted">{{ message|default:'No items found.' }}</h5>
    {% if action_url and action_label %}
    <a href="{{ action_url }}" class="btn btn-ariba-primary mt-2">{{ action_label }}</a>
    {% endif %}
</div>
```
Include it with `{% include '_empty_state.html' with icon='bi-cloud-slash' message='No Wazuh agents connected.' %}`.

## QA Verification
1. Navigate to a settings list page that has no records — a styled empty state with icon and message must appear.
2. The empty state must include a "Create" button if the user has permission.
3. On a page with records, the empty state must not appear.
