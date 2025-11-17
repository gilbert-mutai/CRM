# domain/views.py
from io import StringIO
import csv
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from .forms import AddDomainForm
from .models import Domain
from .utils import get_record_by_id, delete_record, has_form_changed
from core.mattermost import send_to_mattermost ,send_email_alert_to_mattermost
from core.forms import NotificationForm
from core.constants import SIGNATURE_BLOCKS as SIGNATURES


def notify_domain(action, company_name, user):
    user_name = user.get_full_name() or user.email
    if action == "add":
        message = f"CRM Updates (Domains & Hosting): A new domain record for {company_name} has been added by {user_name}."
    elif action == "update":
        message = f"CRM Updates (Domains & Hosting): Domain record for {company_name} has been modified by {user_name}."
    elif action == "delete":
        message = f"CRM Updates (Domains & Hosting): Domain record for {company_name} has been deleted by {user_name}."
    else:
        message = f"CRM Updates (Domains & Hosting): Domain record for {company_name} was changed by {user_name}."

    send_to_mattermost(message)


@login_required
def domain_records(request):
    query = request.GET.get("search", "")
    host_filter = request.GET.get("host", "")

    records = Domain.objects.select_related("client").order_by("client__name", "domain")

    if query:
        records = records.filter(
            Q(client__name__icontains=query)
            | Q(client__email__icontains=query)
            | Q(domain__icontains=query)
            | Q(host__icontains=query)
        )

    if host_filter:
        records = records.filter(host=host_filter)

    # Distinct hosts for dropdown
    hosts = Domain.objects.values_list("host", flat=True).distinct().order_by("host")

    hosts = list(
        Domain.objects.values_list("host", flat=True).distinct().order_by("host")
    )

    # Force "None" to appear first if present
    if "None" in hosts:
        hosts.remove("None")
    hosts.insert(0, "None")

    # Pagination
    page_size = int(request.GET.get("page_size", 20) or 20)
    paginator = Paginator(records, page_size)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "records": page_obj.object_list,
        "page_obj": page_obj,
        "page_size": page_size,
        "search_query": query,
        "hosts": hosts,
        "selected_host": host_filter,
    }
    return render(request, "domain_records.html", context)


def domain_record_details(request, pk):
    if not request.user.is_authenticated:
        messages.warning(request, "You must be logged in to view that page.")
        return redirect("home")

    customer_record = get_record_by_id(pk)
    return render(
        request, "domain_record_details.html", {"customer_record": customer_record}
    )


def delete_domain_record(request, pk):
    if not request.user.is_authenticated:
        messages.warning(request, "You must be logged in to do that.")
        return redirect("login")

    record = get_record_by_id(pk)
    company_name = (
        record.client.name if record and getattr(record, "client", None) else "Unknown Company"
    )

    delete_record(pk)
    messages.success(request, "Domain record deleted successfully.")

    # Mattermost notification
    notify_domain("delete", company_name, request.user)

    return redirect("domain_records")


def add_domain_record(request):
    if not request.user.is_authenticated:
        messages.warning(request, "You must be logged in.")
        return redirect("login")

    if request.method == "POST":
        form = AddDomainForm(request.POST)
        if form.is_valid():
            new_record = form.save(commit=False)
            new_record.created_by = request.user
            new_record.updated_by = request.user
            new_record.save()
            messages.success(request, "Domain record has been added!")

            # Mattermost notification
            company_name = (
                new_record.client.name if getattr(new_record, "client", None) else "Unknown Company"
            )
            notify_domain("add", company_name, request.user)

            return redirect("domain_records")
    else:
        form = AddDomainForm()

    return render(request, "domain_add_record.html", {"form": form})


def update_domain_record(request, pk):
    if not request.user.is_authenticated:
        messages.warning(request, "You must be logged in.")
        return redirect("login")

    customer_record = get_record_by_id(pk)
    form = AddDomainForm(request.POST or None, instance=customer_record)

    if form.is_valid():
        updated_record = form.save(commit=False)

        if has_form_changed(form):
            updated_record.updated_by = request.user
            updated_record.save()
            messages.success(request, "Domain record has been updated!")

            # Mattermost notification
            company_name = (
                updated_record.client.name
                if getattr(updated_record, "client", None)
                else "Unknown Company"
            )
            notify_domain("update", company_name, request.user)
        else:
            messages.warning(request, "No changes detected.")

        return redirect("domain_record", pk=pk)

    return render(
        request,
        "domain_update_record.html",
        {"form": form, "customer_record": customer_record},
    )


@login_required
def send_notification_domain(request):
    client_ids = request.GET.get("clients", "")
    client_ids = [int(cid) for cid in client_ids.split(",") if cid.isdigit()]

    if not client_ids:
        messages.error(request, "No companies selected.")
        return redirect("domain_records")

    from core.models import Client

    clients = Client.objects.filter(id__in=client_ids)
    emails = [c.email for c in clients if c.email]

    if request.method == "GET":
        if not emails:
            messages.error(request, "No email addresses found for selected companies.")
            return redirect("domain_records")
        form = NotificationForm(initial={"bcc_emails": ",".join(emails)})
        return render(
            request,
            "domain_email_notification.html",
            {"form": form, "emails": emails},
        )

    if request.method == "POST":
        form = NotificationForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data["subject"]
            body = form.cleaned_data["body"]
            signature_key = form.cleaned_data["signature"]
            valid_emails = form.cleaned_data["valid_emails"]

            signature_block = SIGNATURES.get(signature_key, signature_key)
            full_body = f"{body}<br><br>--<br>{signature_block}"

            msg = EmailMultiAlternatives(
                subject=subject,
                body=full_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                bcc=valid_emails,
            )
            msg.attach_alternative(full_body, "text/html")
            msg.send(fail_silently=False)

            # Send alert to Mattermost
            send_email_alert_to_mattermost(
                subject=subject,
                recipient_count=len(valid_emails),
                user_display=request.user.get_full_name() or request.user.username,
                context="domain",
            )

            messages.success(
                request, f"Notification sent to {len(valid_emails)} recipient(s)."
            )
            return redirect("domain_records")

        return render(
            request,
            "domain_email_notification.html",
            {"form": form, "emails": emails},
        )



@require_POST
@login_required
def export_selected_domain_records(request):
    ids = request.POST.get("ids", "").split(",")
    ids = [int(i) for i in ids if i.isdigit()]

    from core.models import Client

    clients = Client.objects.filter(id__in=ids)
    records = Domain.objects.select_related("client").filter(client__in=clients)

    # CSV export
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(
        [
            "Company Name",
            "Contact Person",
            "Email",
            "Phone Number",
            "Domain",
            "Host",
            "Package",
        ]
    )

    for rec in records:
        writer.writerow(
            [
                rec.client.name,
                rec.client.contact_person,
                rec.client.email,
                rec.client.phone_number,
                rec.domain,
                rec.host,
                rec.package,
            ]
        )

    response = HttpResponse(csv_buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="Domain_and_Hosting_Clients.csv"'
    )
    return response
