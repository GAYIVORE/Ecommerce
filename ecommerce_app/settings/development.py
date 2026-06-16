# ecommerce_shop/settings/development.py
import os
from .base import *
from decouple import config
import dj_database_url
from pathlib import Path

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Recalculate BASE_DIR cleanly based on this file's position
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY', default='your-insecure-dev-secret-key-please-change')

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

# This is where WhiteNoise looks for your raw local development assets
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# This tells WhiteNoise where to compile production static assets
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Ensure Cloudinary is loaded before staticfiles in INSTALLED_APPS
if 'cloudinary_storage' not in INSTALLED_APPS:
    try:
        staticfiles_index = INSTALLED_APPS.index('django.contrib.staticfiles')
        INSTALLED_APPS.insert(staticfiles_index, 'cloudinary_storage')
    except ValueError:
        INSTALLED_APPS.append('cloudinary_storage')

# Cloudinary Storage Configurations
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
}

# ==============================================================================
# FORCE REMOVE DEPRECATED STORAGE CONFIGURATIONS
# ==============================================================================
# 1. Nullify it globally
DEFAULT_FILE_STORAGE = None

# 2. Forcefully purge it out of the global runtime namespace dictionary
if 'DEFAULT_FILE_STORAGE' in globals():
    del globals()['DEFAULT_FILE_STORAGE']

# Modern Django Storage Configuration (Replaces DEFAULT_FILE_STORAGE)
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# 3. LEGACY COMPATIBILITY PATCH FOR CLOUDINARY_STORAGE OVERRIDE
# This satisfies the third-party package check during collectstatic
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (user-uploaded content)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Email settings for development (e.g., print to console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Paystack API Keys
PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default='fallback-dev-secret-key')
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default='fallback-dev-public-key')