from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.models import Client


class SDWAN(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sdwan_created_records",
        verbose_name="Created By",
    )

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="sdwan_records",
        verbose_name="Client",
    )

    PROVIDER_CHOICES = [
        ("Hirani", "Hirani"),
        ("JTL", "JTL"),
        ("Zuku", "Zuku"),
        ("VGG", "VGG"),
        ("Safaricom", "Safaricom"),
        ("Simbanet", "Simbanet"),
        ("Fon", "Fon"),
        ("Vilcom", "Vilcom"),
        ("Syokinet", "Syokinet"),
    ]

    providers = models.JSONField(
        default=list,
        verbose_name="Providers",
        help_text="Select one or more providers",
    )

    last_updated = models.DateTimeField(auto_now=True, verbose_name="Last Updated")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sdwan_updated_records",
        verbose_name="Updated By",
    )

    def clean(self):
        super().clean()

        if not isinstance(self.providers, list):
            raise ValidationError({"providers": "Invalid provider data."})

        allowed = {choice for choice, _ in self.PROVIDER_CHOICES}
        cleaned = []
        for provider in self.providers:
            if provider not in allowed:
                raise ValidationError(
                    {"providers": f"'{provider}' is not an allowed provider."}
                )
            if provider not in cleaned:
                cleaned.append(provider)

        self.providers = cleaned

    @property
    def primary_provider(self):
        return self.providers[0] if self.providers else None

    def get_providers_display(self):
        return ", ".join(self.providers) if self.providers else "-"

    def __str__(self):
        provider_label = self.primary_provider or "No Provider"
        return f"{self.client.name} - {provider_label}"

    class Meta:
        ordering = ["-last_updated"]
        verbose_name = "SD-WAN"
        verbose_name_plural = "SD-WAN Records"
