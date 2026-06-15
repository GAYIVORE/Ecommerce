# apps/users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    This allows us to add custom fields to the user model later
    without having to migrate existing user data.
    """

    # Example of adding a custom field (optional for now, but good to have)
    # phone_number = models.CharField(max_length=15, blank=True, null=True, unique=True)
    # profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    # You can add more fields here as needed for your e-commerce platform,
    # e.g., default_shipping_address, marketing_opt_in, etc.

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['email']  # Order users by email by default

    def __str__(self):
        return self.email  # Use email as the primary string representation
