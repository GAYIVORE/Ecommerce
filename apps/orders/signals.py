# apps/orders/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order, SubOrder

@receiver(post_save, sender=Order)
def order_payment_confirmation_trigger(sender, instance, created, **kwargs):
    """
    ⚡ Signal Hook: Triggers automatically when a parent order status changes.
    You can use this to send payment confirmation emails or vendor alerts
    once instance.payment_status transitions to True.
    """
    if not created and instance.payment_status:
        # Cascade statuses down to sub-orders if needed
        pending = list(instance.sub_orders.filter(status='Pending'))
        for sub_order in pending:
            sub_order.status = 'Processing'
            sub_order.save()


@receiver(post_save, sender=SubOrder)
def suborder_status_rollup_trigger(sender, instance, created, **kwargs):
    """
    ⚡ Vendor influence hook: whenever ANY vendor updates their own SubOrder
    (marking it Shipped, Delivered, Refunded, etc. — from the vendor dashboard,
    the admin panel, or anywhere else), recompute the customer-facing parent
    Order status so it always reflects the combined state every vendor is in.
    """
    if not created:
        instance.parent_order.recompute_status()