# ecommerce_app/wsgi.py

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_app.settings.development')

application = get_wsgi_application()