# Standard library
import json
import os
from io import BytesIO

# Third-party libraries
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Table,
    TableStyle,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Image,
)

# Django core
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models.functions import ExtractMonth, ExtractYear
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# Local app imports
from .forms import AddProjectForm, UpdateProjectForm
from .models import Project
from .utils import (
    delete_project,
    generate_csv_for_selected_projects,
    get_project_by_id,
    has_form_changed,

)
from core.mattermost import send_to_mattermost


# Get custom user model
User = get_user_model()

def notify_project(action, company_name, user):
    user_name = user.get_full_name() or user.email
    if action == "add":
        message = f"CRM updates: A new Project record for {company_name} has been added by {user_name}"
    elif action == "update":
        message = f"CRM updates: Project record for {company_name} has been modified by {user_name}"
    elif action == "delete":
        message = f"CRM updates: Project record for {company_name} has been deleted by {user_name}"
    else:
        message = f"CRM updates: Project record for {company_name} was changed by {user_name}"

    send_to_mattermost(message)



@login_required
def pm_records(request):
    query = request.GET.get("search", "")
    engineer_filter = request.GET.get("engineer", "")
    status_filter = request.GET.get("status", "")
    certificate_filter = request.GET.get("certificate", "")
    year_filter = request.GET.get("year", "")
    month_filter = request.GET.get("month", "")

    projects = Project.objects.all().order_by("-date_of_request")

    # Apply search on customer name and project title
    if query:
        projects = projects.filter(
            Q(customer_name__name__icontains=query) | Q(project_title__icontains=query)
        )

    # Filter by engineer
    if engineer_filter:
        projects = projects.filter(engineer__id=engineer_filter)

    # Filter by status
    if status_filter:
        projects = projects.filter(status=status_filter)

    # Filter by certificate
    if certificate_filter:
        projects = projects.filter(job_completion_certificate=certificate_filter)

    # Filter by year
    if year_filter:
        projects = projects.filter(date_of_request__year=year_filter)

    # Filter by month
    if month_filter:
        projects = projects.filter(date_of_request__month=month_filter)

    # Pagination
    page_size = request.GET.get("page_size", 20)
    try:
        page_size = int(page_size)
        if page_size not in [20, 50, 100]:
            page_size = 20
    except ValueError:
        page_size = 20

    paginator = Paginator(projects, page_size)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Engineer choices
    engineers = User.objects.filter(project__isnull=False).distinct()
    engineers_choices = [(e.id, e.get_full_name()) for e in engineers]

    # Available years for filter
    available_years = (
        Project.objects.annotate(year=ExtractYear("date_of_request"))
        .values_list("year", flat=True)
        .distinct()
        .order_by("-year")
    )

    # Available months
    raw_months = (
        Project.objects.annotate(month=ExtractMonth("date_of_request"))
        .values_list("month", flat=True)
        .distinct()
        .order_by("month")
    )
    import calendar

    months = [(m, calendar.month_name[m]) for m in raw_months if m]

    context = {
        "projects": page_obj.object_list,
        "page_obj": page_obj,
        "page_size": page_size,
        # Filters
        "search_query": query,
        "selected_engineer": engineer_filter,
        "selected_status": status_filter,
        "selected_certificate": certificate_filter,
        "selected_year": year_filter,
        "selected_month": month_filter,
        # Dropdown choices
        "engineers": engineers_choices,
        "status_choices": dict(Project.STATUS_CHOICES),
        "certificate_choices": dict(Project.CERTIFICATE_CHOICES),
        "available_years": available_years,
        "months": months,
    }

    return render(request, "pm_records.html", context)


@login_required
def pm_record_details(request, pk):
    project = get_project_by_id(pk)
    context = {"project": project}

    if request.user.is_staff:
        try:
            engineer_group = Group.objects.get(name="Engineers")
            engineers = engineer_group.user_set.all()
        except Group.DoesNotExist:
            engineers = User.objects.none()

        context["engineers"] = engineers

    return render(request, "pm_record_details.html", context)


