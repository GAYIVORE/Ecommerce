# apps/promotions/models.py

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from apps.products.models import Shop


class Coupon(models.Model):
    """
    Represents a multi-vendor flexible discount coupon. 
    Can be platform-wide or isolated to a specific vendor shop catalog.
    """
    code = models.CharField(max_length=50, unique=True, verbose_name="Coupon Code")
    
    # ⚡ Added: Multi-vendor scoping capability
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name='coupons',
        null=True,
        blank=True,
        verbose_name="Vendor Shop Scope",
        help_text="Leave blank for platform-wide coupons that apply across all items."
    )
    
    valid_from = models.DateTimeField(verbose_name="Valid From")
    valid_to = models.DateTimeField(verbose_name="Valid To")
    
    discount = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        verbose_name="Discount Percentage"
    )
    
    # ⚡ Added: Financial safeguards and usage limiting
    usage_limit = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name="Max Total Usages",
        help_text="Total number of times this coupon can be redeemed across all consumers."
    )
    times_used = models.PositiveIntegerField(
        default=0, 
        verbose_name="Current Usage Count"
    )
    
    active = models.BooleanField(default=True, verbose_name="Active State")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Coupon'
        verbose_name_plural = 'Coupons'
        ordering = ['-valid_from']
        indexes = [
            models.Index(fields=['code', 'active']),
            models.Index(fields=['valid_from', 'valid_to']),
        ]

    def __str__(self):
        if self.shop:
            return f"{self.code} [{self.shop.name} Only] - {self.discount}%"
        return f"{self.code} [Global] - {self.discount}%"

    @property
    def is_valid(self):
        """
        ⚡ Evaluates general timeline window sanity checks and capacity ceilings.
        """
        now = timezone.now()
        timeline_valid = self.valid_from <= now <= self.valid_to
        
        if self.usage_limit is not None:
            capacity_valid = self.times_used < self.usage_limit
        else:
            capacity_valid = True
            
        return self.active and timeline_valid and capacity_valid