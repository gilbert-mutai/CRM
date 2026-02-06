from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from .forms import SignUpForm


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    add_form = SignUpForm

    list_display = ("email", "first_name", "last_name", "is_staff", "is_2fa_enabled", "is_2fa_required")
    ordering = ("email",)
    search_fields = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_2fa_required",
                    "is_2fa_enabled",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important Dates", {"fields": ("last_login",)}),
    )

    # 👇 THIS is where we add 'groups' to the add form
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_2fa_required",
                    "groups",
                ),
            },
        ),
    )


admin.site.register(CustomUser, CustomUserAdmin)
