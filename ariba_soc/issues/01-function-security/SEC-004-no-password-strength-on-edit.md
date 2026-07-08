# SEC-004: No Password Strength Validation on User Edit / Reset

- **Severity**: High
- **Priority**: P1 (this sprint)
- **Category**: Function & Security

## Current Problem
`settings_manager/forms.py:232` defines `ResetPasswordForm` with only a `new_password` and `confirm_password` field, but applies **no validators**:
```python
class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control form-control-sm'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control form-control-sm'}))
```
There is no minimum length check, no complexity requirement, and no comparison with the user's known attributes. An admin can set a weak password for any user.

## Expected Behavior
- Minimum length enforcement (>= 8 chars recommended)
- At least one uppercase, one lowercase, one digit
- Password cannot be too similar to username
- Validation error displayed clearly

## Affected Files
- `settings_manager/forms.py:232-240`
- `settings_manager/views.py:107-123`

## Suggested Fix
```python
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput(...))
    confirm_password = forms.CharField(widget=forms.PasswordInput(...))

    def clean_new_password(self):
        password = self.cleaned_data['new_password']
        validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('new_password') != cleaned.get('confirm_password'):
            raise ValidationError("Passwords do not match.")
        return cleaned
```

## QA Verification
1. Reset password to "password" — must fail with "too common" or "too short" message.
2. Reset password to "Test123!" — must succeed.
3. Reset with mismatched confirmation — must show mismatch error.
