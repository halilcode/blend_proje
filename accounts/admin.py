from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "get_full_name", "role", "department", "student_number", "is_active")
    list_filter = ("role", "department", "is_active", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email", "student_number")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Okul bilgileri", {"fields": ("role", "department", "student_number")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Okul bilgileri", {"fields": ("role", "department", "student_number")}),
    )
