# Standard Library
import csv
import json

# Django Core
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

# App Imports
from .models import VeeamJob
from .forms import AddVeeamForm, UpdateVeeamForm
from .utils import get_record_by_id, delete_record, has_form_changed
from core.mattermost import send_to_mattermost, send_email_alert_to_mattermost

# Core App
from core.models import Client
from core.forms import NotificationForm
from core.constants import SIGNATURE_BLOCKS as SIGNATURES


def notify_veeam(action, company_name, user):
    user_name = user.get_full_name() or user.email
    if action == "add":
        message = f"CRM updates: A new Veeam record for {company_name} has been added by {user_name}"
    elif action == "update":
        message = f"CRM updates: Veeam record for {company_name} has been modified by {user_name}"
    elif action == "delete":
        message = f"CRM updates: Veeam record for {company_name} has been deleted by {user_name}"
    else:
        message = f"CRM updates: Veeam record for {company_name} was changed by {user_name}"

    send_to_mattermost(message)


@login_required
def veeam_records(request):
    query = request.GET.get("search", "")
    site_filter = request.GET.get("site", "")
    os_filter = request.GET.get("os", "")
    status_filter = request.GET.get("job_status", "")

    records = VeeamJob.objects.select_related("client").order_by(
        "client__name", "client__email", "id"
    )

    if query:
        records = records.filter(
            Q(client__name__icontains=query) | Q(computer_name__icontains=query)
        )
    if site_filter:
        records = records.filter(site=site_filter)
    if os_filter:
        records = records.filter(os=os_filter)
    if status_filter:
        records = records.filter(job_status=status_filter)

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

    # Maintain filters in pagination
    querydict = request.GET.copy()
    querydict.pop("page", None)
    querydict.pop("page_size", None)
    querystring = querydict.urlencode()

    context = {
        "records": page_obj.object_list,
        "page_obj": page_obj,
        "page_size": page_size,
        "search_query": query,
        "selected_site": site_filter,
        "selected_os": os_filter,
        "selected_status": status_filter,
        "site_choices": dict(VeeamJob.SITE_CHOICES),
        "os_choices": dict(VeeamJob.OS_CHOICES),
        "status_choices": dict(VeeamJob.JOB_STATUS_CHOICES),
        "querystring": querystring,
    }

    return render(request, "veeam_records.html", context)


@login_required
def veeam_record_details(request, pk):
    customer_record = get_record_by_id(pk)
    return render(
        request, "veeam_record_details.html", {"customer_record": customer_record}
    )


@login_required
def delete_veeam_record(request, pk):
    record = get_record_by_id(pk)
    company_name = (
        record.client.name if record and getattr(record, "client", None) else "Unknown Company"
    )

    delete_record(pk)
    messages.success(request, "Record deleted successfully.")

    # Mattermost notification
    notify_veeam("delete", company_name, request.user)

    return redirect("veeam_records")


@login_required
def add_veeam_record(request):
    if request.method == "POST":
        form = AddVeeamForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.created_by = request.user
            record.updated_by = request.user
            record.save()
            messages.success(request, "Record has been added!")

            # Mattermost notification
            company_name = (
                record.client.name if getattr(record, "client", None) else "Unknown Company"
            )
            notify_veeam("add", company_name, request.user)

            return redirect("veeam_records")
    else:
        form = AddVeeamForm()

    return render(request, "veeam_add_record.html", {"form": form})


@login_required
def update_veeam_record(request, pk):
    record = get_record_by_id(pk)
    form = UpdateVeeamForm(request.POST or None, instance=record)

    if form.is_valid():
        if has_form_changed(form):
            form.instance.updated_by = request.user
            form.save()
            messages.success(request, "Record has been updated!")

            # Mattermost notification
            company_name = (
                record.client.name if getattr(record, "client", None) else "Unknown Company"
            )
            notify_veeam("update", company_name, request.user)
        else:
            messages.warning(request, "No changes detected.")

        return redirect("veeam_record", pk=pk)

    return render(
        request,
        "veeam_update_record.html",
        {"form": form, "customer_record": record},
    )


@login_required
def send_notification_veeam(request):
    if request.method == "GET":
        ids = request.GET.get("companies", "")
        company_ids = [int(cid) for cid in ids.split(",") if cid.isdigit()]

        if not company_ids:
            messages.error(request, "No companies selected.")
            return redirect("veeam_records")

        clients = Client.objects.filter(id__in=company_ids)
        emails = [c.email for c in clients if c.email]

        if not emails:
            messages.error(request, "Selected companies have no valid emails.")
            return redirect("veeam_records")

        form = NotificationForm(initial={"bcc_emails": ",".join(emails)})
        return render(
            request, "veeam_email_notification.html", {"form": form, "emails": emails}
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

            # 🚀 Send alert to Mattermost (Veeam context)
            send_email_alert_to_mattermost(
                subject=subject,
                recipient_count=len(valid_emails),
                user_display=request.user.get_full_name() or request.user.username,
                context="veeam",
            )

            messages.success(
                request, f"Notification sent to {len(valid_emails)} recipient(s)."
            )
            return redirect("veeam_records")

        emails = request.POST.get("bcc_emails", "").split(",")
        return render(
            request, "veeam_email_notification.html", {"form": form, "emails": emails}
        )

    return redirect("veeam_records")


@login_required
@require_POST
def export_selected_records(request):
    company_ids = [
        cid.strip()
        for cid in request.POST.get("companies", "").split(",")
        if cid.strip().isdigit()
    ]
    companies = Client.objects.filter(id__in=company_ids)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="Veeam_Backup_clients.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "ID",
            "Company Name",
            "Email",
            "Phone",
            "Contact Person",
            "Created on",
            "Last Updated",
        ]
    )

    for c in companies:
        writer.writerow(
            [
                c.id,
                c.name,
                c.email,
                getattr(c, "phone_number", ""),
                getattr(c, "contact_person", ""),
                (
                    getattr(c, "created_at", "").strftime("%Y-%m-%d")
                    if getattr(c, "created_at", None)
                    else ""
                ),
                (
                    getattr(c, "last_updated", "").strftime("%Y-%m-%d")
                    if getattr(c, "last_updated", None)
                    else ""
                ),
            ]
        )

    return response


@login_required
@require_POST
def update_veeam_tag(request, pk):
    return _update_single_field(request, pk, field="tag")


@login_required
@require_POST
def update_veeam_status(request, pk):
    return _update_single_field(
        request,
        pk,
        field="job_status",
        allowed_values=dict(VeeamJob.JOB_STATUS_CHOICES),
    )


@login_required
@require_POST
def update_veeam_comment(request, pk):
    return _update_single_field(request, pk, field="comment")


# === Helper ===
def _update_single_field(request, pk, field, allowed_values=None):
    record = get_object_or_404(VeeamJob, pk=pk)
    if not request.user.is_staff:
        return HttpResponseForbidden("Not allowed.")

    try:
        data = json.loads(request.body)
        new_value = data.get(field, "").strip()

        if allowed_values and new_value not in allowed_values:
            return HttpResponseBadRequest(f"Invalid {field}.")

        setattr(record, field, new_value)
        record.updated_by = request.user
        record.save()
        return JsonResponse({field: new_value})
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid data")
