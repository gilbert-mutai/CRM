from django.urls import path
from . import views

urlpatterns = [
    path("records/", views.pm_records, name="pm_records"),
    path("record/<int:pk>/", views.pm_record_details, name="pm_record"),
    path("delete/<int:pk>/", views.delete_pm_record, name="delete_pm_record"),
    path("add/", views.add_pm_record, name="add_pm_record"),
    path("update/<int:pk>/", views.update_pm_record, name="update_pm_record"),
    path(
        "export/", views.export_selected_pm_records, name="export_selected_pm_records"
    ),
    # Advanced
    path(
        "record/<int:pk>/description/",
        views.update_project_description,
        name="update_project_description",
    ),
    path(
        "record/<int:pk>/status/",
        views.toggle_project_status,
        name="toggle_project_status",
    ),
    path(
        "record/<int:pk>/engineer/",
        views.update_project_engineer,
        name="update_project_engineer",
    ),
    path(
        "record/<int:pk>/comment/",
        views.update_project_comment,
        name="update_project_comment",
    ),
    path(
        "record/<int:pk>/certificate/download/",
        views.download_completion_certificate,
        name="download_completion_certificate",
    ),
    path(
        "record/<int:pk>/certificate/",
        views.toggle_certificate_status,
        name="toggle_certificate_status",
    ),
    path(
        "record/<int:pk>/certificate/share/",
        views.share_completion_certificate,
        name="share_completion_certificate",
    ),
]
