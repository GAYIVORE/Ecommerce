# apps/orders/apps.py

from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.orders'
    verbose_name = 'Fulfillment & Orders'

    def ready(self):
        """
        ⚡ Registration Hook: Connects internal signals to automate automated system tasks 
        (like processing sub-order divisions or adjusting product stock limits on confirmation).
        """
        import apps.orders.signals  # noqa