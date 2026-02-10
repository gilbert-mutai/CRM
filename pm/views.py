# Standard library
import json
import os
from io import BytesIO

# Third-party libraries
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from pdf2image import convert_from_bytes
from PIL import Image as PilImage, ImageDraw, ImageFont
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
from django.core.exceptions import PermissionDenied
from django.core.mail import EmailMultiAlternatives
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


def can_add_pm_record(user):
    return (
        user.is_superuser
        or user.is_staff
        or user.groups.filter(name="Sales Admin").exists()
    )

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


def send_project_assignment_email(project, engineer, is_reassignment=False):
    if not engineer or not getattr(engineer, "email", None):
        return

    action_word = "re-assigned" if is_reassignment else "assigned"
    subject = f"Project {action_word.title()} - {project.project_title}"
    engineer_name = engineer.get_full_name() or engineer.email
    client_name = (
        project.customer_name.name
        if getattr(project, "customer_name", None)
        else "Unknown Client"
    )

    body_text = (
        f"Hello {engineer_name},\n\n"
        f"A project titled \"{project.project_title}\" for {client_name} has been {action_word} to you.\n\n"
        "Regards,\n\n"
        "Support, Angani Ltd\n"
        "Website: www.angani.co\n"
        "Mob: +254207650028\n"
        "West Point Building, 1st Floor,\n"
        "Mpaka Road, Nairobi"
    )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=body_text,
        from_email="support@angani.co",
        to=[engineer.email],
    )
    msg.send(fail_silently=True)



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
        "can_add_pm_record": can_add_pm_record(request.user),
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
    if not can_add_pm_record(request.user):
        raise PermissionDenied
    if request.method == "POST":
        form = AddProjectForm(request.POST)
        if form.is_valid():
            new_project = form.save(commit=False)
            new_project.created_by = request.user
            new_project.updated_by = request.user
            new_project.save()
            messages.success(request, "Project added successfully.")

            send_project_assignment_email(
                new_project,
                new_project.engineer,
                is_reassignment=False,
            )

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
            previous_engineer_id = project.engineer_id
            updated_project = form.save(commit=False)
            if has_form_changed(form):
                updated_project.updated_by = request.user
                updated_project.save()
                messages.success(request, "Project updated successfully.")

                if updated_project.engineer_id != previous_engineer_id:
                    send_project_assignment_email(
                        updated_project,
                        updated_project.engineer,
                        is_reassignment=True,
                    )

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
        previous_engineer_id = project.engineer_id
        engineer = User.objects.get(pk=engineer_id)
        project.engineer = engineer
        project.updated_by = request.user
        project.save()

        if project.engineer_id != previous_engineer_id:
            send_project_assignment_email(
                project,
                project.engineer,
                is_reassignment=True,
            )
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


