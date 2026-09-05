# CODE-004: User list leaks PII without role check

**Severity:** Low  
**Priority:** P3  
**Category:** Security (Information Disclosure)  
**Status:** Open  
**File:** `ariba_soc/accounts/views.py`

## Current Problem
`user_list` is `@login_required` but has no role check. Any logged-in user can view all users' emails, roles, teams, and phone numbers.

## Expected Behavior
Only admins/managers can view user list.

## Affected Files
- `ariba_soc/accounts/views.py` (lines 29-32)

## Suggested Fix
```python
@login_required
def user_list(request):
    if request.user.analyst_profile.role not in ['ADMIN', 'SOC_MGR']:
        raise PermissionDenied("Access denied")
    users = User.objects.select_related('analyst_profile').all()
    return render(request, 'ariba_soc/user_list.html', {'users': users})
```

## QA Verification
- L1 analyst accesses `/users/` → 403 Forbidden
- Admin accesses `/users/` → sees user list
