# apps/reviews/models.py

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.products.models import Product, Shop


class Review(models.Model):
    """
    Represents a customer product review within a multi-vendor structure.
    Enforces a single review per product limit per user and includes vendor response capability.
    """
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='reviews', 
        verbose_name="Product"
    )
    
    # ⚡ Added: Direct Shop relationship for optimal vendor dashboard metric generation
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="Vendor Shop",
        null=True,
        blank=True
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='reviews', 
        verbose_name="User"
    )
    
    # Cleaned: Enforced clean integer validation limits via native validators
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Rating (1-5)"
    )
    
    comment = models.TextField(verbose_name="Customer Comment")
    
    # ⚡ Added: Customer Engagement Tools for Merchants
    vendor_reply = models.TextField(
        blank=True, 
        verbose_name="Vendor Response",
        help_text="The merchant's public reply to this customer's review."
    )
    vendor_replied_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Reply Timestamp"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Updated")

    class Meta:
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        ordering = ['-created_at']
        
        # Enforces database-level uniqueness constraints
        unique_together = ('product', 'user')
        
        # Performance database indexes for fast storefront product loading
        indexes = [
            models.Index(fields=['product', 'rating']),
            models.Index(fields=['shop', 'rating']),
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.product.name} ({self.rating}★)"

    def save(self, *args, **kwargs):
        """
        ⚡ Automatic Injection: Captures the parent product's shop 
        on creation to keep denormalized indices accurately mapped.
        """
        if self.product and not self.shop:
            self.shop = self.product.shop
        super().save(*args, **kwargs)