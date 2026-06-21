# apps/reviews/admin.py

from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    # ⚡ Updated: Added Shop tracking and vendor response indicators to the layout grid
    list_display = ['product', 'shop', 'user', 'rating', 'has_merchant_reply', 'created_at']
    
    # ⚡ Updated: Added Shop filtering so platform managers can track a specific store's quality metrics
    list_filter = ['rating', 'shop', 'created_at', 'product__category']
    search_fields = ['product__name', 'shop__name', 'user__username', 'comment', 'vendor_reply']
    
    # 🛡️ Safety: Added shop to raw_id_fields to maintain lightning-fast admin loads as your marketplace grows
    raw_id_fields = ['product', 'shop', 'user']
    readonly_fields = ['created_at', 'updated_at', 'vendor_replied_at']

    fieldsets = (
        ("Core Review Details", {
            'fields': ('product', 'shop', 'user', 'rating', 'comment')
        }),
        ("Merchant Engagement", {
            'fields': ('vendor_reply', 'vendor_replied_at'),
            'description': "Public response parameters handled by store managers."
        }),
        ("System Timestamps", {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(boolean=True, description="Replied By Merchant")
    def has_merchant_reply(self, obj):
        """
        ⚡ Custom Grid Badge: Renders a true/false icon indicating 
        whether the vendor has publicly answered the customer.
        """
        return bool(obj.vendor_reply.strip())