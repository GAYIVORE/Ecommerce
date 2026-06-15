# apps/core/apps.py

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # CORRECTED: Set the name to the full import path 'apps.core'
    name = 'apps.core'
    verbose_name = 'Core Application' # Optional: A more descriptive name for the admin
