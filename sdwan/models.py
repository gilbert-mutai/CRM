from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models.functions import Lower, Trim
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

    account_number = models.CharField(
        max_length=50,
        verbose_name="Account Number",
    )

    PROVIDER_CHOICES = [
        ("Safaricom", "Safaricom"),
        ("Liquid Telecom", "Liquid Telecom"),
        ("Telkom", "Telkom"),
        ("MTN", "MTN"),
        ("Other", "Other"),
    ]

    provider = models.CharField(
        max_length=50,
        choices=PROVIDER_CHOICES,
        verbose_name="Provider",
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

        if self.account_number:
            self.account_number = self.account_number.strip()

        if self.client_id and self.account_number:
            duplicate_qs = (
                SDWAN.objects.annotate(normalized_account=Lower(Trim("account_number")))
                .filter(
                    client=self.client,
                    normalized_account=self.account_number.lower(),
                )
            )
            if self.pk:
                duplicate_qs = duplicate_qs.exclude(pk=self.pk)

            if duplicate_qs.exists():
                raise ValidationError(
                    {
                        "account_number": (
                            "This account number already exists for the selected client."
                        )
                    }
                )

    def __str__(self):
        return f"{self.client.name} - {self.provider} ({self.account_number})"

    class Meta:
        indexes = [
            models.Index(fields=["account_number"]),
            models.Index(fields=["provider"]),
        ]
        constraints = [
            models.UniqueConstraint(
                "client",
                Lower(Trim("account_number")),
                name="unique_client_account_number_ci",
            )
        ]
        ordering = ["-last_updated"]
        verbose_name = "SD-WAN"
        verbose_name_plural = "SD-WAN Records"
