# apps/products/models.py

from django.db import models
from django.urls import reverse
from django.conf import settings
from apps.shops.models import Shop
from django.utils.text import slugify
from django.utils import timezone
import datetime

class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-updating
    created_at and updated_at fields for all inherited entities.
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Updated")

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    """
    Represents a product category.
    """
    name = models.CharField(max_length=255, unique=True, verbose_name="Category Name")
    slug = models.SlugField(max_length=255, unique=True, help_text="A unique slug for the category URL.")
    description = models.TextField(blank=True, verbose_name="Category Description")
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name="Category Image")

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """
        Generates the canonical URL for routing customers directly to 
        the product list filtered by this category sector.
        """
        return reverse('products:product_list_by_category', kwargs={'category_slug': self.slug})


class Product(TimeStampedModel):
    """
    Represents a single product inside the store, protected with 
    enterprise compound indexes and soft deletion status metrics.
    """
    shop = models.ForeignKey(
        'shops.Shop', 
        on_delete=models.CASCADE, 
        related_name='products',
        null=True,
        blank=True,
        verbose_name="Associated Shop"
    )
    
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='products', 
        verbose_name="Product Category"
    )
    name = models.CharField(max_length=255, verbose_name="Product Name")
    slug = models.SlugField(max_length=255, unique=True, help_text="A unique slug for the product URL.")
    description = models.TextField(verbose_name="Product Description")
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Price (GHS)") 
    stock = models.PositiveIntegerField(default=0, verbose_name="Available Stock")
    available = models.BooleanField(default=True, verbose_name="Is Available")
    is_deleted = models.BooleanField(default=False, verbose_name="Soft Deleted")
    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True,
        verbose_name="Product Image",
        help_text="Upload a product image.",
    )
    
    @property
    def is_newly_restocked(self):
        # Returns True if updated in the last 24 hours and is in stock
        return self.stock > 0 and self.updated_at >= timezone.now() - datetime.timedelta(hours=24)

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['shop', '-created_at']),
            models.Index(fields=['available', 'is_deleted', '-created_at']),
        ]
        
    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products:product_detail', args=[self.slug])