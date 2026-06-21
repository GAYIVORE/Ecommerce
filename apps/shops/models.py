from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify

class Shop(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('ACTIVE', 'Active'),
        ('SUSPENDED', 'Suspended'),
    ]

    # Use OneToOneField to enforce the business rule that one user has one shop
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='shop',
        verbose_name="Shop Owner"
    )
    phone_number = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        verbose_name="Contact Phone Number",
        help_text="Primary phone number to reach the vendor."
    )
    name = models.CharField(max_length=255, unique=True, verbose_name="Shop Name")
    slug = models.SlugField(max_length=255, unique=True, blank=True, help_text="A unique slug for the shop URL.")
    description = models.TextField(blank=True, null=True, verbose_name="Shop Description")
    image = models.ImageField(upload_to='shops/', blank=True, null=True, verbose_name="Shop Logo/Banner")
    
    # Status and visibility flags
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="Approval Status")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    is_deleted = models.BooleanField(default=False, verbose_name="Soft Deleted")
    
    # Financial/Admin fields
    paystack_subaccount_code = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="The merchant's unique Paystack Subaccount ID."
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Shop'
        verbose_name_plural = 'Shops'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active', 'is_deleted', 'status']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products:shop_storefront', args=[self.slug])