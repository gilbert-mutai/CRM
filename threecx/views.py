# threecx/views.py
from io import StringIO
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.exceptions import PermissionDenied

from core.models import Client
from .forms import AddThreeCXForm
import csv
from django.http import HttpResponse
from .utils import (
    get_record_by_id,
    delete_record,
    has_form_changed,
)
from core.mattermost import send_to_mattermost ,send_email_alert_to_mattermost
from .models import ThreeCX
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from core.forms import NotificationForm
from core.constants import SIGNATURE_BLOCKS as SIGNATURES


# --- Helper function for notifications ---
def notify_threecx(action, company_name, user):
    user_name = user.get_full_name() or user.email
    if action == "add":
        message = f"CRM updates: A new 3CX record for {company_name} has been added by {user_name}"
    elif action == "update":
        message = f"CRM updates: 3CX record for {company_name} has been modified by {user_name}"
    elif action == "delete":
        message = f"CRM updates: 3CX record for {company_name} has been deleted by {user_name}"
    else:
        message = f"CRM updates: 3CX record for {company_name} was changed by {user_name}"

    send_to_mattermost(message)


# --- Views ---
def can_modify_threecx_record(user):
    return user.is_superuser or user.is_staff


@login_required
def threecx_records(request):
    query = request.GET.get("search", "")
    sip_filter = request.GET.get("sip_provider", "")
    license_filter = request.GET.get("license_type", "")

    records = ThreeCX.objects.all().order_by("-last_updated", "-created_at")

    if query:
        records = records.filter(
            Q(client__name__icontains=query)
            | Q(client__primary_email__icontains=query)
            | Q(client__secondary_email__icontains=query)
            | Q(fqdn__icontains=query)
        )

    if sip_filter:
        records = records.filter(sip_provider=sip_filter)

    if license_filter:
        records = records.filter(license_type=license_filter)

    # Pagination logic
    page_size = request.GET.get("page_size", 20)
    try:
        page_size = int(page_size)
        if page_size not in [20, 50, 100]:
            page_size = 20
    except ValueError:
        page_size = 20

    paginator = Paginator(records, page_size)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "records": page_obj.object_list,
        "page_obj": page_obj,
        "page_size": page_size,
        "search_query": query,
        "selected_sip": sip_filter,
        "selected_license": license_filter,
        "sip_providers": dict(ThreeCX.SIP_PROVIDERS),
        "license_types": dict(ThreeCX.LICENSE_TYPES),
    }

    return render(request, "threecx_records.html", context)


@login_required
def threecx_record_details(request, pk):
    customer_record = get_record_by_id(pk)
    context = {
        "customer_record": customer_record,
        "can_modify_record": can_modify_threecx_record(request.user),
    }
    return render(request, "threecx_record_details.html", context)


@login_required
def delete_threecx_record(request, pk):
    if not can_modify_threecx_record(request.user):
        raise PermissionDenied

    record = get_record_by_id(pk)
    company_name = (
        record.client.name if record and getattr(record, "client", None) else "Unknown Company"
    )

    delete_record(pk)
    messages.success(request, "Record deleted successfully.")

    # Mattermost notification
    notify_threecx("delete", company_name, request.user)

    return redirect("threecx_records")


@login_required
def add_threecx_record(request):
    if request.method == "POST":
        form = AddThreeCXForm(request.POST)
        if form.is_valid():
            new_record = form.save(commit=False)
            new_record.created_by = request.user
            new_record.updated_by = request.user
            new_record.save()
            messages.success(request, "Record has been added!")

            # Mattermost notification
            company_name = (
                new_record.client.name if getattr(new_record, "client", None) else "Unknown Company"
            )
            notify_threecx("add", company_name, request.user)

            return redirect("threecx_records")
    else:
        form = AddThreeCXForm()

    return render(request, "threecx_add_record.html", {"form": form})


@login_required
def update_threecx_record(request, pk):
    if not can_modify_threecx_record(request.user):
        raise PermissionDenied

    current_record = get_record_by_id(pk)
    form = AddThreeCXForm(request.POST or None, instance=current_record)

    if form.is_valid():
        updated_record = form.save(commit=False)

        if has_form_changed(form):
            updated_record.updated_by = request.user
            updated_record.save()
            messages.success(request, "Record has been updated!")

            # Mattermost notification
            company_name = (
                updated_record.client.name
                if getattr(updated_record, "client", None)
                else "Unknown Company"
            )
            notify_threecx("update", company_name, request.user)
        else:
            messages.warning(request, "No changes detected.")

        return redirect("threecx_record", pk=pk)

    return render(
        request,
        "threecx_update_record.html",
        {"form": form, "customer_record": current_record},
    )

@login_required
def send_notification_threecx(request):
    if request.method == "GET":
        client_ids = request.GET.get("clients", "")
        client_ids = [int(cid) for cid in client_ids.split(",") if cid.isdigit()]

        if not client_ids:
            messages.error(request, "No clients selected.")
            return redirect("threecx_records")

        clients = Client.objects.filter(id__in=client_ids)
        emails = []
        for c in clients:
            if c.primary_email:
                emails.append(c.primary_email)
            if c.secondary_email:
                emails.append(c.secondary_email)

        if not emails:
            messages.error(request, "No email addresses found for selected clients.")
            return redirect("threecx_records")
        form = NotificationForm(initial={"bcc_emails": ",".join(emails)})
        return render(
            request,
            "threecx_email_notification.html",
            {"form": form, "emails": emails},
        )

    if request.method == "POST":
        form = NotificationForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data["subject"]
            body = form.cleaned_data["body"]
            signature_key = form.cleaned_data["signature"]
            valid_emails = form.cleaned_data["valid_emails"]
            invalid_emails = form.cleaned_data["invalid_emails"]

            if invalid_emails:
                messages.warning(
                    request,
                    f"Ignoring invalid email(s): {', '.join(invalid_emails)}",
                )

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

            #Send alert to Mattermost
            send_email_alert_to_mattermost(
                subject=subject,
                recipient_count=len(valid_emails),
                user_display=request.user.get_full_name() or request.user.username,
                context="threecx",
            )

            messages.success(
                request,
                f"Notification sent to {len(valid_emails)} recipient(s).",
            )
            return redirect("threecx_records")

        emails = request.POST.get("bcc_emails", "").split(",")
        return render(
            request,
            "threecx_email_notification.html",
            {"form": form, "emails": emails},
        )

    return redirect("threecx_records")



@require_POST
@login_required
def export_selected_threecx_records(request):
    ids = request.POST.get("ids", "").split(",")
    ids = [int(i) for i in ids if i.isdigit()]
    records = ThreeCX.objects.select_related("client").filter(id__in=ids)

    # Prepare CSV
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(
        [
            "Company Name",
            "Contact Person",
            "Primary Email",
            "Secondary Email",
            "Phone Number",
            "SIP Provider",
            "FQDN",
            "License Type",
            "Simultaneous Calls",
        ]
    )

    for rec in records:
        writer.writerow(
            [
                rec.client.name,
                rec.client.contact_person,
                rec.client.primary_email,
                rec.client.secondary_email or "",
                rec.client.phone_number,
                rec.get_sip_provider_display(),
                rec.fqdn,
                rec.get_license_type_display(),
                rec.simultaneous_calls,
            ]
        )

    # Generate response
    response = HttpResponse(csv_buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="3cx_Clients.csv"'
    return response
