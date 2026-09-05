# CODE-006: Model __str__ crashes if user is None

**Severity:** Low  
**Priority:** P3  
**Category:** Reliability  
**Status:** Open  
**File:** `ariba_soc/alerts/models.py`

## Current Problem
`AlertComment.__str__` uses `self.user` which can be `None` if user was deleted (on_delete=SET_NULL). Shows "None - Analyst Note".

## Expected Behavior
Handle None user gracefully.

## Affected Files
- `ariba_soc/alerts/models.py` (lines 215, 249, 263)

## Suggested Fix
```python
def __str__(self):
    username = self.user.username if self.user else 'System'
    return f"{username} - {self.comment_type}"
```

## QA Verification
- Delete a user who has comments → comments show "System" instead of "None"
