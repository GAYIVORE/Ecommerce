# apps/products/admin.py

from django.contrib import admin
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)} # Automatically populate slug from name
    search_fields = ['name']
    list_filter = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'price', 'stock', 'available', 'category', 'created_at', 'updated_at']
    list_filter = ['available', 'created_at', 'updated_at', 'category']
    list_editable = ['price', 'stock', 'available'] # Allow direct editing from list view
    prepopulated_fields = {'slug': ('name',)}
    raw_id_fields = ['category'] # Use a raw ID field for category for large number of categories
    search_fields = ['name', 'description']
    date_hierarchy = 'created_at' # Add a date drill-down navigation
    ordering = ['-created_at']
