# apps/orders/models.py

from django.db import models
from django.conf import settings
from apps.products.models import Product

class ShippingAddress(models.Model):
    """
    Represents a shipping address, linked to a user.
    Users can have multiple addresses.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shipping_addresses', verbose_name="User")
    full_name = models.CharField(max_length=255, verbose_name="Full Name")
    address_line1 = models.CharField(max_length=255, verbose_name="Address Line 1")
    address_line2 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Address Line 2")
    city = models.CharField(max_length=100, verbose_name="City")
    state = models.CharField(max_length=100, blank=True, null=True, verbose_name="State/Region")
    postal_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="Postal Code")
    country = models.CharField(max_length=100, default="Ghana", verbose_name="Country")
    phone_number = models.CharField(max_length=20, verbose_name="Phone Number")
    is_default = models.BooleanField(default=False, verbose_name="Set as Default")

    class Meta:
        verbose_name = 'Shipping Address'
        verbose_name_plural = 'Shipping Addresses'
        unique_together = ('user', 'full_name', 'address_line1', 'city', 'country') # Prevent exact duplicate addresses for a user

    def __str__(self):
        return f"{self.full_name}, {self.address_line1}, {self.city}, {self.country}"

    def save(self, *args, **kwargs):
        # Ensure only one default address per user
        if self.is_default and self.user:
            ShippingAddress.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Order(models.Model):
    """
    Represents a customer's order.
    """
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
        ('Refunded', 'Refunded'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name="Customer")
    # If user is null, it's a guest order. We might need to store guest info separately or on the order directly.
    # For simplicity, we'll assume guest orders will have their details captured in the shipping address.

    shipping_address = models.ForeignKey(ShippingAddress, on_delete=models.SET_NULL, null=True, related_name='orders', verbose_name="Shipping Address")
    # Store a snapshot of the shipping address at the time of order for historical accuracy
    shipping_full_name = models.CharField(max_length=255, verbose_name="Shipping Full Name")
    shipping_address_line1 = models.CharField(max_length=255, verbose_name="Shipping Address Line 1")
    shipping_address_line2 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Shipping Address Line 2")
    shipping_city = models.CharField(max_length=100, verbose_name="Shipping City")
    shipping_state = models.CharField(max_length=100, blank=True, null=True, verbose_name="Shipping State/Region")
    shipping_postal_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="Shipping Postal Code")
    shipping_country = models.CharField(max_length=100, verbose_name="Shipping Country")
    shipping_phone_number = models.CharField(max_length=20, verbose_name="Shipping Phone Number")

    order_date = models.DateTimeField(auto_now_add=True, verbose_name="Order Date")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Updated")
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending', verbose_name="Order Status")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total Amount (GHS)")
    original_total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Original Total Before Discount")
    coupon_applied = models.CharField(max_length=50, null=True, blank=True, verbose_name="Coupon Code Applied")
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Discount Percentage")
    payment_method = models.CharField(max_length=20, default='pay_on_delivery')
    payment_status = models.BooleanField(default=False, verbose_name="Payment Received")
    transaction_id = models.CharField(max_length=255, blank=True, null=True, unique=True, verbose_name="Transaction ID")

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-order_date']
        indexes = [
            models.Index(fields=['-order_date']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"Order {self.id} by {self.user.username if self.user else 'Guest'}"

    def get_total_cost(self):
        """Calculates the total cost of all items in the order."""
        return sum(item.get_item_total for item in self.items.all())


class OrderItem(models.Model):
    """
    Represents an individual item within an order.
    Stores product details at the time of order to ensure historical accuracy
    even if product details change later.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="Order")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, verbose_name="Product") # Keep product link, but allow null if product is deleted
    product_name = models.CharField(max_length=255, verbose_name="Product Name (at time of order)")
    product_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price (at time of order)")
    quantity = models.PositiveIntegerField(verbose_name="Quantity")

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
        unique_together = ('order', 'product') # A product can only be on an order once (per line item)

    def __str__(self):
        return f"{self.quantity} x {self.product_name} in Order {self.order.id}"

    @property
    def get_item_total(self):
        """Calculates the total price for this specific order item."""
        return self.quantity * self.product_price
