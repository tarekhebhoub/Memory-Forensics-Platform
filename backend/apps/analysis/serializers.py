from rest_framework import serializers
from .models import AnalysisJob, PluginResult


class PluginResultSerializer(serializers.ModelSerializer):
    row_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PluginResult
        fields = (
            "id", "plugin_name", "status", "started_at", "completed_at",
            "duration_ms", "error", "summary", "row_count",
        )


class PluginResultDetailSerializer(serializers.ModelSerializer):
    row_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PluginResult
        fields = (
            "id", "plugin_name", "status", "started_at", "completed_at",
            "duration_ms", "error", "raw_output", "parsed_rows", "summary",
            "row_count",
        )


class AnalysisJobSerializer(serializers.ModelSerializer):
    plugin_results = PluginResultSerializer(many=True, read_only=True)
    evidence_name = serializers.CharField(source="evidence.name", read_only=True)
    case = serializers.IntegerField(source="evidence.case_id", read_only=True)
    case_code = serializers.CharField(source="evidence.case.code", read_only=True)

    class Meta:
        model = AnalysisJob
        fields = (
            "id", "uid", "evidence", "evidence_name", "case", "case_code",
            "requested_by", "plugins", "status", "error", "mode",
            "started_at", "completed_at", "created_at",
            "detected_os", "risk_score",
            "detections", "mitre_techniques",
            "plugin_results",
        )
        read_only_fields = fields
