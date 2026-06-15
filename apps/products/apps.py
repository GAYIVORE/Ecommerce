# apps/products/apps.py

from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # CORRECTED: Set the name to the full import path 'apps.products'
    name = 'apps.products'
    verbose_name = 'Products' # Optional: A more descriptive name for the admin
