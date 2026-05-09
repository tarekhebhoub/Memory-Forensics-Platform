from django.contrib import admin
from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "actor_username", "action", "target_type", "target_id",
                    "method", "status_code", "severity")
    list_filter = ("severity", "action", "target_type")
    search_fields = ("actor_username", "action", "path", "target_id")
    readonly_fields = [f.name for f in AuditEvent._meta.fields]
