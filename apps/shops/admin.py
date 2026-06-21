from django.contrib import admin
from .models import Shop
from .forms import ShopForm  # Importing your actual custom form layout

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    # Force Django Admin to use your cleanly styled form from forms.py
    form = ShopForm

    list_display = ('name', 'owner', 'status', 'is_active', 'is_deleted', 'created_at')
    list_filter = ('status', 'is_active', 'is_deleted', 'created_at')
    search_fields = ('name', 'owner__username', 'owner__email', 'description')
    
    # Kept as read-only since your model's save() method handles auto-generation perfectly
    readonly_fields = ('slug', 'created_at', 'updated_at')
    
    actions = ['approve_shops', 'suspend_shops', 'soft_delete_shops']
    list_editable = ['is_active', 'is_deleted'] 
    raw_id_fields = ['owner'] 
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    # --- Admin Actions ---
    @admin.action(description="Approve selected shop applications")
    def approve_shops(self, request, queryset):
        updated = queryset.update(status='ACTIVE', is_active=True)
        self.message_user(request, f"{updated} shop(s) successfully approved and activated.")

    @admin.action(description="Suspend selected shops")
    def suspend_shops(self, request, queryset):
        updated = queryset.update(status='SUSPENDED', is_active=False)
        self.message_user(request, f"{updated} shop(s) successfully suspended and deactivated.")

    @admin.action(description="Soft-delete selected shops")
    def soft_delete_shops(self, request, queryset):
        updated = queryset.update(is_deleted=True, is_active=False)
        self.message_user(request, f"{updated} shop(s) marked as soft-deleted.")