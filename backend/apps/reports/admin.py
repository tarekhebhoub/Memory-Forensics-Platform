from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("title", "case", "format", "status", "created_at", "completed_at")
    list_filter = ("format", "status")
