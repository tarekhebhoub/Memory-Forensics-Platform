from rest_framework import serializers
from .models import Evidence, UploadSession


class EvidenceSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(source="uploaded_by.username", read_only=True)
    case_code = serializers.CharField(source="case.code", read_only=True)

    class Meta:
        model = Evidence
        fields = (
            "id", "uid", "case", "case_code", "kind", "name", "description",
            "size_bytes", "mime_type", "sha256", "md5", "os_profile_hint",
            "status", "uploaded_by", "uploaded_by_username",
            "uploaded_at", "verified_at", "last_analyzed_at", "metadata",
        )
        read_only_fields = (
            "uid", "size_bytes", "sha256", "md5", "status",
            "uploaded_by", "uploaded_at", "verified_at", "last_analyzed_at",
            "case_code", "uploaded_by_username", "mime_type",
        )


class EvidenceUploadSerializer(serializers.Serializer):
    case = serializers.IntegerField()
    file = serializers.FileField()
    description = serializers.CharField(required=False, allow_blank=True, default="")
    os_hint = serializers.CharField(required=False, allow_blank=True, default="")


class UploadSessionInitSerializer(serializers.Serializer):
    case = serializers.IntegerField()
    filename = serializers.CharField(max_length=255)
    total_size = serializers.IntegerField(min_value=1)
    chunk_size = serializers.IntegerField(min_value=1024, default=8 * 1024 * 1024)
    expected_sha256 = serializers.CharField(required=False, allow_blank=True, max_length=64, default="")


class UploadSessionSerializer(serializers.ModelSerializer):
    progress = serializers.FloatField(read_only=True)

    class Meta:
        model = UploadSession
        fields = (
            "id", "uid", "case", "filename", "total_size", "chunk_size",
            "received_bytes", "received_chunks", "expected_sha256", "final_sha256",
            "status", "started_at", "completed_at", "progress",
        )
        read_only_fields = fields


class UploadChunkSerializer(serializers.Serializer):
    chunk_index = serializers.IntegerField(min_value=0)
    chunk = serializers.FileField()


class UploadFinalizeSerializer(serializers.Serializer):
    description = serializers.CharField(required=False, allow_blank=True, default="")
    os_hint = serializers.CharField(required=False, allow_blank=True, default="")