def build_completion_certificate_pdf(project):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        topMargin=85,
        bottomMargin=28,
        leftMargin=35,
        rightMargin=35,
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
        fontSize=10.5,
        leading=15,
    )

    section_header_style = ParagraphStyle(
        name="SectionHeader",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#0F3D66"),
        spaceBefore=6,
        spaceAfter=6,
    )

    label_style = ParagraphStyle(
        name="BoldLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        textColor=colors.HexColor("#1F2937"),
    )

    value_style = ParagraphStyle(
        name="NormalValue",
        parent=styles["Normal"],
        fontSize=9.5,
        textColor=colors.HexColor("#111827"),
    )

    small_muted_style = ParagraphStyle(
        name="SmallMuted",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#4B5563"),
    )

    acceptance_style = ParagraphStyle(
        name="Acceptance",
        parent=styles["Italic"],
        fontSize=9.5,
        textColor=colors.HexColor("#374151"),
        leading=13,
    )

    def draw_page_canvas(canvas_obj, _doc):
        page_width, page_height = landscape(A4)

        # Background watermark seal
        canvas_obj.saveState()
        canvas_obj.setFillColor(colors.HexColor("#EEF2F7"))
        canvas_obj.setFont("Helvetica-Bold", 80)
        canvas_obj.translate(page_width / 2, page_height / 2 + 20)
        canvas_obj.rotate(25)
        canvas_obj.drawCentredString(0, 0, "ANGANI LIMITED")
        canvas_obj.restoreState()

        # Header band
        header_height = 60
        canvas_obj.setFillColor(colors.HexColor("#0F3D66"))
        canvas_obj.rect(0, page_height - header_height, page_width, header_height, fill=1, stroke=0)

        # Logo + title
        logo_path = os.path.join(settings.BASE_DIR, "static/images/logo.png")
        if os.path.exists(logo_path):
            canvas_obj.drawImage(
                logo_path,
                35,
                page_height - header_height + 10,
                width=40,
                height=40,
                preserveAspectRatio=True,
                mask="auto",
            )

        canvas_obj.setFillColor(colors.white)
        canvas_obj.setFont("Helvetica-Bold", 18)
        canvas_obj.drawString(85, page_height - header_height + 25, "Job Completion Certificate")
        canvas_obj.setFont("Helvetica", 10)
        canvas_obj.drawString(85, page_height - header_height + 10, "Provisioned Service Completion Confirmation")

    # Fields
    certificate_id = f"JCC-{project.id:06d}"

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
        [Paragraph("Certificate ID:", label_style), Paragraph(certificate_id, value_style)],
    ]

    elements.append(Paragraph("Project Details", section_header_style))
    table = Table(data, colWidths=[210, 530])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F3F4F6")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1F2937")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elements.append(table)
    elements.append(Spacer(1, 10))

    # Certification text (Justified)
    elements.append(Paragraph("Certification", section_header_style))
    cert_text = (
        "This is to certify that Angani Limited has provisioned and commissioned the service named above as per the "
        "agreed standards and requirements. We confirm that the service is up and running as per requirement."
    )
    elements.append(Paragraph(cert_text, justified_style))
    elements.append(Spacer(1, 10))

    # Sign-off section
    elements.append(Paragraph("Sign Off", section_header_style))

    customer_signoff = [
        [Paragraph("<b>CUSTOMER SIGN OFF</b>", small_muted_style)],
        [Paragraph("Name", label_style)],
        [""],
        [Paragraph("Designation", label_style)],
        [""],
        [Paragraph("Date", label_style)],
        [""],
        [Paragraph("Signature", label_style)],
        [Paragraph("____________________________", value_style)],
    ]

    angani_signoff = [
        [Paragraph("<b>ANGANI SIGN OFF</b>", small_muted_style)],
        [Paragraph("Name", label_style)],
        [Paragraph(engineer, value_style)],
        [Paragraph("Designation", label_style)],
        [Paragraph("Support Engineer", value_style)],
        [Paragraph("Date", label_style)],
        [Paragraph(date_provisioned, value_style)],
        [Paragraph("<b>Signature:</b> A.S", value_style)],
        [Paragraph("____________________________", value_style)],
    ]

    customer_table = Table(customer_signoff, colWidths=[350])
    angani_table = Table(angani_signoff, colWidths=[350])

    for table in (customer_table, angani_table):
        table.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("LINEBELOW", (0, 2), (0, 2), 0.75, colors.HexColor("#9CA3AF")),
                    ("LINEBELOW", (0, 4), (0, 4), 0.75, colors.HexColor("#9CA3AF")),
                    ("LINEBELOW", (0, 6), (0, 6), 0.75, colors.HexColor("#9CA3AF")),
                    ("LINEBELOW", (0, 8), (0, 8), 0.75, colors.HexColor("#9CA3AF")),
                ]
            )
        )

    signoff_wrapper = Table(
        [[customer_table, angani_table]],
        colWidths=[360, 360],
        hAlign="LEFT",
    )
    signoff_wrapper.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    elements.append(signoff_wrapper)

    # Build
    doc.build(elements, onFirstPage=draw_page_canvas, onLaterPages=draw_page_canvas)
    buffer.seek(0)

    safe_customer_name = customer.replace(" ", "_")
    filename = f"Job Completion Certificate - {safe_customer_name} - {certificate_id}.pdf"

    return buffer.getvalue(), filename


def _load_watermark_font(font_size):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
    except Exception:
        return ImageFont.load_default()


