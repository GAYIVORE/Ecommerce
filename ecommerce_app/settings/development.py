# ecommerce_app/settings/development.py
import os
import sys
import logging
from pathlib import Path
from decouple import config
import dj_database_url
from whitenoise.storage import CompressedManifestStaticFilesStorage
from .base import *

logger = logging.getLogger(__name__)

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

# 1. Clear out legacy settings from global scope
DEFAULT_FILE_STORAGE = None
if 'DEFAULT_FILE_STORAGE' in globals():
    del globals()['DEFAULT_FILE_STORAGE']


# 2. Subclass WhiteNoise with strict checking completely disabled
class LaxWhiteNoiseStorage(CompressedManifestStaticFilesStorage):
    """
    Custom storage engine natively built to bypass MissingFileErrors.
    Setting manifest_strict = False prevents Django 5.2+ collectstatic from 
    crashing when third-party apps (like django.contrib.admin) reference 
    missing or dead CSS assets (e.g., sorting-icons.svg).
    """
    manifest_strict = False

    def stored_name(self, name):
        try:
            return super().stored_name(name)
        except ValueError as e:
            logger.warning(f"File not found, using original name fallback: {name}")
            return name

    def post_process(self, *args, **kwargs):
        try:
            yield from super().post_process(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Ignored post-processing error on file: {e}")
            return


# 3. CLEAN STR-BASED INLINE CLASS PATH REGISTRATION
# Places this settings module directly into sys.modules map so Django's setup routines 
# can cleanly parse it via string dot-notation inside the STORAGES configuration block.
sys.modules['ecommerce_app.settings.development'] = sys.modules[__name__]


# 4. Modern Django Storage Configuration (Replaces DEFAULT_FILE_STORAGE)
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "ecommerce_app.settings.development.LaxWhiteNoiseStorage",
    },
}

# 5. LEGACY ATTRIBUTE PATCH FOR OLDER PACKAGES & CLOUDINARY INTERNALS
STATICFILES_STORAGE = "ecommerce_app.settings.development.LaxWhiteNoiseStorage"

# ==============================================================================

# Media files (user-uploaded content)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Email settings for development (e.g., print to console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Paystack API Keys
PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default='fallback-dev-secret-key')
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default='fallback-dev-public-key')