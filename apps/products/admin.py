# apps/products/admin.py

from django.contrib import admin
from .models import Category, Shop, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Upgraded to manage complex multi-vendor details, cross-shop optimization,
    and soft-deletion monitoring.
    """
    list_display = [
        'name', 'shop', 'price', 'stock', 'available', 
        'is_deleted', 'category', 'created_at'
    ]
    list_filter = ['available', 'is_deleted', 'shop', 'category', 'created_at']
    list_editable = ['price', 'stock', 'available', 'is_deleted'] # Live marketplace modifications
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description', 'shop__name']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    # ⚡ CRITICAL ENTERPRISE OPTIMIZATION
    raw_id_fields = ['category', 'shop'] # Swaps laggy select dropdowns for fast search popups
    
    def get_queryset(self, request):
        """
        Optimizes database performance by pre-fetching foreign key mappings.
        Prevents N+1 query overhead in the admin listing.
        """
        return super().get_queryset(request).select_related('shop', 'category')