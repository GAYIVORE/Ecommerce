# ecommerce_shop/settings/production.py

from .base import *
from decouple import config
import dj_database_url

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
# Always get SECRET_KEY from environment variables in production.
SECRET_KEY = config('SECRET_KEY')

# Allowed hosts for production (your domain names).
# Defaults to allowing any *.vercel.app subdomain so the app isn't fully
# locked out (every request gets Django's generic "Bad Request (400)") if
# the ALLOWED_HOSTS env var isn't set yet. Still strongly recommended to set
# ALLOWED_HOSTS explicitly to your real domain(s) once you have one.
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='.vercel.app').split(',')

# Database for production (e.g., Supabase/Postgres).
# Preferred: a single DATABASE_URL connection string (this is what Supabase
# gives you). Falls back to individual DB_* vars if DATABASE_URL isn't set,
# for compatibility with other hosting providers.
# CONN_MAX_AGE keeps a DB connection alive and reused across requests within
# the same worker instead of opening a brand-new Postgres connection (full
# TCP handshake + auth) on every single request — a real per-request cost
# that was previously paid on every page load. Configurable via env in case
# a given host (e.g. short-lived serverless workers) needs it disabled (0).
DB_CONN_MAX_AGE = config('DB_CONN_MAX_AGE', default=60, cast=int)

DATABASE_URL = config('DATABASE_URL', default='')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=DB_CONN_MAX_AGE)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST'),
            'PORT': config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': DB_CONN_MAX_AGE,
        }
    }

# Static files (CSS, JavaScript, Images) for production
# These should be served by a web server (Nginx/Apache) or CDN
STATIC_URL = '/static/'
# NOTE: nested one level deeper than Vercel's static-build distDir ("staticfiles").
# Vercel publishes the *contents* of distDir directly at the site root with no
# added prefix, so files must already sit under a "static/" folder here in
# order to end up served at /static/... to match STATIC_URL and {% static %}.
STATIC_ROOT = BASE_DIR / 'staticfiles' / 'static'  # Collected static files for deployment


STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
# Legacy aliases: django-cloudinary-storage's collectstatic command reads
# settings.STATICFILES_STORAGE directly (old Django <4.2 style) instead of
# the new STORAGES dict, so it crashes with AttributeError if only STORAGES
# is defined. Keep both in sync.
STATICFILES_STORAGE = STORAGES['staticfiles']['BACKEND']
DEFAULT_FILE_STORAGE = STORAGES['default']['BACKEND']
# Media files (user-uploaded content) for production
# These should be served by a web server or cloud storage (e.g., S3)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Email settings for production (e.g., SendGrid, Mailgun).
# Falls back to console backend if not configured, rather than crashing boot.
if config('EMAIL_HOST', default=''):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@localhost')

# Paystack API Keys
PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default='')
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default='')

# Google OAuth (settings-based app config; no DB SocialApp row required).
# Accepts either GOOGLE_OAUTH_CLIENT_ID/SECRET (preferred) or the shorter
# GOOGLE_CLIENT_ID/SECRET names, so this works regardless of which naming
# was used when the env vars were set up on the host (e.g. Vercel).
GOOGLE_OAUTH_CLIENT_ID = config('GOOGLE_OAUTH_CLIENT_ID', default=config('GOOGLE_CLIENT_ID', default=''))
GOOGLE_OAUTH_CLIENT_SECRET = config('GOOGLE_OAUTH_CLIENT_SECRET', default=config('GOOGLE_CLIENT_SECRET', default=''))
GOOGLE_OAUTH_ENABLED = bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET)

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APPS': [
            {
                'client_id': GOOGLE_OAUTH_CLIENT_ID,
                'secret': GOOGLE_OAUTH_CLIENT_SECRET,
                'key': '',
            }
        ] if GOOGLE_OAUTH_ENABLED else [],
    }
}

ACCOUNT_EMAIL_VERIFICATION = config('ACCOUNT_EMAIL_VERIFICATION', default='mandatory')
ACCOUNT_LOGIN_METHODS = {'email', 'username'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']

# Cloudinary (media/static storage) for production
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
}
if config('CLOUDINARY_CLOUD_NAME', default=''):
    STORAGES['default'] = {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"}
    DEFAULT_FILE_STORAGE = STORAGES['default']['BACKEND']

# Security settings
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', cast=bool, default=True)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', cast=bool, default=True)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', cast=bool, default=True)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', cast=int, default=31536000)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', cast=bool, default=True)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', cast=bool, default=True)
X_FRAME_OPTIONS = 'DENY'