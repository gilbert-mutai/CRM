from django.contrib import admin
from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    # Fields to display in the list view
    list_display = (
        "get_customer_name",  # Display customer's name
        "get_customer_email",  # Display customer's email
        "project_title",  # Project title
        "status",  # Project status (e.g., Pending/Completed)
        "job_completion_certificate",  # Certificate status (e.g., Pending/Shared)
        "get_engineer_name",  # Assigned engineer name
    )

    # Filters shown in the right sidebar
    list_filter = ("status", "job_completion_certificate")

    # Fields searchable in the admin
    search_fields = ("customer_name__name", "customer_name__email", "project_title")

    # Read-only metadata fields (auto managed)
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")

    # Grouped field sections for detail/edit view
    fieldsets = (
        (
            "Project Info",
            {
                "fields": (
                    "customer_name",
                    "project_title",
                    "service_description",
                    "status",
                    "date_of_completion",
                    "job_completion_certificate",
                    "engineer",
                    "comment",
                )
            },
        ),
        (
            "Metadata",
            {"fields": ("created_by", "updated_by", "created_at", "updated_at")},
        ),
    )

    # Custom display for customer name
    def get_customer_name(self, obj):
        return obj.customer_name.name

    get_customer_name.short_description = "Customer Name"

    # Custom display for customer email
    def get_customer_email(self, obj):
        return obj.customer_name.primary_email

    get_customer_email.short_description = "Email Address"

    # Custom display for engineer name (safe fallback)
    def get_engineer_name(self, obj):
        return obj.engineer.get_full_name() if obj.engineer else "-"

    get_engineer_name.short_description = "Engineer"

    # Automatically set created_by and updated_by fields
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user  # Set creator only once
        obj.updated_by = request.user  # Always update this
        super().save_model(request, obj, form, change)
