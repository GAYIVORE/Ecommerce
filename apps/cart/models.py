# apps/cart/models.py

from django.db import models
from django.conf import settings # To get the AUTH_USER_MODEL
from apps.products.models import Product # Import Product model

class Cart(models.Model):
    """
    Represents a shopping cart.
    Can be linked to an authenticated user or a session key for anonymous users.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='cart', verbose_name="User")
    session_key = models.CharField(max_length=40, null=True, blank=True, unique=True, verbose_name="Session Key")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Updated")

    class Meta:
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'
        # Ensure that either user or session_key is present, and they are unique when present
        constraints = [
            models.UniqueConstraint(fields=['user'], name='unique_user_cart', condition=models.Q(user__isnull=False)),
            models.UniqueConstraint(fields=['session_key'], name='unique_session_cart', condition=models.Q(session_key__isnull=False)),
        ]
        indexes = [
            models.Index(fields=['session_key']),
        ]

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username}"
        elif self.session_key:
            return f"Cart for session {self.session_key[:10]}..."
        return "Anonymous Cart"

    @property
    def get_total_price(self):
        """Calculates the total price of all items in the cart."""
        return sum(item.get_total_item_price for item in self.items.all())

    @property
    def get_total_items(self):
        """Calculates the total number of distinct items in the cart."""
        return self.items.count()

    @property
    def get_total_quantity(self):
        """Calculates the total quantity of all items in the cart."""
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    """
    Represents an individual item within a shopping cart.
    """
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name="Cart")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Product")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantity")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Added At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Updated")

    class Meta:
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        unique_together = ('cart', 'product') # A product can only be added once per cart

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in {self.cart}"

    @property
    def get_total_item_price(self):
        """Calculates the total price for this specific cart item."""
        return self.quantity * self.product.price
