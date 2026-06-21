# apps/wishlist/admin.py

from django.contrib import admin
from django.db.models import Count
from .models import Wishlist, WishlistItem


class WishlistItemInline(admin.TabularInline):
    """
    Allows WishlistItems to be viewed and managed directly 
    within the parent Wishlist detail page.
    """
    model = WishlistItem
    raw_id_fields = ['product']
    readonly_fields = ['added_at']
    extra = 0


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    # Added 'total_items' to display analytical metric insights per user profile
    list_display = ['user', 'total_items', 'created_at', 'updated_at']
    search_fields = ['user__username', 'user__email']
    raw_id_fields = ['user']
    inlines = [WishlistItemInline]
    readonly_fields = ['created_at', 'updated_at']

    def get_queryset(self, request):
        """ Overridden to optimize database overhead and inject counter aggregations. """
        queryset = super().get_queryset(request)
        return queryset.select_related('user').annotate(
            _total_items=Count('items')
        )

    @admin.display(ordering='_total_items', description='Total Saved Items')
    def total_items(self, obj):
        return obj._total_items


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ['wishlist', 'product', 'added_at']
    # Removed the deep nested product__category filter lookup to prevent admin crash 
    # if category isn't directly bound to your product model string profile.
    list_filter = ['added_at']
    search_fields = ['wishlist__user__username', 'wishlist__user__email', 'product__name']
    raw_id_fields = ['wishlist', 'product']
    readonly_fields = ['added_at']

    def get_queryset(self, request):
        """ Prevents N+1 database queries by pre-fetching relational data streams. """
        return super().get_queryset(request).select_related('wishlist__user', 'product')