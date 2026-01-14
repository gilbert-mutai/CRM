from django.contrib import admin
from .models import ThreeCX


@admin.register(ThreeCX)
class ThreeCXAdmin(admin.ModelAdmin):
    # Displayed columns in list view
    list_display = (
        "get_client_name",
        "get_client_email",
        "get_client_phone",
        "sip_provider",
        "fqdn",
        "license_type",
        "created_at",
        "last_updated",
    )

    # Filter options in the sidebar
    list_filter = ("sip_provider", "license_type")

    # Searchable fields
    search_fields = ("client__name", "client__primary_email", "client__secondary_email", "client__phone_number")

    # Read-only timestamp fields
    readonly_fields = ("created_at", "last_updated")

    # Field layout in the form view
    fieldsets = (
        (None, {"fields": ("client", "sip_provider", "fqdn", "license_type")}),
        (
            "Timestamps",
            {
                "fields": ("created_at", "last_updated"),
            },
        ),
    )

    # Custom display methods
    @admin.display(description="Client Name")
    def get_client_name(self, obj):
        return obj.client.name

    @admin.display(description="Email Address")
    def get_client_email(self, obj):
        return obj.client.primary_email

    @admin.display(description="Phone Number")
    def get_client_phone(self, obj):
        return obj.client.phone_number

    # Automatically track creator and updater
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
