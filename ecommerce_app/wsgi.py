"""
WSGI config for ecommerce_app project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
<<<<<<< HEAD

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_app.settings.development')
=======
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_app.settings.development') # Or whatever your settings path is
>>>>>>> 3fa173f347882383480e83d283bc48a9e89b09c0

application = get_wsgi_application()
