from django.contrib import admin

from .models import EarningTransaction, QuickCashOffer, Service, ServiceBooking


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'provider', 'category', 'price', 'is_active', 'created_at')
    list_filter = ('category', 'is_active')
    search_fields = ('title', 'description', 'provider__email', 'provider__username')


@admin.register(ServiceBooking)
class ServiceBookingAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'service', 'customer', 'status', 'amount', 'provider_earning', 'created_at'
    )
    list_filter = ('status',)
    search_fields = ('service__title', 'customer__email', 'customer__username')
    actions = ['mark_completed_action']

    @admin.action(description='Mark selected bookings as completed')
    def mark_completed_action(self, request, queryset):
        for booking in queryset:
            booking.mark_completed()


@admin.register(QuickCashOffer)
class QuickCashOfferAdmin(admin.ModelAdmin):
    list_display = ('title', 'offer_type', 'earning_range', 'is_active', 'submitted_by')
    list_filter = ('offer_type', 'is_active')
    search_fields = ('title', 'description')


@admin.register(EarningTransaction)
class EarningTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'transaction_type', 'status', 'created_at')
    list_filter = ('transaction_type', 'status')
    search_fields = ('user__email', 'user__username', 'description')
