from django import forms
from django.contrib import admin

from .models import ThreeCX


class SIPProviderFilter(admin.SimpleListFilter):
    title = "SIP Provider"
    parameter_name = "sip_provider"

    def lookups(self, request, model_admin):
        return ThreeCX.SIP_PROVIDERS

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(sip_providers__contains=[value])
        return queryset


class ThreeCXAdminForm(forms.ModelForm):
    sip_providers = forms.MultipleChoiceField(
        choices=ThreeCX.SIP_PROVIDERS,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = ThreeCX
        fields = "__all__"


@admin.register(ThreeCX)
class ThreeCXAdmin(admin.ModelAdmin):
    form = ThreeCXAdminForm
    # Displayed columns in list view
    list_display = (
        "get_client_name",
        "get_client_email",
        "get_client_phone",
        "get_sip_providers",
        "fqdn",
        "license_type",
        "created_at",
        "last_updated",
    )

    # Filter options in the sidebar
    list_filter = (SIPProviderFilter, "license_type")

    # Searchable fields
    search_fields = ("client__name", "client__primary_email", "client__secondary_email", "client__phone_number")

    # Read-only timestamp fields
    readonly_fields = ("created_at", "last_updated")

    # Field layout in the form view
    fieldsets = (
        (None, {"fields": ("client", "sip_providers", "fqdn", "license_type")}),
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

    @admin.display(description="SIP Providers")
    def get_sip_providers(self, obj):
        return obj.get_sip_providers_display()

    # Automatically track creator and updater
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
