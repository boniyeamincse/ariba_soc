# DB-004: Duplicate AlertSource Model Across Two Apps

- **Severity**: Low
- **Priority**: P3 (backlog)
- **Category**: Database

## Current Problem
There are **two separate models** representing the same concept:
1. `alerts/models.py:41-52` — `AlertSource` (used by the `Alert` model as a FK)
2. `settings_manager/models.py:22-35` — `AlertSourceSettings` (used by the Settings UI)

Both have identical fields: `name`, `source_type`, `description`, `is_active`, `created_at`, `updated_at`. The `Alert` model references `AlertSource`, while the settings UI manages `AlertSourceSettings`. These are completely independent tables — creating a source in Settings does not make it available for alert assignment, and vice versa.

## Expected Behavior
There should be a single `AlertSource` model. The settings UI should manage instances of the same model that the `Alert` FK references. This prevents data duplication and ensures consistency.

## Affected Files
- `alerts/models.py:41-52` (AlertSource)
- `settings_manager/models.py:22-35` (AlertSourceSettings)
- `settings_manager/views.py:207-253` (views that manage AlertSourceSettings)
- `wazuh_integration/services.py:156` (creates AlertSource)

## Suggested Fix
1. Delete `AlertSourceSettings` from `settings_manager/models.py`.
2. Update `settings_manager/views.py` to use `alerts.models.AlertSource` instead.
3. Update `settings_manager/forms.py` to reference `AlertSource`.
4. Generate a migration that migrates data from `AlertSourceSettings` to `AlertSource`.
5. Update all settings templates to use the new model name.

## QA Verification
1. Navigate to Settings → Alert Sources — must show the same sources linked to alerts.
2. Creating a source in Settings must immediately be available for alert filtering.
3. No duplicate tables exist after migration.
