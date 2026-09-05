# SEC-002: Wazuh API Credentials Stored in Django Settings

- **Severity**: Critical
- **Priority**: P0 (immediate)
- **Category**: Function & Security

## Current Problem
`config/settings.py:110-114` and `wazuh_integration/models.py:21` store Wazuh API credentials:
- Settings file reads from env but exposes in `settings.py` module (accessible via Django debug / error pages)
- Model stores `api_password` as plain `CharField` in the database — anyone with DB read access sees the password
- `WazuhConfigurationForm` renders the password field with `render_value=True`, exposing it in HTML

```python
# settings.py
WAZUH_API_PASSWORD = os.environ.get('WAZUH_API_PASSWORD', '')

# models.py
api_password = models.CharField(max_length=500, blank=True)
```

## Expected Behavior
- Passwords must be encrypted at rest using Django's `Fernet` fields or custom encryption
- Password field should not render the value back in HTML by default
- Audit log should mask credential changes

## Affected Files
- `config/settings.py:110-114`
- `wazuh_integration/models.py:21`
- `wazuh_integration/forms.py:11` (render_value=True)

## Suggested Fix
1. Replace `CharField` with encrypted field (use `django-cryptography` or `django-fernet-fields`):
   ```python
   from django_cryptography.fields import encrypt
   api_password = encrypt(models.CharField(max_length=500, blank=True))
   ```
2. In `forms.py`, remove `render_value=True` from the password widget.
3. Mask password in audit logs and never expose in API responses.

## QA Verification
1. View the Wazuh API settings page HTML — the password field must show `********` not the actual value.
2. Query the database directly — the password column must show encrypted (non-plaintext) content.
3. Save a new configuration — the password must be decryptable by the application but not by DB readers.
