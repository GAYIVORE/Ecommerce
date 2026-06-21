# apps/orders/models.py

from django.db import models
from django.conf import settings
from apps.products.models import Product
from apps.products.models import Shop # ⚡ Linked to capture vendor ownership tracking models


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
        unique_together = ('user', 'full_name', 'address_line1', 'city', 'country')

    def __str__(self):
        return f"{self.full_name}, {self.address_line1}, {self.city}, {self.country}"

    def save(self, *args, **kwargs):
        if self.is_default and self.user:
            ShippingAddress.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Order(models.Model):
    """
    Parent Order container holding global checkout data metrics, 
    financial totals, and core gateway payload tokens.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name="Customer")
    shipping_address = models.ForeignKey(ShippingAddress, on_delete=models.SET_NULL, null=True, related_name='orders', verbose_name="Shipping Address")
    
    # Snapshot properties
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
    
    # Financial metrics
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total Amount (GHS)")
    original_total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Original Total Before Discount")
    coupon_applied = models.CharField(max_length=50, null=True, blank=True, verbose_name="Coupon Code Applied")
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Discount Percentage")
    
    PAYMENT_METHOD_CHOICES = (
        ('paystack', 'Paystack Online Gateway'),
        ('flutterwave', 'Flutterwave Payment Link'),
        ('momo', 'Mobile Money Express Direct'),
        ('cod', 'Pay on Delivery / Cash'),
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='paystack')
    payment_status = models.BooleanField(default=False, verbose_name="Payment Verified")
    transaction_id = models.CharField(max_length=255, blank=True, null=True, unique=True, verbose_name="Transaction ID Reference")
    
    STATUS_CHOICES = [
        ('Pending', 'Pending'),          # Created, awaiting secure checkout payment
        ('Processing', 'Processing'),    # Paid, vendors notified to prepare items
        ('Completed', 'Completed'),      # Every single vendor sub-order was delivered
        ('Cancelled', 'Cancelled'),      # Voided or completely refunded
    ]
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='Pending'
    )

    class Meta:
        verbose_name = 'Global Order'
        verbose_name_plural = 'Global Orders'
        ordering = ['-order_date']
        indexes = [
            models.Index(fields=['-order_date']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"Order Group {self.id} by {self.user.username if self.user else 'Guest'}"


class SubOrder(models.Model):
    """
    ⚡ Vendor Partition: Splits parent order components out so separate vendors
    can manage fulfillment sequences independently without cross-contaminating view contexts.
    """
    STATUS_CHOICES = (
        ('Pending', 'Pending Fulfillment'),
        ('Processing', 'Processing / Packing'),
        ('Shipped', 'Handed over to Courier'),
        ('Delivered', 'Delivered Successfully'),
        ('Cancelled', 'Cancelled / Invalid'),
        ('Refunded', 'Returned & Funds Reversed'),
    )

    parent_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='sub_orders', verbose_name="Parent Order Group")
    shop = models.ForeignKey(Shop, on_delete=models.PROTECT, related_name='vendor_orders', verbose_name="Vendor Shop")
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending', verbose_name="Fulfillment Status")
    
    # Isolated subtotals for specific vendor settlements
    sub_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Vendor Subtotal (GHS)")
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Vendor Shipping Fee")
    
    tracking_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Courier Air Waybill / Tracking")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Vendor Sub-Order'
        verbose_name_plural = 'Vendor Sub-Orders'
        ordering = ['-created_at']

    def __str__(self):
        return f"SubOrder {self.id} | Shop: {self.shop.name} | Part of Order {self.parent_order.id}"


class OrderItem(models.Model):
    """
    Represents an individual item within an order, tied to both the global 
    and sub-order tracking segments.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="Global Order")
    # ⚡ Foreign target hook connecting line rows straight into localized shop bins
    sub_order = models.ForeignKey(SubOrder, on_delete=models.CASCADE, related_name='items', null=True, blank=True, verbose_name="Vendor Sub-Order Group")
    
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, verbose_name="Product Link")
    product_name = models.CharField(max_length=255, verbose_name="Product Name (Snapshot)")
    product_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price (Snapshot)")
    quantity = models.PositiveIntegerField(verbose_name="Quantity Ordered")

    class Meta:
        verbose_name = 'Line Order Item'
        verbose_name_plural = 'Line Order Items'
        unique_together = ('order', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product_name} (Order Ref #{self.order.id})"

    @property
    def get_item_total(self):
        price = self.price or 0
        quantity = self.quantity or 0
        return price * quantity