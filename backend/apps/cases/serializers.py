from __future__ import annotations

from rest_framework import serializers

from apps.authentication.serializers import UserSerializer

from .models import Case, CaseNote, ChainOfCustody


class ChainOfCustodySerializer(serializers.ModelSerializer):
    class Meta:
        model = ChainOfCustody
        fields = ("id", "actor_username", "action", "description", "metadata", "timestamp")
        read_only_fields = fields


class CaseNoteSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = CaseNote
        fields = ("id", "case", "author", "author_username", "body", "pinned",
                  "created_at", "updated_at")
        read_only_fields = ("author", "author_username", "created_at", "updated_at")


class CaseSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    lead_analyst = UserSerializer(read_only=True)
    lead_analyst_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    assignees = UserSerializer(many=True, read_only=True)
    assignee_ids = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, required=False, source="assignees",
        queryset=__import__("apps.authentication.models", fromlist=["User"]).User.objects.all(),
    )
    evidence_count = serializers.SerializerMethodField()
    notes_count = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = (
            "id", "uid", "code", "title", "description",
            "status", "severity", "classification",
            "created_by", "lead_analyst", "lead_analyst_id",
            "assignees", "assignee_ids",
            "opened_at", "closed_at", "updated_at",
            "tags",
            "evidence_count", "notes_count",
        )
        read_only_fields = ("uid", "opened_at", "updated_at", "created_by")

    def get_evidence_count(self, obj) -> int:
        return obj.evidence.count() if hasattr(obj, "evidence") else 0

    def get_notes_count(self, obj) -> int:
        return obj.notes.count()

    def update(self, instance, validated_data):
        if "lead_analyst_id" in validated_data:
            instance.lead_analyst_id = validated_data.pop("lead_analyst_id")
        return super().update(instance, validated_data)
