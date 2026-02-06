from django import forms
from django.contrib.auth import get_user_model
from core.models import Client
from .models import Project

User = get_user_model()


# Custom field to display only the client name
class ClientNameOnlyChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.name


# Custom field to display engineer's full name
class EngineerNameOnlyChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        full_name = f"{obj.first_name} {obj.last_name}".strip()
        if full_name:
            return full_name
        username = getattr(obj, "username", "")
        return username or obj.email


# Shared Base Form
class BaseProjectForm(forms.ModelForm):
    customer_name = ClientNameOnlyChoiceField(
        queryset=Client.objects.order_by("name"),
        widget=forms.Select(attrs={"class": "form-control", "id": "id_customer_name"}),
    )

    project_title = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    service_description = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
    )

    job_completion_certificate = forms.ChoiceField(
        choices=Project.CERTIFICATE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    status = forms.ChoiceField(
        choices=Project.STATUS_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    engineer = EngineerNameOnlyChoiceField(
        queryset=User.objects.filter(groups__name="Engineers"),
        empty_label="Select Engineer",
        widget=forms.Select(attrs={"class": "form-control", "id": "id_engineer"}),
        required=False,
    )

    comment = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        required=False,
    )

    class Meta:
        model = Project
        fields = [
            "customer_name",
            "project_title",
            "service_description",
            "status",
            "job_completion_certificate",
            "engineer",
            "comment",
        ]


class AddProjectForm(BaseProjectForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Use placeholders and remove labels
        placeholder_map = {
            "customer_name": "Select Client",
            "project_title": "Project Title",
            "service_description": "Service Description",
            "engineer": "Select Engineer",
            "comment": "Comment",
        }

        for name, field in self.fields.items():
            if name in placeholder_map:
                field.label = ""
                field.widget.attrs["placeholder"] = placeholder_map[name]

        # Set and disable default status and certificate
        self.fields["status"].initial = Project.STATUS_PENDING
        self.fields["status"].disabled = True
        self.fields["status"].label = "Project Status"

        self.fields["job_completion_certificate"].initial = Project.CERT_PENDING
        self.fields["job_completion_certificate"].disabled = True
        self.fields["job_completion_certificate"].label = "Certificate Status"


class UpdateProjectForm(BaseProjectForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Labels (no colons)
        label_map = {
            "customer_name": "Client",
            "project_title": "Project Title",
            "service_description": "Service Description",
            "status": "Status",
            "job_completion_certificate": "Certificate",
            "engineer": "Engineer",
            "comment": "Comment",
        }

        for name, field in self.fields.items():
            field.label = label_map.get(name, name.replace("_", " ").capitalize())
            field.widget.attrs.pop("placeholder", None)