def _apply_watermark(image, text):
    base = image.convert("RGBA")
    watermark = PilImage.new("RGBA", base.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(watermark)

    width, height = base.size
    font_size = max(18, int(width * 0.04))
    font = _load_watermark_font(font_size)

    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    padding = int(min(width, height) * 0.03)
    x = width - text_width - padding
    y = height - text_height - padding

    draw.text(
        (x, y),
        text,
        font=font,
        fill=(120, 120, 120, 45),
    )

    combined = PilImage.alpha_composite(base, watermark)
    return combined.convert("RGB")


def build_completion_certificate_image(project):
    pdf_bytes, _ = build_completion_certificate_pdf(project)
    images = convert_from_bytes(pdf_bytes, dpi=200, fmt="png")
    if not images:
        raise ValueError("Failed to render certificate image.")

    image = _apply_watermark(images[0], "Issued by Angani Limited")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    customer = project.customer_name.name if project.customer_name else "N/A"
    safe_customer_name = customer.replace(" ", "_")
    certificate_id = f"JCC-{project.id:06d}"
    filename = f"Job Completion Certificate - {safe_customer_name} - {certificate_id}.png"
    return buffer.getvalue(), filename


@login_required
def download_completion_certificate(request, pk):
    project = get_object_or_404(Project, pk=pk)
    image_bytes, filename = build_completion_certificate_image(project)

    response = HttpResponse(image_bytes, content_type="image/png")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Cache-Control"] = "no-store"
    return response


@require_POST
@login_required
def share_completion_certificate(request, pk):
    project = get_object_or_404(Project, pk=pk)

    if request.user != project.engineer and not request.user.is_staff:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    if project.status != Project.STATUS_COMPLETED:
        return JsonResponse({"error": "Project is not completed."}, status=400)

    client_email = (
        project.customer_name.primary_email
        if project.customer_name and project.customer_name.primary_email
        else None
    )
    if not client_email:
        return JsonResponse({"error": "Client primary email not available."}, status=400)

    image_bytes, filename = build_completion_certificate_image(project)

    subject = f"Job Completion Certificate - {project.customer_name.name}"
    recipient_name = project.customer_name.contact_person or project.customer_name.name
    body_text = (
        f"Dear {recipient_name},\n\n"
        "I hope this message finds you well.\n\n"
        "Thank you for choosing Angani Services.\n\n"
        "Please find attached the job completion form for your review. Kindly sign, "
        "stamp, and return it at your earliest convenience.\n\n"
        "Should you have any questions or require further clarification, please feel free to reach out.\n\n"
        "Thank you, and we look forward to your response.\n\n"
        "Regards,\n\n"
        "Support, Angani Ltd\n"
        "Website: www.angani.co\n"
        "Mob: +254207650028\n"
        "West Point Building, 1st Floor,\n"
        "Mpaka Road, Nairobi"
    )
    body_html = (
        f"Dear {recipient_name},<br><br>"
        "I hope this message finds you well.<br><br>"
        "Thank you for choosing Angani Services.<br><br>"
        "Please find attached the job completion form for your review. Kindly sign, "
        "stamp, and return it at your earliest convenience.<br><br>"
        "Should you have any questions or require further clarification, please feel free to reach out.<br><br>"
        "Thank you, and we look forward to your response.<br><br>"
        "Regards,<br><br>"
        "Support, Angani Ltd<br>"
        "Website: www.angani.co<br>"
        "Mob: +254207650028<br>"
        "West Point Building, 1st Floor,<br>"
        "Mpaka Road, Nairobi"
    )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=body_text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[client_email],
        cc=[email for email in settings.CERTIFICATE_CC_EMAILS if email],
    )
    msg.attach_alternative(body_html, "text/html")
    msg.attach(filename, image_bytes, "image/png")
    msg.send(fail_silently=False)

    project.job_completion_certificate = Project.CERT_SHARED
    project.save(update_fields=["job_completion_certificate"])

    return JsonResponse(
        {
            "success": True,
            "certificate_status": project.job_completion_certificate,
            "certificate_status_display": project.get_job_completion_certificate_display(),
        }
    )


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
