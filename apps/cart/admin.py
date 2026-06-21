# apps/cart/admin.py

from django.contrib import admin
from .models import Cart, CartItem

class CartItemInline(admin.TabularInline):
    """
    Allows CartItems to be edited directly from the Cart admin page.
    """
    model = CartItem
    raw_id_fields = ['product'] 
    extra = 0 
    # ⚡ Added fields layout to clearly display vendor tracking on the inline sub-rows
    readonly_fields = ['get_item_vendor']
    fields = ['product', 'get_item_vendor', 'quantity']

    def get_item_vendor(self, obj):
        if obj.product and obj.product.shop:
            return obj.product.shop.name
        return "N/A"
    get_item_vendor.short_description = 'Vendor / Shop'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_key', 'unique_shops_count', 'get_total_quantity', 'get_total_price', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'session_key']
    inlines = [CartItemInline] 
    readonly_fields = ['created_at', 'updated_at', 'get_total_price', 'get_total_quantity', 'unique_shops_count']

    def get_queryset(self, request):
        """⚡ Eagerly load user profiles to prevent massive N+1 database queries on list layouts."""
        return super().get_queryset(request).select_related('user')

    def get_total_price(self, obj):
        return obj.get_total_price
    get_total_price.short_description = 'Total Price (GHS)'

    def get_total_quantity(self, obj):
        return obj.get_total_quantity
    get_total_quantity.short_description = 'Total Quantity'
    
    def unique_shops_count(self, obj):
        return obj.unique_shops_count
    unique_shops_count.short_description = 'Involved Vendors'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    # ⚡ Added 'get_product_vendor' so admins can instantly identify merchants on global audit panels
    list_display = ['id', 'cart', 'product', 'get_product_vendor', 'quantity', 'get_total_item_price', 'created_at']
    list_filter = ['created_at', 'product__shop', 'product__category']
    search_fields = ['product__name', 'cart__user__username', 'cart__session_key']
    readonly_fields = ['get_total_item_price']
    raw_id_fields = ['cart', 'product']

    def get_queryset(self, request):
        """⚡ Optimize query processing using compound foreign target selection paths."""
        return super().get_queryset(request).select_related('cart__user', 'product__shop')

    def get_total_item_price(self, obj):
        return obj.get_total_item_price
    get_total_item_price.short_description = 'Item Total (GHS)'

    def get_product_vendor(self, obj):
        return obj.product.shop.name
    get_product_vendor.short_description = 'Vendor'