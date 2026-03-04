from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from resumes.models import Resume

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ("user", "file", "created_at")  # table me columns
    readonly_fields = ("created_at",)  # created_at sirf read-only
    search_fields = ("user__email",)  # user email se search possible
    list_filter = ("created_at",)  # filter by date

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    
    model = CustomUser

    # Admin list view (table me kya dikhe)
    list_display = ("email", "role", "is_staff", "is_active")

    # Edit page layout
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Role Info", {"fields": ("role",)}),
        ("Permissions", {"fields": ("is_staff", "is_active", "is_superuser", "groups", "user_permissions")}),
    )

    # New user create form layout
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "role", "is_staff", "is_active"),
        }),
    )

    search_fields = ("email",)
    ordering = ("email",)