from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from core.models import Client


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
    sip_provider = models.CharField(max_length=20, choices=SIP_PROVIDERS, default="None")

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

        duplicate_qs = ThreeCX.objects.filter(client=self.client)
        if self.pk:
            duplicate_qs = duplicate_qs.exclude(pk=self.pk)

        if duplicate_qs.exists():
            raise ValidationError(
                {"client": "A 3CX record already exists for this client."}
            )

    def __str__(self):
        return f"{self.client.name} - {self.fqdn}"

    class Meta:
        indexes = [
            models.Index(fields=["fqdn"]),
            models.Index(fields=["sip_provider"]),
            models.Index(fields=["license_type"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["client"], name="unique_threecx_client")
        ]
