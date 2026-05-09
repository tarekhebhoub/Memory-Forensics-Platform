from django.contrib import admin
from .models import Evidence, UploadSession


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ("name", "case", "kind", "size_bytes", "status", "uploaded_at")
    list_filter = ("kind", "status", "os_profile_hint")
    search_fields = ("name", "sha256", "md5")


@admin.register(UploadSession)
class UploadSessionAdmin(admin.ModelAdmin):
    list_display = ("uid", "case", "filename", "status", "received_bytes", "total_size", "started_at")
    list_filter = ("status",)
