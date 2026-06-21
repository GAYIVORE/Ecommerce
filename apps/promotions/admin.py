# apps/promotions/admin.py

from django.contrib import admin
from django.utils import timezone
from .models import Coupon


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    # ⚡ Updated: Added Shop ownership scopes, operational usage data counters, and a validity status badge
    list_display = [
        'code', 'shop', 'discount', 'valid_from', 'valid_to', 
        'times_used', 'usage_limit', 'active', 'get_coupon_status'
    ]
    
    # ⚡ Added: Quick filter partitions to separate corporate global discounts from vendor boutique campaigns
    list_filter = ['active', 'valid_from', 'valid_to', 'shop']
    search_fields = ['code', 'shop__name']
    raw_id_fields = ['shop'] # Prevents database lag if your merchant pool scales to thousands
    list_editable = ['active'] # Instantly kill or activate a campaign from the grid dashboard
    actions = ['make_active', 'make_inactive']

    @admin.display(description="Current Status")
    def get_coupon_status(self, obj):
        """
        ⚡ Custom Grid Badge: Instantly shows why a coupon is offline (expired or out of stock)
        """
        now = timezone.now()
        if not obj.active:
            return "❌ Disabled"
        if obj.valid_from > now:
            return "⏳ Scheduled"
        if obj.valid_to < now:
            return "🥀 Expired"
        if obj.usage_limit is not None and obj.times_used >= obj.usage_limit:
            return "🛑 Fully Redeemed"
        return "✅ Live"

    @admin.action(description="Mark selected coupons as Active")
    def make_active(self, request, queryset):
        rows_updated = queryset.update(active=True)
        self.message_user(request, f"Successfully activated {rows_updated} coupon configurations.")

    @admin.action(description="Mark selected coupons as Inactive")
    def make_inactive(self, request, queryset):
        rows_updated = queryset.update(active=False)
        self.message_user(request, f"Successfully deactivated {rows_updated} coupon configurations.")