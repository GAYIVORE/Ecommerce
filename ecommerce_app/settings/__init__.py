# ecommerce_app/settings/__init__.py

import os

# Check which environment Django is trying to load
settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', 'ecommerce_app.settings.development')

if settings_module == 'ecommerce_app.settings.development':
    from .development import *
elif settings_module == 'ecommerce_app.settings.production':
    from .production import *