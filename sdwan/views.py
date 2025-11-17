# === Standard Library ===
import csv
import json

# === Django Core ===
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import (
    HttpResponse,
    JsonResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

# === App Imports (SD-WAN) ===
from .models import SDWAN   # adjust to your actual model name
from .forms import AddSDWANForm, UpdateSDWANForm
from .utils import get_record_by_id, delete_record, has_form_changed

# === Core App ===
from core.models import Client
from core.forms import NotificationForm
from core.constants import SIGNATURE_BLOCKS as SIGNATURES
from core.mattermost import send_to_mattermost,send_email_alert_to_mattermost


# ===========================
# SDWAN Views
# ===========================

def notify_sdwan(action, company_name, user):
    user_name = user.get_full_name() or user.email
    if action == "add":
        message = f"CRM Updates (SD-WAN): A new SD-WAN record for {company_name} has been added by {user_name}."
    elif action == "update":
        message = f"CRM Updates (SD-WAN): SD-WAN record for {company_name} has been modified by {user_name}."
    elif action == "delete":
        message = f"CRM Updates (SD-WAN): SD-WAN record for {company_name} has been deleted by {user_name}."
    else:
        message = f"CRM Updates (SD-WAN): SD-WAN record for {company_name} was changed by {user_name}."

    send_to_mattermost(message)


@login_required
def sdwan_records(request):
    query = request.GET.get("search", "")
    provider_filter = request.GET.get("provider", "")

    records = SDWAN.objects.select_related("client").order_by(
        "client__name", "client__email", "id"
    )

    if query:
        records = records.filter(
            Q(client__name__icontains=query) | Q(account_number__icontains=query)
        )
    if provider_filter:
        records = records.filter(provider=provider_filter)

    # Pagination
    try:
        page_size = int(request.GET.get("page_size", 20))
        if page_size not in [20, 50, 100]:
            page_size = 20
    except ValueError:
        page_size = 20

    paginator = Paginator(records, page_size)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    querydict = request.GET.copy()
    querydict.pop("page", None)
    querydict.pop("page_size", None)
    querystring = querydict.urlencode()

    context = {
        "records": page_obj.object_list,
        "page_obj": page_obj,
        "page_size": page_size,
        "search_query": query,
        "selected_provider": provider_filter,
        "provider_choices": dict(SDWAN.PROVIDER_CHOICES),
        "querystring": querystring,
    }
    return render(request, "sdwan_records.html", context)


@login_required
def sdwan_record_details(request, pk):
    customer_record = get_object_or_404(SDWAN, pk=pk)
    return render(request, "sdwan_record_details.html", {"customer_record": customer_record})


@login_required
def add_sdwan_record(request):
    if request.method == "POST":
        form = AddSDWANForm(request.POST)
        if form.is_valid():
            new_record = form.save(commit=False)
            new_record.created_by = request.user
            new_record.updated_by = request.user
            new_record.save()
            messages.success(request, "SD-WAN record has been added!")

            # Mattermost notification
            company_name = (
                new_record.client.name if getattr(new_record, "client", None) else "Unknown Company"
            )
            notify_sdwan("add", company_name, request.user)

            return redirect("sdwan_records")
    else:
        form = AddSDWANForm()

    return render(request, "sdwan_add_record.html", {"form": form})


@login_required
def update_sdwan_record(request, pk):
    current_record = get_object_or_404(SDWAN, pk=pk)
    form = UpdateSDWANForm(request.POST or None, instance=current_record)

    if form.is_valid():
        updated_record = form.save(commit=False)

        if has_form_changed(form):
            updated_record.updated_by = request.user
            updated_record.save()
            messages.success(request, "SD-WAN record has been updated!")

            # Mattermost notification
            company_name = (
                updated_record.client.name
                if getattr(updated_record, "client", None)
                else "Unknown Company"
            )
            notify_sdwan("update", company_name, request.user)
        else:
            messages.warning(request, "No changes detected.")

        return redirect("sdwan_record", pk=pk)

    return render(
        request,
        "sdwan_update_record.html",
        {"form": form, "customer_record": current_record},
    )


@login_required
def delete_sdwan_record(request, pk):
    record = get_object_or_404(SDWAN, pk=pk)
    company_name = (
        record.client.name if record and getattr(record, "client", None) else "Unknown Company"
    )
    record.delete()
    messages.success(request, "SD-WAN record deleted successfully.")

    # Mattermost notification
    notify_sdwan("delete", company_name, request.user)

    return redirect("sdwan_records")


# ========== Notifications ==========

@login_required
def send_notification_sdwan(request):
    if request.method == "GET":
        ids = request.GET.get("companies", "")
        company_ids = [int(cid) for cid in ids.split(",") if cid.isdigit()]

        if not company_ids:
            messages.error(request, "No companies selected.")
            return redirect("sdwan_records")

        clients = Client.objects.filter(id__in=company_ids)
        emails = [c.email for c in clients if c.email]

        if not emails:
            messages.error(request, "Selected companies have no valid emails.")
            return redirect("sdwan_records")

        form = NotificationForm(initial={"bcc_emails": ",".join(emails)})
        return render(
            request, "sdwan_email_notification.html", {"form": form, "emails": emails}
        )

    elif request.method == "POST":
        form = NotificationForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data["subject"]
            body = form.cleaned_data["body"]
            signature_key = form.cleaned_data["signature"]
            valid_emails = form.cleaned_data["valid_emails"]
            invalid_emails = form.cleaned_data["invalid_emails"]

            if invalid_emails:
                messages.warning(
                    request, f"Ignoring invalid email(s): {', '.join(invalid_emails)}"
                )

            full_body = (
                f"{body}<br><br>--<br>{SIGNATURES.get(signature_key, signature_key)}"
            )

            msg = EmailMultiAlternatives(
                subject=subject,
                body=full_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                bcc=valid_emails,
            )
            msg.attach_alternative(full_body, "text/html")
            msg.send(fail_silently=False)

            # Send alert to Mattermost (SD-WAN context)
            send_email_alert_to_mattermost(
                subject=subject,
                recipient_count=len(valid_emails),
                user_display=request.user.get_full_name() or request.user.username,
                context="sdwan",
            )

            messages.success(
                request, f"Notification sent to {len(valid_emails)} recipient(s)."
            )
            return redirect("sdwan_records")

        emails = request.POST.get("bcc_emails", "").split(",")
        return render(
            request, "sdwan_email_notification.html", {"form": form, "emails": emails}
        )

    return redirect("sdwan_records")

# ========== Export ==========
@login_required
@require_POST
def export_selected_sdwan_records(request):
    company_ids = [
        cid.strip()
        for cid in request.POST.get("companies", "").split(",")
        if cid.strip().isdigit()
    ]
    companies = Client.objects.filter(id__in=company_ids)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="SDWAN_clients.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "ID",
            "Company Name",
            "Account Number",
            "Provider",
            "Contact Person",
            "Email",
            "Phone",
            "Created on",
            "Last Updated",
        ]
    )

    for sdwan in SDWAN.objects.filter(client__in=companies):
        writer.writerow(
            [
                sdwan.id,
                sdwan.client.name,
                sdwan.account_number,
                sdwan.provider,
                sdwan.client.contact_person,
                sdwan.client.email,
                sdwan.client.phone_number,
                sdwan.created_at.strftime("%Y-%m-%d"),
                sdwan.last_updated.strftime("%Y-%m-%d"),
            ]
        )

    return response
