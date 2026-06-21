from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver

class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    Handles standard customer authentication alongside dedicated multi-vendor
    merchant role authorization and system admin variables.
    """
    
    

    class Roles(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Customer'
        VENDOR = 'VENDOR', 'Vendor'
        ADMIN = 'ADMIN', 'Administrator'

    # --- CRITICAL UPDATE: Enforce unique emails for e-commerce ---
    email = models.EmailField(unique=True)

    # System Identification Parameters
    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.CUSTOMER,
        help_text="Determines user clearance level and accessible dashboard panels."
    )
    
    # Core Metadata Fields 
    # (Removed unique=True from phone_number to prevent empty-string database crashes)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    marketing_opt_in = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['username']  # Standardizing on username to prevent missing index anomalies
        

    
    # High-Performance Logic Check Helpers
    @property
    def is_vendor(self):
        """Returns True if the account is an active marketplace merchant."""
        return self.role == self.Roles.VENDOR

    @property
    def is_customer(self):
        """Returns True if the account is a standard shopping consumer."""
        return self.role == self.Roles.CUSTOMER

    def __str__(self):
        # Graceful fallback logic string generation for system command utilities
        return self.email if self.email else f"@{self.username}"
    
    def delete(self, *args, **kwargs):
        # Explicitly clear relationships before the database tries to enforce the constraint
        self.groups.clear()
        self.user_permissions.clear()
        super().delete(*args, **kwargs) 
        
@receiver(pre_delete, sender=User)
def clear_user_permissions(sender, instance, **kwargs):
    instance.groups.clear()
    instance.user_permissions.clear()        