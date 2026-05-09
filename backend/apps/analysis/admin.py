from django.contrib import admin
from .models import AnalysisJob, PluginResult


class PluginResultInline(admin.TabularInline):
    model = PluginResult
    extra = 0
    readonly_fields = ("plugin_name", "status", "duration_ms", "started_at", "completed_at")
    fields = readonly_fields


@admin.register(AnalysisJob)
class AnalysisJobAdmin(admin.ModelAdmin):
    list_display = ("uid", "evidence", "status", "risk_score", "detected_os", "created_at")
    list_filter = ("status", "detected_os")
    inlines = [PluginResultInline]


@admin.register(PluginResult)
class PluginResultAdmin(admin.ModelAdmin):
    list_display = ("job", "plugin_name", "status", "duration_ms", "completed_at")
    list_filter = ("plugin_name", "status")
