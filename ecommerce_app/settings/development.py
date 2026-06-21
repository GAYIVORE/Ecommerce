# ecommerce_shop/settings/development.py
import os
from .base import *
from decouple import config
import dj_database_url

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
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
STATICFILES_DIRS = [
    BASE_DIR / 'static', # Global static files
]

# Required for Vercel deployment build process compilation
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Cloudinary Account Configurations
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
}

# ==============================================================================
# UNIFIED CLOUDINARY STORAGE ENGINE BLOCK (Fixes Vercel Read-Only & App Crashes)
# ==============================================================================

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "cloudinary_storage.storage.StaticCloudinaryStorage",
    },
}

# Explicitly declare legacy properties to satisfy package checks during collectstatic
STATICFILES_STORAGE = 'cloudinary_storage.storage.StaticCloudinaryStorage'
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# ==============================================================================

# Media files (user-uploaded content)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Email settings for development (e.g., print to console)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)

# Paystack API Keys
PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default='fallback-dev-secret-key')
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default='fallback-dev-public-key')