# apps/wishlist/models.py

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.products.models import Product


class Wishlist(models.Model):
    """
    Represents a user's wishlist container. Each user has exactly one wishlist lifecycle instance.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='wishlist', 
        verbose_name="User"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Updated")

    class Meta:
        verbose_name = 'Wishlist'
        verbose_name_plural = 'Wishlists'

    def __str__(self):
        return f"Wishlist of {self.user.username or self.user.email}"

    @property
    def item_count(self):
        """Returns total quantity of uniquely bookmarked variations."""
        return self.items.count()

    @property
    def total_price(self):
        """Calculates the gross marketplace value of all saved listings."""
        return sum(item.product.price for item in self.items.select_related('product').all() if item.product.price)


class WishlistItem(models.Model):
    """
    Represents a singular Product instance nested within a specific user's wishlist container.
    """
    wishlist = models.ForeignKey(
        Wishlist, 
        on_delete=models.CASCADE, 
        related_name='items', 
        verbose_name="Wishlist"
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='wishlist_items', 
        verbose_name="Product"
    )
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Added At")

    class Meta:
        verbose_name = 'Wishlist Item'
        verbose_name_plural = 'Wishlist Items'
        unique_together = ('wishlist', 'product') 
        ordering = ['-added_at']

    def __str__(self):
        username = self.wishlist.user.username or self.wishlist.user.email
        return f"{self.product.name} in {username}'s Wishlist"

    def clean(self):
        """
        Validates that a vendor cannot add their own listed products to their wishlist.
        Defensively handles variations in the Shop model relationship attribute naming.
        """
        if hasattr(self.product, 'shop') and self.product.shop:
            # Safely look for 'user' or 'vendor' attributes on your Shop instance
            shop_owner = getattr(self.product.shop, 'user', getattr(self.product.shop, 'vendor', None))
            
            if shop_owner == self.wishlist.user:
                raise ValidationError("You cannot add your own shop's products to your wishlist.")
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)