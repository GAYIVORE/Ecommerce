# apps/orders/admin.py

from django.contrib import admin
from .models import ShippingAddress, Order, SubOrder, OrderItem


@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'address_line1', 'city', 'country', 'phone_number', 'is_default']
    list_filter = ['country', 'is_default']
    search_fields = ['user__username', 'full_name', 'address_line1', 'city', 'phone_number']
    raw_id_fields = ['user']
    list_editable = ['is_default']


class OrderItemInline(admin.TabularInline):
    """
    Allows OrderItems to be edited/viewed from the Order panels.
    """
    model = OrderItem
    raw_id_fields = ['product', 'sub_order']
    readonly_fields = ['product_name', 'product_price', 'get_item_total']
    extra = 0

    def get_item_total(self, obj):
        return obj.get_item_total
    get_item_total.short_description = 'Item Total (GHS)'


class SubOrderInline(admin.TabularInline):
    """
    ⚡ Added: Displays vendor split partitions directly inside the Global Order page.
    """
    model = SubOrder
    raw_id_fields = ['shop']
    readonly_fields = ['sub_total', 'created_at']
    extra = 0
    show_change_link = True # Adds a shortcut link straight to that vendor's detailed sub-order page


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'order_date', 'total_amount', 'payment_method', 'payment_status', 'shipping_city']
    list_filter = ['payment_status', 'payment_method', 'order_date']
    search_fields = ['user__username', 'id', 'transaction_id', 'shipping_full_name']
    readonly_fields = ['order_date', 'updated_at', 'total_amount', 'transaction_id']
    
    # ⚡ Render both the split vendor headers and the item rows
    inlines = [SubOrderInline, OrderItemInline]
    
    fieldsets = (
        (None, {
            'fields': ('user', 'payment_method', 'payment_status', 'total_amount', 'transaction_id')
        }),
        ('Shipping Information', {
            'fields': (
                'shipping_full_name', 'shipping_address_line1', 'shipping_address_line2',
                'shipping_city', 'shipping_state', 'shipping_postal_code',
                'shipping_country', 'shipping_phone_number', 'shipping_address'
            ),
            'description': 'Snapshot of shipping address captured at checkout initialization.'
        }),
        ('Dates', {
            'fields': ('order_date', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'shipping_address')


@admin.register(SubOrder)
class SubOrderAdmin(admin.ModelAdmin):
    """
    ⚡ Added: Dedicated panel for managing localized shop fulfillment workflows.
    """
    list_display = ['id', 'parent_order', 'get_customer', 'shop', 'status', 'sub_total', 'shipping_cost', 'tracking_number', 'updated_at']
    list_filter = ['status', 'created_at', 'shop']
    search_fields = ['id', 'parent_order__id', 'shop__name', 'tracking_number', 'parent_order__user__username']
    list_editable = ['status', 'tracking_number'] # Fast tracking pipeline updates right from the dashboard grid
    raw_id_fields = ['parent_order', 'shop']
    inlines = [OrderItemInline]

    def get_queryset(self, request):
        # Prevent severe query leaks across nested tables
        return super().get_queryset(request).select_related('parent_order__user', 'shop')

    def get_customer(self, obj):
        return obj.parent_order.user.username if obj.parent_order.user else "Guest"
    get_customer.short_description = 'Customer'