# apps/wishlist/models.py

from django.db import models
from django.conf import settings # To link to the custom User model
from apps.products.models import Product # To link to the Product model

class Wishlist(models.Model):
    """
    Represents a user's wishlist. Each user has one wishlist.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist', verbose_name="User")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Updated")

    class Meta:
        verbose_name = 'Wishlist'
        verbose_name_plural = 'Wishlists'

    def __str__(self):
        return f"Wishlist of {self.user.username}"

class WishlistItem(models.Model):
    """
    Represents an individual product within a wishlist.
    """
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items', verbose_name="Wishlist")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlist_items', verbose_name="Product")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Added At")

    class Meta:
        verbose_name = 'Wishlist Item'
        verbose_name_plural = 'Wishlist Items'
        unique_together = ('wishlist', 'product') # A product can only be in a wishlist once
        ordering = ['-added_at'] # Newest items first

    def __str__(self):
        return f"{self.product.name} in {self.wishlist.user.username}'s Wishlist"
