# PERF-004: Static Files Not Minified or Compressed

- **Severity**: Low
- **Priority**: P3 (backlog)
- **Category**: Performance

## Current Problem
The static files have no minification or compression:
- `static/css/ariba-soc.css` — 1053 lines, ~28 KB, unminified with comments and whitespace
- `static/js/ariba-soc.js` — 192 lines, ~5 KB, unminified
- No `django-compressor` or `whitenoise` with compression configured
- No cache-busting (`?v=...` or `ManifestStaticFilesStorage`)

In production with `DEBUG=False`, Django does not serve static files. A production deployment using `whitenoise` or nginx will serve the uncompressed files.

## Expected Behavior
- CSS and JS should be minified in production
- `django-compressor` should be configured for offline compression
- Cache-busting manifest should be enabled via `ManifestStaticFilesStorage`

## Affected Files
- `static/css/ariba-soc.css` (entire file)
- `static/js/ariba-soc.js` (entire file)
- `config/settings.py` (needs STATICFILES_STORAGE and compressor config)

## Suggested Fix
1. Install: `pip install django-compressor`
2. Settings:
```python
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
INSTALLED_APPS += ['compressor']
COMPRESS_ENABLED = not DEBUG
COMPRESS_CSS_FILTERS = ['compressor.filters.cssmin.CSSMinFilter']
COMPRESS_JS_FILTERS = ['compressor.filters.jsmin.JSMinFilter']
```
3. In templates, wrap with `{% compress css %}` / `{% compress js %}`.
4. Run `python manage.py compress` during deployment.

## QA Verification
1. Run `python manage.py compress` → verify output CSS/JS are minified.
2. View page source → CSS/JS URLs must include hashed filenames (cache-busting).
3. Page load time for first visit must decrease by >20% due to smaller files.
