from rest_framework import serializers
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    case_code = serializers.CharField(source="case.code", read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            "id", "uid", "case", "case_code", "title", "format", "status",
            "created_by", "size_bytes", "error", "created_at", "completed_at",
            "download_url",
        )
        read_only_fields = ("uid", "status", "size_bytes", "error",
                            "created_at", "completed_at", "case_code", "download_url")

    def get_download_url(self, obj) -> str:
        if obj.status != Report.Status.READY:
            return ""
        return f"/api/v1/reports/{obj.id}/download/"
