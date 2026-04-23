from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, CareerProfile
from resumes.models import Resume



@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ("user", "file", "created_at")
    readonly_fields = ("created_at",)
    search_fields = ("user__email",)
    list_filter = ("created_at",)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):

    model = CustomUser

    # Admin table me kya kya show hoga
    list_display = (
        "email",
        "role",
        "name",
        "phone",
        "student_or_graduate",
        "current_degree",
        "last_degree",
        "company_name",
        "is_staff",
        "is_active",
    )

    # Admin edit page layout
    fieldsets = (
        (None, {"fields": ("email", "password")}),

        ("Basic Information", {
            "fields": (
                "role",
                "name",
                "phone",
                "address",
                "age",
            )
        }),

        ("Education Information", {
            "fields": (
                "student_or_graduate",
                "current_degree",
                "last_degree",
                "field_of_study",
            )
        }),

        ("Company Information (HR)", {
            "fields": (
                "company_name",
                "company_address",
                "designation",
            )
        }),

        ("Permissions", {
            "fields": (
                "is_staff",
                "is_active",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "role",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )

    search_fields = ("email", "name", "phone")
    list_filter = ("role", "student_or_graduate", "is_active")
    ordering = ("email",)


@admin.register(CareerProfile)
class CareerProfileAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "education_level",
        "career_level",
        "experience",
    )

    search_fields = ("user__email",)