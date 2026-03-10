from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.models import Client


def default_sip_provider_list():
    return ["None"]


class ThreeCX(models.Model):
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="threecx_created_records",
    )

    # Link to client
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="threecx_records"
    )

    # Dropdowns
    SIP_PROVIDERS = [
        ("None", "None"),
        ("Angani", "Angani"),
        ("Safaricom", "Safaricom"),
        ("Airtel", "Airtel"),
        ("JTL", "JTL"),
    ]
    sip_providers = models.JSONField(
        default=default_sip_provider_list,
        verbose_name="SIP Providers",
        help_text="Select one or more SIP providers",
    )

    fqdn = models.CharField(max_length=100, unique=True)

    LICENSE_TYPES = [
        ("3CX Basic", "3CX Basic"),
        ("3CX Pro", "3CX Pro"),
        ("3CX Enterprise", "3CX Enterprise"),
    ]

    license_type = models.CharField(max_length=20, choices=LICENSE_TYPES)
    SIMULTANEOUS_CALL_OPTIONS = [1, 2, 4, 8, 16, 24, 32, 48, 64, 96, 128, 256]

    simultaneous_calls = models.IntegerField(
        choices=[(val, f"{val} SC") for val in SIMULTANEOUS_CALL_OPTIONS],
        default=4,
    )

    # Audit trail
    last_updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="threecx_updated_records",
    )

    def clean(self):
        super().clean()

        if not isinstance(self.sip_providers, list):
            raise ValidationError({"sip_providers": "Invalid provider data."})

        allowed = {value for value, _ in self.SIP_PROVIDERS}
        cleaned = []

        for provider in self.sip_providers:
            if provider not in allowed:
                raise ValidationError(
                    {"sip_providers": f"'{provider}' is not an allowed SIP provider."}
                )

            if provider not in cleaned:
                cleaned.append(provider)

        self.sip_providers = cleaned

    @property
    def primary_sip_provider(self):
        return self.sip_providers[0] if self.sip_providers else None

    def get_sip_providers_display(self):
        return ", ".join(self.sip_providers) if self.sip_providers else "-"

    def __str__(self):
        primary = self.primary_sip_provider or "No SIP Provider"
        return f"{self.client.name} - {self.fqdn} ({primary})"

    class Meta:
        indexes = [
            models.Index(fields=["fqdn"]),
            models.Index(fields=["license_type"]),
        ]
