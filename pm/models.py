from django.db import models
from django.utils import timezone
from django.conf import settings
from core.models import Client


class Project(models.Model):
    STATUS_COMPLETED = "Completed"
    STATUS_PENDING = "Pending"

    STATUS_CHOICES = [
        (STATUS_COMPLETED, "Completed"),
        (STATUS_PENDING, "Pending"),
    ]

    CERT_SHARED = "Shared"
    CERT_PENDING = "Pending"

    CERTIFICATE_CHOICES = [
        (CERT_SHARED, "Shared"),
        (CERT_PENDING, "Pending"),
    ]

    customer_name = models.ForeignKey(Client, on_delete=models.CASCADE)
    project_title = models.CharField(max_length=255)
    service_description = models.TextField()
    date_of_request = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    date_of_completion = models.DateTimeField(null=True, blank=True)
    job_completion_certificate = models.CharField(
        max_length=10, choices=CERTIFICATE_CHOICES, default=CERT_PENDING
    )

    engineer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={"groups__name": "Engineers"},
    )

    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="projects_created",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="projects_updated",
    )

    def __str__(self):
        return f"Project: {self.customer_name.name} - {self.status}"

    def clean(self):
        super().clean()

        if self.project_title:
            self.project_title = self.project_title.strip()

    @property
    def is_completed(self):
        return self.status == self.STATUS_COMPLETED

    class Meta:
        ordering = ["-date_of_request"]
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["customer_name"]),
        ]
