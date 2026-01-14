import csv
from io import StringIO
from django.http import HttpResponse
from django.core.validators import validate_email as django_validate_email
from django.core.exceptions import ValidationError
from .models import Client


def validate_emails(raw_emails):
    """
    Takes a comma-separated string of emails.
    Returns a tuple of (valid_emails, invalid_emails).
    """
    raw_list = [e.strip() for e in raw_emails.split(",") if e.strip()]
    valid = []
    invalid = []

    for email in raw_list:
        try:
            django_validate_email(email)
            valid.append(email)
        except ValidationError:
            invalid.append(email)

    return valid, invalid


def generate_csv_for_selected_emails(emails):
    """
    Generates a CSV file response containing full client records for selected emails.
    """
    clients = Client.objects.filter(primary_email__in=emails)

    buffer = StringIO()
    writer = csv.writer(buffer)

    # Write header
    writer.writerow(["Name", "Client Type", "Contact Person", "Primary Email", "Secondary Email", "Phone Number"])

    # Write client data
    for client in clients:
        writer.writerow(
            [
                client.name,
                client.client_type,
                client.contact_person,
                client.primary_email,
                client.secondary_email or "",
                client.phone_number,
            ]
        )

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=Angani_Clients.csv"
    return response