@login_required
def add_pm_record(request):
    if request.method == "POST":
        form = AddProjectForm(request.POST)
        if form.is_valid():
            new_project = form.save(commit=False)
            new_project.created_by = request.user
            new_project.updated_by = request.user
            new_project.save()
            messages.success(request, "Project added successfully.")

            # Mattermost notification
            company_name = (
                new_project.customer_name.name
                if getattr(new_project, "customer_name", None)
                else "Unknown Company"
            )
            notify_project("add", company_name, request.user)

            return redirect("pm_records")
    else:
        form = AddProjectForm()

    return render(request, "pm_add_record.html", {"form": form})


@login_required
def update_pm_record(request, pk):
    project = get_project_by_id(pk)
    if request.method == "POST":
        form = UpdateProjectForm(request.POST, instance=project)
        if form.is_valid():
            updated_project = form.save(commit=False)
            if has_form_changed(form):
                updated_project.updated_by = request.user
                updated_project.save()
                messages.success(request, "Project updated successfully.")

                # Mattermost notification
                company_name = (
                    updated_project.customer_name.name
                    if getattr(updated_project, "customer_name", None)
                    else "Unknown Company"
                )
                notify_project("update", company_name, request.user)
            else:
                messages.warning(request, "No changes detected.")
            return redirect("pm_record", pk=pk)
    else:
        form = UpdateProjectForm(instance=project)

    return render(request, "pm_update_record.html", {"form": form, "project": project})


@login_required
def delete_pm_record(request, pk):
    project = get_project_by_id(pk)
    company_name = (
        project.customer_name.name
        if getattr(project, "customer_name", None)
        else "Unknown Company"
    )

    delete_project(pk)
    messages.success(request, "Project deleted successfully.")

    # Mattermost notification
    notify_project("delete", company_name, request.user)

    return redirect("pm_records")


@require_POST
@login_required
def export_selected_pm_records(request):
    raw_ids = request.POST.get("ids", "")
    project_ids = [int(id.strip()) for id in raw_ids.split(",") if id.strip().isdigit()]
    return generate_csv_for_selected_projects(project_ids)


# Advanced Logics
@csrf_exempt
@login_required
def toggle_project_status(request, pk):
    project = get_project_by_id(pk)

    if request.user != project.engineer and not request.user.is_staff:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    data = json.loads(request.body)
    new_status = data.get("status")

    project.status = new_status

    if new_status == Project.STATUS_COMPLETED:
        project.date_of_completion = timezone.now()
    else:
        project.date_of_completion = None

    project.updated_by = request.user
    project.save()

    return JsonResponse(
        {
            "status": new_status,
            "status_display": project.get_status_display(),
            "completion_date": (
                project.date_of_completion.strftime("%b %d, %Y %H:%M")
                if project.date_of_completion
                else None
            ),
        }
    )


@csrf_exempt
@login_required
def update_project_engineer(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not request.user.is_staff:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    data = json.loads(request.body)
    engineer_id = data.get("engineer_id")

    try:
        engineer = User.objects.get(pk=engineer_id)
        project.engineer = engineer
        project.updated_by = request.user
        project.save()
        return JsonResponse({"success": True})
    except User.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Engineer not found"}, status=400
        )


@csrf_exempt
@login_required
def update_project_comment(request, pk):
    project = get_project_by_id(pk)

    if request.user != project.engineer and not request.user.is_staff:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    data = json.loads(request.body)
    comment = data.get("comment", "").strip()
    project.comment = comment
    project.updated_by = request.user
    project.save()

    return JsonResponse({"comment": comment})


