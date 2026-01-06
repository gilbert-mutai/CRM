from django import forms
from .models import Client
from core.utils import validate_emails
from core.constants import SIGNATURE_CHOICES
from django.core.validators import RegexValidator

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
    
    # Point of Presence checkboxes
    pop_adc_nbo = forms.BooleanField(required=False, label="ADC NBO")
    pop_icolo_nbo = forms.BooleanField(required=False, label="Icolo NBO")
    pop_icolo_mbo = forms.BooleanField(required=False, label="Icolo MBO")
    pop_ixafrica_nbo = forms.BooleanField(required=False, label="IXAfrica NBO")
    pop_raxio_ug = forms.BooleanField(required=False, label="Raxio UG")
    pop_tanzania = forms.BooleanField(required=False, label="Tanzania")

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
        
        # Initialize POP checkboxes from instance
        if self.instance and self.instance.pk:
            pops = self.instance.get_pops()
            self.fields['pop_adc_nbo'].initial = Client.POP_ADC_NBO in pops
            self.fields['pop_icolo_nbo'].initial = Client.POP_ICOLO_NBO in pops
            self.fields['pop_icolo_mbo'].initial = Client.POP_ICOLO_MBO in pops
            self.fields['pop_ixafrica_nbo'].initial = Client.POP_IXAFRICA_NBO in pops
            self.fields['pop_raxio_ug'].initial = Client.POP_RAXIO_UG in pops
            self.fields['pop_tanzania'].initial = Client.POP_TANZANIA in pops
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Save POPs from checkboxes
        pops = []
        if self.cleaned_data.get('pop_adc_nbo'):
            pops.append(Client.POP_ADC_NBO)
        if self.cleaned_data.get('pop_icolo_nbo'):
            pops.append(Client.POP_ICOLO_NBO)
        if self.cleaned_data.get('pop_icolo_mbo'):
            pops.append(Client.POP_ICOLO_MBO)
        if self.cleaned_data.get('pop_ixafrica_nbo'):
            pops.append(Client.POP_IXAFRICA_NBO)
        if self.cleaned_data.get('pop_raxio_ug'):
            pops.append(Client.POP_RAXIO_UG)
        if self.cleaned_data.get('pop_tanzania'):
            pops.append(Client.POP_TANZANIA)
        
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
