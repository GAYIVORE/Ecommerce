# ecommerce_app/settings/development.py
import os
from .base import *
from decouple import config
import dj_database_url
from pathlib import Path
from whitenoise.storage import CompressedManifestStaticFilesStorage
import logging

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

# 1. Clear out the legacy media storage setting cleanly from global scope
DEFAULT_FILE_STORAGE = None
if 'DEFAULT_FILE_STORAGE' in globals():
    del globals()['DEFAULT_FILE_STORAGE']

# 2. Subclass WhiteNoise and safely handle missing files
class LaxWhiteNoiseStorage(CompressedManifestStaticFilesStorage):
    """
    Custom storage that handles missing files gracefully.
    This prevents the build from failing when Django's admin CSS
    references files that don't exist.
    """
    
    def stored_name(self, name):
        """
        Override stored_name to return the original name if the file
        can't be found, instead of raising MissingFileError.
        """
        try:
            return super().stored_name(name)
        except ValueError as e:
            # Log the missing file but don't fail the build
            if "could not be found" in str(e) or "sorting-icons" in str(e):
                logger.warning(f"File not found, using original name: {name}")
                return name
            raise e
    
    def post_process(self, *args, **kwargs):
        """
        Override post_process to catch any errors during processing.
        """
        try:
            yield from super().post_process(*args, **kwargs)
        except Exception as e:
            # If there's an error, log it but don't fail
            logger.warning(f"Post-processing error: {e}")
            return

# 3. DYNAMIC SYS MODULE REGISTRATION
# Maps the class into system memory so Django can safely .rsplit() it as a string path
import sys
sys.modules['lax_storage_patch'] = sys.modules[__name__]

# 4. Modern Django Storage Configuration (Replaces DEFAULT_FILE_STORAGE)
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "lax_storage_patch.LaxWhiteNoiseStorage",
    },
}

# 5. LEGACY ATTRIBUTE PATCH FOR CLOUDINARY INTERNALS
STATICFILES_STORAGE = "lax_storage_patch.LaxWhiteNoiseStorage"

# ==============================================================================

# Media files (user-uploaded content)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Email settings for development (e.g., print to console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Paystack API Keys
PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default='fallback-dev-secret-key')
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default='fallback-dev-public-key')