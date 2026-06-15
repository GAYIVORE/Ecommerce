# apps/wishlist/admin.py

from django.contrib import admin
from .models import Wishlist, WishlistItem

class WishlistItemInline(admin.TabularInline):
    """
    Allows WishlistItems to be edited directly from the Wishlist admin page.
    """
    model = WishlistItem
    raw_id_fields = ['product']
    readonly_fields = ['added_at']
    extra = 0 # Don't show extra empty forms by default

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'updated_at']
    search_fields = ['user__username']
    raw_id_fields = ['user']
    inlines = [WishlistItemInline]
    readonly_fields = ['created_at', 'updated_at']

@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ['wishlist', 'product', 'added_at']
    list_filter = ['added_at', 'product__category']
    search_fields = ['wishlist__user__username', 'product__name']
    raw_id_fields = ['wishlist', 'product']
    readonly_fields = ['added_at']