# views.py
@csrf_exempt
@login_required
def update_project_description(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.user != project.engineer and not request.user.is_staff:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    data = json.loads(request.body)
    new_desc = data.get("service_description")
    project.service_description = new_desc
    project.updated_by = request.user
    project.save()
    return JsonResponse({"service_description": new_desc})


@login_required
def download_completion_certificate(request, pk):
    project = get_object_or_404(Project, pk=pk)
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=50,
        bottomMargin=50,
        leftMargin=50,
        rightMargin=50,
    )

    # Set PDF metadata
    doc.title = "Job Completion Certificate"
    doc.author = "Angani Limited"
    doc.subject = "Provisioned Service Completion Confirmation"
    doc.creator = "Angani Client Manager System"

    elements = []

    styles = getSampleStyleSheet()

    justified_style = ParagraphStyle(
        name="Justify",
        parent=styles["Normal"],
        alignment=4,  # Justify
        fontSize=10,
        leading=14,
    )

    bold_center_style = ParagraphStyle(
        name="CenterTitle",
        parent=styles["Heading1"],
        fontSize=16,
        alignment=1,  # Center
        spaceAfter=10,
    )

    label_style = ParagraphStyle(
        name="BoldLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
    )

    value_style = ParagraphStyle(
        name="NormalValue",
        parent=styles["Normal"],
        fontSize=10,
    )

    # Logo
    logo_path = os.path.join(settings.BASE_DIR, "static/images/logo.png")
    if os.path.exists(logo_path):
        img = Image(logo_path, width=1.2 * inch, height=1.2 * inch)
        elements.append(img)
        elements.append(Spacer(1, 10))

    # Title
    elements.append(Paragraph("Job Completion Certificate", bold_center_style))
    elements.append(Spacer(1, 10))

    # Fields
    customer = project.customer_name.name if project.customer_name else "N/A"
    service = project.service_description or "N/A"
    date_provisioned = (
        project.date_of_completion.strftime("%d %B %Y")
        if project.date_of_completion
        else "Not Set"
    )
    engineer = project.engineer.get_full_name() if project.engineer else "N/A"

    data = [
        [
            Paragraph("Client (Company) Name:", label_style),
            Paragraph(customer, value_style),
        ],
        [Paragraph("Service Provided:", label_style), Paragraph(service, value_style)],
        [
            Paragraph("Date Provisioned:", label_style),
            Paragraph(date_provisioned, value_style),
        ],
        [Paragraph("Engineer's Name:", label_style), Paragraph(engineer, value_style)],
    ]

    table = Table(data, colWidths=[180, 350])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elements.append(table)
    elements.append(Spacer(1, 15))

    # Certification text (Justified)
    cert_text = (
        "This is to certify that Angani Limited has provisioned and commissioned the service named above as per the "
        "agreed standards and requirements. We confirm that the service is up and running as per requirement."
    )
    elements.append(Paragraph(cert_text, justified_style))
    elements.append(Spacer(1, 30))

    # Sign-off section
    signoff_data = [
        [
            Paragraph("<b>CUSTOMER SIGN OFF</b>", styles["Normal"]),
            Paragraph("<b>ANGANI SIGN OFF</b>", styles["Normal"]),
        ],
        [
            Paragraph("<b>Name:</b> __________________________", styles["Normal"]),
            Paragraph(f"<b>Name:</b> {engineer}", styles["Normal"]),
        ],
        [
            Paragraph("<b>Designation:</b> ____________________", styles["Normal"]),
            Paragraph("<b>Designation:</b> Support Engineer", styles["Normal"]),
        ],
        [
            Paragraph("<b>Date:</b> ___________________________", styles["Normal"]),
            Paragraph(f"<b>Date:</b> {date_provisioned}", styles["Normal"]),
        ],
        [
            Paragraph("<b>Signature:</b> _______________________", styles["Normal"]),
            Paragraph("<b>Signature:</b> A.S", styles["Normal"]),
        ],
    ]

    signoff_table = Table(signoff_data, colWidths=[270, 270])
    signoff_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(signoff_table)

    # Build
    doc.build(elements)
    buffer.seek(0)

    safe_customer_name = customer.replace(" ", "_")
    filename = f"Job Completion Certificate - {safe_customer_name}.pdf"

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@csrf_exempt
@login_required
def toggle_certificate_status(request, pk):
    project = get_object_or_404(Project, pk=pk)

    if request.user != project.engineer and not request.user.is_staff:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    data = json.loads(request.body)
    new_status = data.get("certificate_status")

    project.job_completion_certificate = new_status
    project.save()

    return JsonResponse(
        {
            "certificate_status": new_status,
            "certificate_status_display": project.get_job_completion_certificate_display(),
        }
    )
