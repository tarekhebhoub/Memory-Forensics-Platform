from django.contrib import admin
from .models import IOC


@admin.register(IOC)
class IOCAdmin(admin.ModelAdmin):
    list_display = ("kind", "value", "case", "severity", "confidence", "source_plugin", "discovered_at")
    list_filter = ("kind", "severity", "source_plugin")
    search_fields = ("value", "description")
