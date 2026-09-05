# SEC-001: Credentials committed to repository

**Severity:** Critical  
**Priority:** P0  
**Category:** Security  
**Status:** Open  
**File:** `ariba_soc/.env`

## Current Problem
The `.env` file contains real credentials (`Admin@12345`, `WazuhApi@12345`, `ariba_soc`). If this was ever committed to git (even if later removed), secrets remain in git history.

## Expected Behavior
- No real credentials in any tracked file
- Only `.env.example` with placeholder values
- Production secrets stored in vault/Docker secrets

## Affected Files
- `ariba_soc/.env` (line 1-69)
- `ariba_soc/.env.example` (line 1-69)

## Suggested Fix
```bash
# 1. Remove .env from git tracking
git rm --cached ariba_soc/.env

# 2. Rotate ALL credentials immediately

# 3. Purge from git history (if ever committed)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch ariba_soc/.env' \
  --prune-empty --tag-name-filter cat -- --all
```

## QA Verification
- `git log --all --full-history -- ariba_soc/.env` returns empty
- `.env` not in `git status`
