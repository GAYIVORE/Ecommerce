from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Extends standard Django UserAdmin structure to manage multi-vendor roles,
    contact tracking strings, and corporate asset permissions.
    """
    
    # Grid Table Columns Display Configurations
    list_display = ('username', 'email', 'role', 'phone_number', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active', 'marketing_opt_in')
    search_fields = ('username', 'email', 'phone_number')
    ordering = ('username',)

    # Detail view layout structure adjustments
    fieldsets = UserAdmin.fieldsets + (
        ('Marketplace Attributes', {
            'fields': ('role', 'phone_number', 'profile_picture', 'marketing_opt_in'),
            'classes': ('collapse',),  # Clean toggle expansion UI inside the layout panel
        }),
    )

    # Creation view framework adjustments
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Initial Clearance Assignment', {
            'fields': ('role', 'phone_number', 'marketing_opt_in'),
        }),
    )