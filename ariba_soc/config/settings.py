import os
from pathlib import Path
from django.contrib.messages import constants as messages
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() == 'true'

_INSECURE_SECRET_KEY_DEFAULTS = {'', 'dev-secret-key-change-in-production', 'change-this-to-a-secure-random-key'}
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
if SECRET_KEY in _INSECURE_SECRET_KEY_DEFAULTS:
    if DEBUG:
        SECRET_KEY = 'dev-secret-key-change-in-production'
    else:
        # A guessable SECRET_KEY lets an attacker forge session cookies, CSRF
        # tokens, and password-reset links -- refuse to start rather than run
        # a production instance signed with a key anyone can read in this repo.
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY is unset or using a known insecure default. '
            'Set a unique DJANGO_SECRET_KEY in the environment before running with DJANGO_DEBUG=False.'
        )

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

# Kept independent from SECRET_KEY on purpose: SECRET_KEY signs sessions/CSRF/
# password-reset tokens and should be rotatable on its own for security hygiene
# without silently breaking decryption of data-at-rest (django-cryptography
# derives its key from CRYPTOGRAPHY_KEY, falling back to SECRET_KEY if unset --
# that fallback is what broke the 3 encrypted fields when SECRET_KEY rotated).
CRYPTOGRAPHY_KEY = os.environ.get('DJANGO_CRYPTOGRAPHY_KEY', '')
if not CRYPTOGRAPHY_KEY:
    if DEBUG:
        CRYPTOGRAPHY_KEY = 'dev-cryptography-key-change-in-production'
    else:
        raise ImproperlyConfigured(
            'DJANGO_CRYPTOGRAPHY_KEY is unset. Set a unique DJANGO_CRYPTOGRAPHY_KEY '
            'in the environment before running with DJANGO_DEBUG=False.'
        )

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'accounts',
    'alerts',
    'wazuh_integration',
    'dashboard',
    'reports',
    'audit',
    'settings_manager',
    'monitor',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.MonitorAccessMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'audit.middleware.AuditMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'alerts.context_processors.user_alerts_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DATABASE_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.environ.get('DATABASE_NAME', 'ariba_soc'),
        'USER': os.environ.get('DATABASE_USER', 'ariba_soc'),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD', 'ariba_soc'),
        'HOST': os.environ.get('DATABASE_HOST', 'localhost'),
        'PORT': os.environ.get('DATABASE_PORT', '5432'),
    }
}

# Fallback to SQLite if postgres isn't available (dev only)
if 'test' in os.environ.get('DJANGO_RUN_MODE', '') or os.environ.get('DATABASE_ENGINE', '').endswith('sqlite3'):
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:role_redirect'
LOGOUT_REDIRECT_URL = 'accounts:login'

MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
    }
}

WAZUH_API_URL = os.environ.get('WAZUH_API_URL', '')
WAZUH_API_USERNAME = os.environ.get('WAZUH_API_USERNAME', '')
WAZUH_API_PASSWORD = os.environ.get('WAZUH_API_PASSWORD', '')
WAZUH_VERIFY_SSL = os.environ.get('WAZUH_VERIFY_SSL', 'False').lower() == 'true'
WAZUH_API_TIMEOUT = int(os.environ.get('WAZUH_API_TIMEOUT', '30'))

_USE_HTTPS = os.environ.get('DJANGO_USE_HTTPS', 'False').lower() == 'true'
SESSION_COOKIE_SECURE = _USE_HTTPS
CSRF_COOKIE_SECURE = _USE_HTTPS
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()
]

# Inert while DJANGO_USE_HTTPS is unset (matches SESSION/CSRF_COOKIE_SECURE
# above) -- HSTS/redirect headers are meaningless without TLS in front of
# nginx. Flip DJANGO_USE_HTTPS once real certs are in place; if nginx
# terminates TLS and proxies to this app over plain HTTP, SECURE_PROXY_SSL_HEADER
# also needs to be set then, otherwise SECURE_SSL_REDIRECT will redirect-loop.
SECURE_SSL_REDIRECT = _USE_HTTPS
SECURE_HSTS_SECONDS = 31536000 if _USE_HTTPS else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = _USE_HTTPS
SECURE_HSTS_PRELOAD = _USE_HTTPS

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '25'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'False').lower() == 'true'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'ariba_soc@localhost')
