# apps/cart/apps.py

from django.apps import AppConfig


class CartConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.cart'
    verbose_name = 'Shopping Cart'

    def ready(self):
        """
        Connects the cart lifecycle signals when the application initializes.
        This handles background tasks like cleanups or auto-instantiations.
        """
        import apps.cart.signals  # noqa