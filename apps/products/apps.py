# apps/products/apps.py

from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    
    # CORRECTED: Set the name to the full import path 'apps.products'
    name = 'apps.products'
    
    # Optional: A more descriptive name for the admin interface
    verbose_name = 'Marketplace Inventory & Storefront Management' 

    def ready(self):
        """
        🌟 ENTERPRISE UPGRADE: Imports and registers marketplace background signals 
        when the application subsystem initializes.
        """
        try:
            import apps.products.signals  # noqa
        except ImportError:
            pass