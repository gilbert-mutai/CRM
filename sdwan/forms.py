from django import forms

from core.models import Client

from .models import SDWAN


class ClientNameOnlyChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.name


class BaseSDWANForm(forms.ModelForm):
    client = ClientNameOnlyChoiceField(
        queryset=Client.objects.order_by("name"),
        widget=forms.Select(attrs={"class": "form-control", "id": "id_client"}),
        empty_label="Select Client",
    )

    providers = forms.MultipleChoiceField(
        choices=SDWAN.PROVIDER_CHOICES,
        widget=forms.SelectMultiple(
            attrs={"class": "form-control", "id": "id_providers"}
        ),
    )

    class Meta:
        model = SDWAN
        fields = [
            "client",
            "providers",
        ]


class AddSDWANForm(BaseSDWANForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Hide labels and use placeholders instead
        for field in self.fields.values():
            field.label = ""
        self.fields["providers"].widget.attrs["data-placeholder"] = "Select Providers"


class UpdateSDWANForm(BaseSDWANForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Match the add form styling (labels hidden, rely on placeholders)
        for field in self.fields.values():
            field.label = ""
        self.fields["providers"].widget.attrs["data-placeholder"] = "Select Providers"
