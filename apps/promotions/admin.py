# apps/promotions/admin.py

from django.contrib import admin
from .models import Coupon

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'valid_from', 'valid_to', 'discount', 'active']
    list_filter = ['active', 'valid_from', 'valid_to']
    search_fields = ['code']
    actions = ['make_active', 'make_inactive']

    def make_active(self, request, queryset):
        queryset.update(active=True)
        self.message_user(request, "Selected coupons marked as active.")
    make_active.short_description = "Mark selected coupons as active"

    def make_inactive(self, request, queryset):
        queryset.update(active=False)
        self.message_user(request, "Selected coupons marked as inactive.")
    make_inactive.short_description = "Mark selected coupons as inactive"
