from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.models.functions import Lower, Trim
from core.models import Client


class VeeamJob(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="veeam_created_records",
        verbose_name="Created By",
    )

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="veeam_records",
        verbose_name="Client",
    )

    SITE_CHOICES = [
        ("Angani ADC", "Angani ADC"),
        ("Angani Icolo", "Angani Icolo"),
    ]

    OS_CHOICES = [
        ("Linux", "Linux"),
        ("Windows", "Windows"),
    ]

    MANAGED_BY_CHOICES = [
        ("Backup Agent", "Backup Agent"),
        ("VBR", "VBR"),
    ]

    JOB_STATUS_CHOICES = [
        ("Running", "Running"),
        ("Success", "Success"),
        ("Failed", "Failed"),
    ]

    site = models.CharField(max_length=50, choices=SITE_CHOICES, verbose_name="Site")
    computer_name = models.CharField(max_length=100, verbose_name="Computer Name")
    tag = models.CharField(max_length=100, blank=True, verbose_name="Tag")
    os = models.CharField(
        max_length=20, choices=OS_CHOICES, verbose_name="Operating System"
    )
    managed_by = models.CharField(
        max_length=20, choices=MANAGED_BY_CHOICES, verbose_name="Managed By"
    )
    job_status = models.CharField(
        max_length=20,
        choices=JOB_STATUS_CHOICES,
        default="Running",
        verbose_name="Job Status",
    )
    engineer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="veeam_jobs",
        verbose_name="Engineer",
        limit_choices_to={"groups__name": "Engineers"},
    )
    comment = models.TextField(blank=True, null=True, verbose_name="Comment")

    last_updated = models.DateTimeField(auto_now=True, verbose_name="Last Updated")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="veeam_updated_records",
        verbose_name="Updated By",
    )

    def clean(self):
        super().clean()

        if self.computer_name:
            self.computer_name = self.computer_name.strip()

        if self.client_id and self.computer_name:
            duplicate_qs = (
                VeeamJob.objects.annotate(
                    normalized_computer_name=Lower(Trim("computer_name"))
                )
                .filter(
                    client=self.client,
                    normalized_computer_name=self.computer_name.lower(),
                )
            )
            if self.pk:
                duplicate_qs = duplicate_qs.exclude(pk=self.pk)

            if duplicate_qs.exists():
                raise ValidationError(
                    {
                        "computer_name": (
                            "This computer name already exists for the selected client."
                        )
                    }
                )

    def __str__(self):
        return f"{self.client.name} - {self.computer_name}"

    class Meta:
        indexes = [
            models.Index(fields=["computer_name"]),
            models.Index(fields=["site"]),
            models.Index(fields=["os"]),
            models.Index(fields=["managed_by"]),
            models.Index(fields=["job_status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                "client",
                Lower(Trim("computer_name")),
                name="unique_client_computer_ci",
            )
        ]
        ordering = ["-last_updated"]
        verbose_name = "Veeam Job"
        verbose_name_plural = "Veeam Jobs"
