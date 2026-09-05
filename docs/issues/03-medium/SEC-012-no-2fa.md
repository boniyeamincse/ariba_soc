# SEC-012: No 2FA support

**Severity:** Medium  
**Priority:** P2  
**Category:** Security / Missing Feature  
**Status:** Open  
**File:** `ariba_soc/accounts/`

## Current Problem
No two-factor authentication. For a SOC tool with access to sensitive security data, 2FA should be mandatory.

## Expected Behavior
- TOTP-based 2FA (Google Authenticator, Authy)
- Backup codes
- Mandatory for admin users

## Affected Files
- `ariba_soc/accounts/views.py`
- `ariba_soc/accounts/urls.py`
- `ariba_soc/config/settings.py`

## Suggested Fix
```bash
pip install django-otp qrcode
```
```python
# settings.py
INSTALLED_APPS += ['django_otp', 'django_otp.plugins.otp_totp']

MIDDLEWARE += ['django_otp.middleware.OTPMiddleware']

# views.py
from django_otp import otp上司
def login_view(request):
    # ... after authentication
    if not request.user.is_verified():
        return redirect('accounts:verify_otp')
```

## QA Verification
- Login with 2FA enabled → OTP prompt
- Invalid OTP → access denied
- Backup codes work
