from django import forms
from .models import Client
from core.utils import validate_emails
from core.constants import SIGNATURE_CHOICES
from django.core.validators import RegexValidator

# Label mapping for update form
LABEL_MAP = {
    "name": "Full Name or Company",
    "contact_person": "Contact Person (for Company)",
    "email": "Email Address",
    "phone_number": "Phone Number",
    "client_type": "Client Type",
    "has_adc_services": "Has services in ADC",
    "has_icolo_services": "Has services in Icolo",
}

# Placeholder mapping for add form
PLACEHOLDER_MAP = {
    "name": "Full Name or Company",
    "contact_person": "Contact Person (for Company)",
    "email": "Email Address",
    "phone_number": "Phone Number",
    "client_type": "Select Client Type",
}


class BaseClientForm(forms.ModelForm):
    phone_number = forms.CharField(
        required=True,
        validators=[RegexValidator(r"^\+?\d{7,15}$", "Enter a valid phone number.")],
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Client
        fields = [
            "client_type",
            "name",
            "contact_person",
            "email",
            "phone_number",
            "has_adc_services",
            "has_icolo_services",
        ]


class AddClientForm(BaseClientForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Use placeholders, remove labels; set appropriate widget classes
        for field_name, field in self.fields.items():
            # Remove labels for add form
            field.label = ""
            # Checkbox fields: use Bootstrap checkbox input class
            if field_name in ("has_adc_services", "has_icolo_services"):
                field.widget = forms.CheckboxInput(attrs={"class": "form-check-input"})
                continue

            # Select fields: use form-select
            if field_name == "client_type":
                if hasattr(field.widget, "attrs"):
                    field.widget.attrs["class"] = "form-select"
                continue

            # Default: set placeholder and form-control
            if hasattr(field.widget, "attrs"):
                field.widget.attrs["placeholder"] = PLACEHOLDER_MAP.get(
                    field_name, field_name.replace("_", " ").capitalize()
                )
                field.widget.attrs["class"] = "form-control"


class ClientUpdateForm(BaseClientForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Use labels, remove placeholders; set appropriate widget classes
        for field_name, field in self.fields.items():
            field.label = LABEL_MAP.get(
                field_name, field_name.replace("_", " ").capitalize()
            )

            # Checkbox fields: keep label and use checkbox class
            if field_name in ("has_adc_services", "has_icolo_services"):
                field.widget = forms.CheckboxInput(attrs={"class": "form-check-input"})
                # ensure no placeholder for checkboxes
                continue

            # Select fields: use form-select
            if field_name == "client_type":
                if hasattr(field.widget, "attrs"):
                    field.widget.attrs.pop("placeholder", None)
                    field.widget.attrs["class"] = "form-select"
                continue

            # Default: remove placeholder and set form-control
            if hasattr(field.widget, "attrs"):
                field.widget.attrs.pop("placeholder", None)
                field.widget.attrs["class"] = "form-control"


class NotificationForm(forms.Form):
    bcc_emails = forms.CharField(widget=forms.HiddenInput())

    subject = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Subject"}
        ),
        label="",
    )

    signature = forms.ChoiceField(
        choices=SIGNATURE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="",
    )

    body = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "id": "editor"}), label=""
    )

    def clean_bcc_emails(self):
        raw = self.cleaned_data["bcc_emails"]
        valid_emails, invalid_emails = validate_emails(raw)
        if not valid_emails:
            raise forms.ValidationError("No valid Bcc email addresses provided.")
        self.cleaned_data["valid_emails"] = valid_emails
        self.cleaned_data["invalid_emails"] = invalid_emails
        return raw
