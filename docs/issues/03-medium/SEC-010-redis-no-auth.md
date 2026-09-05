# SEC-010: Redis has no authentication

**Severity:** Medium  
**Priority:** P2  
**Category:** Security  
**Status:** Open  
**File:** `infrastructure/docker-compose.yml`

## Current Problem
Redis is deployed without a password. Any container in the Docker network can connect and read/modify cached data.

## Expected Behavior
Redis requires authentication.

## Affected Files
- `infrastructure/docker-compose.yml` (lines 132-142)

## Suggested Fix
```yaml
redis:
  image: redis:7
  command: redis-server --requirepass ${REDIS_PASSWORD}
  volumes:
    - redis_data:/data
  healthcheck:
    test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
```

## QA Verification
- `redis-cli ping` without password → error
- `redis-cli -a password ping` → PONG
