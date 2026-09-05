# SEC-005: No password validation on admin reset

**Severity:** High  
**Priority:** P1  
**Category:** Security (Authentication)  
**Status:** Open  
**File:** `ariba_soc/settings_manager/views.py`

## Current Problem
`user_reset_password` view calls `user.set_password()` without running Django's `AUTH_PASSWORD_VALIDATORS`. An admin can set a user's password to `a` or `123456`.

## Expected Behavior
All password changes must pass Django's password validators (minimum length, common password check, numeric check).

## Affected Files
- `ariba_soc/settings_manager/views.py` (lines 116-132)
- `ariba_soc/settings_manager/forms.py` (lines 232-240)

## Suggested Fix
```python
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

@login_required
def user_reset_password(request, user_id):
    # ... existing code ...
    if form.is_valid():
        new_password = form.cleaned_data['new_password']
        try:
            validate_password(new_password, user=target_user)
        except ValidationError as e:
            for error in e.messages:
                messages.error(request, error)
            return render(request, 'settings_manager/user_reset_password.html', context)
        
        target_user.set_password(new_password)
        target_user.save()
```

## QA Verification
- Try setting password to `a` → error message
- Try setting to `password` → error message
- Try setting to `Str0ngP@ss!` → success
