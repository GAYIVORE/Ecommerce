# apps/products/models.py

from django.db import models
from django.urls import reverse # Used for getting URL of a product

class Category(models.Model):
    """
    Represents a product category.
    Categories can be nested (optional, but good for future).
    """
    name = models.CharField(max_length=255, unique=True, verbose_name="Category Name")
    slug = models.SlugField(max_length=255, unique=True, help_text="A unique slug for the category URL.")
    description = models.TextField(blank=True, verbose_name="Category Description")
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name="Category Image")

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """
        Returns the URL to a specific category.
        """
        return reverse('products:category_list', args=[self.slug]) # Placeholder, will update later for specific category view


class Product(models.Model):
    """
    Represents a single product in the store.
    """
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products', verbose_name="Product Category")
    name = models.CharField(max_length=255, unique=True, verbose_name="Product Name")
    slug = models.SlugField(max_length=255, unique=True, help_text="A unique slug for the product URL.")
    description = models.TextField(verbose_name="Product Description")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price (GHS)")
    stock = models.PositiveIntegerField(default=0, verbose_name="Available Stock")
    available = models.BooleanField(default=True, verbose_name="Is Available")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Updated")
    # Placeholder image for products without an image
    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True,
        verbose_name="Product Image",
        help_text="Upload a product image. If none, a placeholder will be used.",
    )

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at'] # Order by newest first
        indexes = [
            models.Index(fields=['-created_at']), # Index for faster ordering
            models.Index(fields=['slug']), # Index for faster slug lookups
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """
        Returns the URL to a specific product.
        """
        return reverse('products:product_detail', args=[self.slug])
