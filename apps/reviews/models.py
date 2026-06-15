# apps/reviews/models.py

from django.db import models
from django.conf import settings # To link to the custom User model
from apps.products.models import Product # To link to the Product model

class Review(models.Model):
    """
    Represents a customer review for a product.
    Includes a rating (1-5 stars) and a text comment.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name="Product")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews', verbose_name="User")
    rating = models.PositiveIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)], # Rating from 1 to 5
        verbose_name="Rating"
    )
    comment = models.TextField(blank=True, verbose_name="Comment")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Updated")

    class Meta:
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        ordering = ['-created_at'] # Newest reviews first
        unique_together = ('product', 'user') # A user can only submit one review per product

    def __str__(self):
        return f"Review for {self.product.name} by {self.user.username} - {self.rating} stars"
