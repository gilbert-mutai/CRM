# core/admin.py
from django.contrib import admin
from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "primary_email", "secondary_email", "phone_number", "client_type")
    search_fields = ("name", "primary_email", "secondary_email", "phone_number")
