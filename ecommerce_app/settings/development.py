# ecommerce_app/settings/development.py
import os
from .base import *
from decouple import config
import dj_database_url

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key-change-me-in-production')

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '.vercel.app']

# Database configuration (Auto-routes to Supabase via Vercel env, falls back to SQLite locally)
DATABASES = {
    'default': config(
        'DATABASE_URL',
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        cast=dj_database_url.parse
    )
}

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
# STATICFILES_DIRS now defined once in base.py, shared with production.

# Required for Vercel deployment build process compilation
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (user-uploaded content)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ==============================================================================
# STORAGE ENGINE: Cloudinary only kicks in when real credentials are provided.
# Otherwise we fall back to local disk storage + Whitenoise so the app works
# out of the box in local development without any third-party account.
# ==============================================================================
CLOUDINARY_CLOUD_NAME = config('CLOUDINARY_CLOUD_NAME', default='')

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
    'API_KEY': config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
}

if CLOUDINARY_CLOUD_NAME:
    # Real Cloudinary credentials supplied -> use Cloudinary for media/static.
    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
else:
    # No Cloudinary configured -> use local filesystem so `runserver` works
    # immediately with zero external services.
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Legacy alias: django-cloudinary-storage's collectstatic command reads
# settings.STATICFILES_STORAGE directly instead of the new STORAGES dict.
STATICFILES_STORAGE = STORAGES['staticfiles']['BACKEND']

# ==============================================================================
# Email settings for development.
# If EMAIL_HOST is not configured, emails print to the console instead of
# crashing the app (this was the #1 cause of the app failing to boot).
# ==============================================================================
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
    DEFAULT_FROM_EMAIL = 'noreply@localhost'

# Paystack API Keys
PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default='fallback-dev-secret-key')
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default='fallback-dev-public-key')

ACCOUNT_EMAIL_VERIFICATION = "none"

# Modern allauth syntax
ACCOUNT_LOGIN_METHODS = {'email', 'username'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']

# Google OAuth is configured via the admin panel (SocialApp row created at
# /admin/socialaccount/socialapp/), not via env vars. Deliberately NOT
# setting 'APPS' here: allauth always merges settings-based APPS with any
# DB-backed SocialApp rows for the same provider, with no way to make one
# take priority over the other. Defining both here and in the admin means
# two matching app configs, and allauth's get_app() raises
# MultipleObjectsReturned instead of picking one, on every page that calls
# {% provider_login_url %}. Leaving SOCIALACCOUNT_PROVIDERS without 'APPS'
# means allauth uses the DB-configured app exclusively.
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
    }
}