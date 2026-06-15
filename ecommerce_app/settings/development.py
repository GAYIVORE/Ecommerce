# ecommerce_shop/settings/development.py
import os
from .base import *
from decouple import config

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
# For development, you can keep it in .env or directly here for simplicity,
# but always use decouple for production.
SECRET_KEY = config('SECRET_KEY', default='your-insecure-dev-secret-key-please-change')

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '.vercel.app']

# Database for development (SQLite is fine for local dev)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static', # Global static files
]

# Media files (user-uploaded content)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Email settings for development (e.g., print to console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Optional: Add any development-specific apps or middleware here
INSTALLED_APPS += [
    # 'debug_toolbar', # Example: Django Debug Toolbar for dev
]

MIDDLEWARE += [
    # 'debug_toolbar.middleware.DebugToolbarMiddleware', # Example
]

# INTERNAL_IPS = [
#     '127.0.0.1',
# ]

PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default='fallback-dev-secret-key')
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default='fallback-dev-public-key')
