from django.db import models

# Create your models here.
# apps/promotions/models.py

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Coupon(models.Model):
    """
    Represents a discount coupon.
    """
    code = models.CharField(max_length=50, unique=True, verbose_name="Coupon Code")
    valid_from = models.DateTimeField(verbose_name="Valid From")
    valid_to = models.DateTimeField(verbose_name="Valid To")
    discount = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Discount Percentage"
    )
    active = models.BooleanField(default=True, verbose_name="Active")

    class Meta:
        verbose_name = 'Coupon'
        verbose_name_plural = 'Coupons'
        ordering = ['-valid_from']

    def __str__(self):
        return self.code
