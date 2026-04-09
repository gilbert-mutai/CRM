from django import forms
from .models import Client
from core.utils import validate_emails
from core.constants import SIGNATURE_CHOICES
from django.core.validators import RegexValidator


def _pop_field_name(pop_value):
    return f"pop_{pop_value.lower().replace('-', '_').replace(' ', '_')}"

# Label mapping for update form
LABEL_MAP = {
    "name": "Full Name or Company",
    "contact_person": "Contact Person (for Company)",
    "primary_email": "Primary Email Address",
    "secondary_email": "Secondary Email Address",
    "phone_number": "Phone Number",
    "client_type": "Client Type",
}

# Placeholder mapping for add form
PLACEHOLDER_MAP = {
    "name": "Full Name or Company",
    "contact_person": "Contact Person (for Company)",
    "primary_email": "Primary Email Address",
    "secondary_email": "Secondary Email Address",
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
            "primary_email",
            "secondary_email",
            "phone_number",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for pop_value, pop_label in Client.POP_CHOICES:
            self.fields[_pop_field_name(pop_value)] = forms.BooleanField(
                required=False,
                label=pop_label,
                widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
            )

        if self.instance and self.instance.pk:
            pops = set(self.instance.get_pops())
            for pop_value, _ in Client.POP_CHOICES:
                self.fields[_pop_field_name(pop_value)].initial = pop_value in pops

        self.regular_fields = [
            self[field_name]
            for field_name in self.fields
            if not field_name.startswith("pop_")
        ]
        self.pop_fields = [
            self[field_name]
            for field_name in self.fields
            if field_name.startswith("pop_")
        ]

    def save(self, commit=True):
        instance = super().save(commit=False)

        pops = [
            pop_value
            for pop_value, _ in Client.POP_CHOICES
            if self.cleaned_data.get(_pop_field_name(pop_value))
        ]
        instance.set_pops(pops)

        if commit:
            instance.save()
        return instance


class AddClientForm(BaseClientForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Use placeholders, remove labels; set appropriate widget classes
        for field_name, field in self.fields.items():
            # POP checkboxes: keep default styling
            if field_name.startswith('pop_'):
                field.widget = forms.CheckboxInput(attrs={"class": "form-check-input"})
                continue
                
            # Remove labels for add form (except POPs which need labels)
            field.label = ""

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
            # POP checkboxes: use checkbox styling
            if field_name.startswith('pop_'):
                field.widget = forms.CheckboxInput(attrs={"class": "form-check-input"})
                continue
                
            field.label = LABEL_MAP.get(
                field_name, field_name.replace("_", " ").capitalize()
            )

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
