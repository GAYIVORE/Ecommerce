# apps/orders/admin.py

from django.contrib import admin
from .models import ShippingAddress, Order, OrderItem

@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'address_line1', 'city', 'country', 'phone_number', 'is_default']
    list_filter = ['country', 'is_default']
    search_fields = ['user__username', 'full_name', 'address_line1', 'city', 'phone_number']
    raw_id_fields = ['user']
    list_editable = ['is_default']


class OrderItemInline(admin.TabularInline):
    """
    Allows OrderItems to be edited directly from the Order admin page.
    """
    model = OrderItem
    raw_id_fields = ['product']
    readonly_fields = ['product_name', 'product_price', 'get_item_total'] # These are snapshots
    extra = 0 # Don't show extra empty forms by default

    def get_item_total(self, obj):
        return obj.get_item_total
    get_item_total.short_description = 'Item Total (GHS)'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'order_date', 'total_amount', 'status', 'payment_status', 'shipping_city', 'shipping_country']
    list_filter = ['status', 'payment_status', 'order_date', 'updated_at']
    search_fields = ['user__username', 'id', 'transaction_id', 'shipping_city', 'shipping_full_name']
    readonly_fields = ['order_date', 'updated_at', 'total_amount', 'transaction_id'] # These are set automatically
    inlines = [OrderItemInline]
    fieldsets = (
        (None, {
            'fields': ('user', 'status', 'payment_status', 'total_amount', 'transaction_id')
        }),
        ('Shipping Information', {
            'fields': (
                'shipping_full_name', 'shipping_address_line1', 'shipping_address_line2',
                'shipping_city', 'shipping_state', 'shipping_postal_code',
                'shipping_country', 'shipping_phone_number', 'shipping_address' # Link to saved address
            ),
            'description': 'Snapshot of shipping address at the time of order.'
        }),
        ('Dates', {
            'fields': ('order_date', 'updated_at'),
            'classes': ('collapse',), # Collapse this section by default
        }),
    )

    def get_queryset(self, request):
        # Optimize queryset for admin list view
        return super().get_queryset(request).select_related('user', 'shipping_address')

    def save_model(self, request, obj, form, change):
        # When saving an order in admin, ensure total_amount is calculated if not set
        if not obj.total_amount:
            obj.total_amount = obj.get_total_cost()
        super().save_model(request, obj, form, change)
