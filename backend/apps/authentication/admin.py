from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class MFPUserAdmin(UserAdmin):
    list_display = ("username", "email", "full_name", "role", "is_active", "last_login")
    list_filter = ("role", "is_active", "is_staff", "mfa_enabled")
    fieldsets = UserAdmin.fieldsets + (
        ("DFIR Profile", {"fields": ("full_name", "title", "phone", "role", "mfa_enabled", "last_login_ip")}),
    )
