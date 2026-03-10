from django.urls import path
from . import views

urlpatterns = [
    path("", views.access_center, name="access_center"),
    path("access-center/", views.access_center, name="access_center_legacy"),
    path("clients/", views.client_records, name="client_records"),
    path("client/<int:pk>/", views.client_record, name="client_record"),
    path("client/add/", views.add_client_record, name="add_client_record"),
    path(
        "client/update/<int:pk>/",
        views.update_client_record,
        name="update_client_record",
    ),
    path(
        "client/delete/<int:pk>/",
        views.delete_client_record,
        name="delete_client_record",
    ),
    path(
        "clients/send-notification/",
        views.send_notification_client,
        name="send_notification_client",
    ),
    path("clients/export/", views.export_clients, name="export_clients"),
]
