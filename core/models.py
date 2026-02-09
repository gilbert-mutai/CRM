from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator


class Client(models.Model):
    INDIVIDUAL = "Individual"
    COMPANY = "Company"
    CLIENT_TYPE_CHOICES = [
        (INDIVIDUAL, "Individual"),
        (COMPANY, "Company"),
    ]

    # Point of Presence choices
    POP_ADC_NBO = "ADC NBO"
    POP_ICOLO_NBO = "Icolo NBO"
    POP_ICOLO_MBA = "Icolo MBA"
    POP_IXAFRICA_NBO = "IXAfrica NBO"
    POP_RAXIO_UG = "Raxio UG"
    POP_TANZANIA = "Tanzania"
    
    POP_CHOICES = [
        (POP_ADC_NBO, "ADC NBO"),
        (POP_ICOLO_NBO, "Icolo NBO"),
        (POP_ICOLO_MBA, "Icolo MBA"),
        (POP_IXAFRICA_NBO, "IXAfrica NBO"),
        (POP_RAXIO_UG, "Raxio UG"),
        (POP_TANZANIA, "Tanzania"),
    ]

    client_type = models.CharField(
        max_length=20, choices=CLIENT_TYPE_CHOICES, default=COMPANY
    )
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    primary_email = models.EmailField()
    secondary_email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r"^\+?1?\d{9,15}$",
                message="Phone number must be in the format: '+999999999'. Up to 15 digits allowed.",
            )
        ],
    )

    # Point of Presence - stored as comma-separated values
    point_of_presence = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Point of Presence locations (comma-separated)"
    )
    
    # Legacy fields - kept for backward compatibility during migration
    has_adc_services = models.BooleanField(
        default=False, help_text="Has services in ADC data center"
    )
    has_icolo_services = models.BooleanField(
        default=False, help_text="Has services in Icolo data center"
    )

    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="clients_created",
    )
    last_updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="clients_updated",
    )

    def clean(self):
        super().clean()
        if self.client_type == self.COMPANY and not self.contact_person:
            raise ValidationError(
                {"contact_person": "Contact person is required for company clients."}
            )

    def __str__(self):
        return f"{self.name} ({self.primary_email})"

    def get_pops(self):
        """Returns list of Point of Presence locations"""
        if not self.point_of_presence:
            return []
        return [pop.strip() for pop in self.point_of_presence.split(",") if pop.strip()]
    
    def set_pops(self, pop_list):
        """Set Point of Presence from a list"""
        self.point_of_presence = ",".join(pop_list) if pop_list else ""
    
    def has_pop(self, pop_value):
        """Check if client has a specific POP"""
        return pop_value in self.get_pops()

    @property
    def data_centers(self):
        """Legacy property for backward compatibility"""
        return self.get_pops()

    def data_centers_display(self):
        """Display POPs as comma-separated string"""
        pops = self.get_pops()
        return ", ".join(pops) if pops else "None"

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["primary_email"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "primary_email"], name="unique_client_name_email"
            )
        ]
