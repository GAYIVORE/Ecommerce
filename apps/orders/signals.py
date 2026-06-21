# apps/orders/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order

@receiver(post_save, sender=Order)
def order_payment_confirmation_trigger(sender, instance, created, **kwargs):
    """
    ⚡ Signal Hook: Triggers automatically when a parent order status changes.
    You can use this to send payment confirmation emails or vendor alerts
    once instance.payment_status transitions to True.
    """
    if not created and instance.payment_status:
        # Cascade statuses down to sub-orders if needed
        for sub_order in instance.sub_orders.filter(status='Pending'):
            sub_order.status = 'Processing'
            sub_order.save()