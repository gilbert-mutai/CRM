from django import forms
from .models import ThreeCX
from core.models import Client

# Allowed simultaneous call values
SC_VALUES = [1, 2, 4, 8, 16, 24, 32, 48, 64, 96, 128, 256]


class ClientNameOnlyChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.name


class BaseThreeCXForm(forms.ModelForm):
    client = ClientNameOnlyChoiceField(
        queryset=Client.objects.order_by("name"),
        widget=forms.Select(attrs={"class": "form-control", "id": "id_client"}),
        empty_label="Select Client",
    )

    sip_provider = forms.ChoiceField(
        choices=ThreeCX.SIP_PROVIDERS,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    fqdn = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "id": "id_fqdn"})
    )

    license_type = forms.ChoiceField(
        choices=ThreeCX.LICENSE_TYPES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    simultaneous_calls = forms.IntegerField(
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "id": "sc-counter",
                "min": 1,
                "max": max(SC_VALUES),
            }
        ),
        initial=4,
    )

    class Meta:
        model = ThreeCX
        fields = [
            "client",
            "fqdn",
            "sip_provider",
            "license_type",
            "simultaneous_calls",
        ]


class AddThreeCXForm(BaseThreeCXForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Remove labels and use placeholders instead
        self.fields["client"].label = ""
        self.fields["fqdn"].label = ""
        self.fields["sip_provider"].label = ""
        self.fields["license_type"].label = ""
        self.fields["simultaneous_calls"].label = ""

        self.fields["fqdn"].widget.attrs["placeholder"] = "FQDN"
        self.fields["simultaneous_calls"].widget.attrs[
            "placeholder"
        ] = "Simultaneous Calls"


class UpdateThreeCXForm(BaseThreeCXForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Use clear field labels (without placeholders)
        self.fields["client"].label = "Client"
        self.fields["fqdn"].label = "FQDN"
        self.fields["sip_provider"].label = "SIP Provider"
        self.fields["license_type"].label = "License Type"
        self.fields["simultaneous_calls"].label = "Simultaneous Calls"
        self.fields["fqdn"].widget.attrs.pop("placeholder", None)
        self.fields["simultaneous_calls"].widget.attrs.pop("placeholder", None)
