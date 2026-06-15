# apps/cart/admin.py

from django.contrib import admin
from .models import Cart, CartItem

class CartItemInline(admin.TabularInline):
    """
    Allows CartItems to be edited directly from the Cart admin page.
    """
    model = CartItem
    raw_id_fields = ['product'] # Use raw ID for product selection
    extra = 0 # Don't show extra empty forms by default

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_key', 'created_at', 'updated_at', 'get_total_price', 'get_total_quantity']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'session_key']
    inlines = [CartItemInline] # Include CartItemInline to manage items directly
    readonly_fields = ['created_at', 'updated_at', 'get_total_price', 'get_total_quantity']

    def get_total_price(self, obj):
        return obj.get_total_price
    get_total_price.short_description = 'Total Price (GHS)'

    def get_total_quantity(self, obj):
        return obj.get_total_quantity
    get_total_quantity.short_description = 'Total Quantity'

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity', 'get_total_item_price', 'created_at']
    list_filter = ['created_at', 'product__category']
    search_fields = ['product__name', 'cart__user__username', 'cart__session_key']
    readonly_fields = ['get_total_item_price']

    def get_total_item_price(self, obj):
        return obj.get_total_item_price
    get_total_item_price.short_description = 'Item Total (GHS)'
