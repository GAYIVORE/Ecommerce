# apps/users/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


# Register your custom User model with the admin site
# You can customize UserAdmin if you add more fields to your User model
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # If you add custom fields to your User model,
    # you'll need to add them to fieldsets and add_fieldsets here.
    # Example:
    # fieldsets = UserAdmin.fieldsets + (
    #     (('Custom Fields', {'fields': ('phone_number', 'profile_picture',)}),)
    # )
    # add_fieldsets = UserAdmin.add_fieldsets + (
    #     (('Custom Fields', {'fields': ('phone_number', 'profile_picture',)}),)
    # )
    pass
