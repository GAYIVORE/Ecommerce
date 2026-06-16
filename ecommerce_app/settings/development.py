# ecommerc_app/settings/development.py
import os
from .base import *
from decouple import config
import dj_database_url
from pathlib import Path
from whitenoise.storage import CompressedManifestStaticFilesStorage

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
# MODERN STORAGE & COMPATIBILITY LAYER FOR DJANGO 5.2+ / CLOUDINARY
# ==============================================================================

# 1. Clear out the legacy media storage setting cleanly from global scope
DEFAULT_FILE_STORAGE = None
if 'DEFAULT_FILE_STORAGE' in globals():
    del globals()['DEFAULT_FILE_STORAGE']

# 2. Safely subclass WhiteNoise to turn off manifest_strict mode.
# This prevents Django 5.2 from throwing an unexpected keyword argument crash on initialization.
class LaxWhiteNoiseStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False

# 3. Modern Django Storage Configuration (Replaces DEFAULT_FILE_STORAGE)
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "ecommerce_app.settings.development.LaxWhiteNoiseStorage",
    },
}

# 4. LEGACY ATTRIBUTE PATCH
# This satisfies the internal package check within django-cloudinary-storage during collectstatic
STATICFILES_STORAGE = 'ecommerce_app.settings.development.LaxWhiteNoiseStorage'


# Media files (user-uploaded content)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Email settings for development (e.g., print to console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Paystack API Keys
PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default='fallback-dev-secret-key')
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default='fallback-dev-public-key')