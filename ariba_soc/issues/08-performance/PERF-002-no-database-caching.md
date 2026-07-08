# PERF-002: No Redis / Database Query Caching

- **Severity**: Medium
- **Priority**: P2 (next sprint)
- **Category**: Performance

## Current Problem
The project has no caching layer. Every page load:
1. Runs multiple database queries
2. Hits the database for alert counts (context processor on every page)
3. Settings dashboard counts are regenerated fresh on every load
4. The alerts API endpoint (`alerts/views.py:254-274`) runs a fresh query even if data hasn't changed

There is no `CACHES` configuration in `config/settings.py` — Django uses the default local-memory cache (LocMemCache), which is per-process and not shared across workers.

## Expected Behavior
- Redis or Memcached should be configured as the cache backend
- Dashboard stats should be cached with a 60-second TTL
- Context processor alert counts should be cached with a 30-second TTL
- The alerts API should use `@cache_page` or fragment caching

## Affected Files
- `config/settings.py` (needs CACHES config)
- `alerts/context_processors.py` (needs cache)
- `dashboard/views.py` (needs cache)
- `alerts/views.py:254-274` (alerts_api could use caching)

## Suggested Fix
```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
    }
}
```

```python
# context_processors.py
from django.core.cache import cache

def user_alerts_context(request):
    cache_key = f'alert_counts_{request.user.id}'
    counts = cache.get(cache_key)
    if counts is None:
        counts = {
            'my_assigned_count': Alert.objects.filter(...).count(),
            'new_alerts_count': Alert.objects.filter(status='New').count(),
            'critical_alerts_count': Alert.objects.filter(...).count(),
        }
        cache.set(cache_key, counts, 30)
    counts.update({'settings_roles': ...})
    return counts
```

## QA Verification
1. Install Redis and configure `REDIS_URL`.
2. Load the same page twice — second load must be faster (check via Django Debug Toolbar).
3. Verify cache key TTL expires after configured timeout.
4. Run with `LocMemCache` fallback if Redis is unavailable.
