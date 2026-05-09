from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.authentication.permissions import IsAnalystOrAbove

from . import services
from .models import Case, CaseNote, ChainOfCustody
from .serializers import CaseNoteSerializer, CaseSerializer, ChainOfCustodySerializer


class CaseViewSet(viewsets.ModelViewSet):
    queryset = Case.objects.all().select_related("created_by", "lead_analyst").prefetch_related("assignees")
    serializer_class = CaseSerializer
    permission_classes = [IsAnalystOrAbove]
    filterset_fields = ("status", "severity", "lead_analyst", "classification")
    search_fields = ("code", "title", "description", "tags")
    ordering_fields = ("opened_at", "updated_at", "severity", "status")

    def perform_create(self, serializer):
        # Use service layer so chain-of-custody + audit are recorded.
        data = serializer.validated_data
        case = services.create_case(
            code=data["code"], title=data["title"],
            description=data.get("description", ""),
            severity=data.get("severity", Case.Severity.MEDIUM),
            classification=data.get("classification", ""),
            created_by=self.request.user,
            tags=data.get("tags", []),
        )
        serializer.instance = case

    @action(detail=True, methods=["post"], url_path="status")
    def set_status(self, request, pk=None):
        case = self.get_object()
        new_status = request.data.get("status")
        if new_status not in dict(Case.Status.choices):
            return Response({"detail": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)
        case = services.change_status(case, new_status=new_status, actor=request.user)
        return Response(CaseSerializer(case).data)

    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, pk=None):
        case = self.get_object()
        ids = request.data.get("user_ids") or []
        if not isinstance(ids, list):
            return Response({"detail": "user_ids must be a list."}, status=status.HTTP_400_BAD_REQUEST)
        case = services.assign_users(case, user_ids=ids, actor=request.user)
        return Response(CaseSerializer(case).data)

    @action(detail=True, methods=["get"], url_path="custody")
    def custody(self, request, pk=None):
        case = self.get_object()
        return Response(ChainOfCustodySerializer(case.custody_log.all(), many=True).data)


class CaseNoteViewSet(viewsets.ModelViewSet):
    queryset = CaseNote.objects.all().select_related("case", "author")
    serializer_class = CaseNoteSerializer
    permission_classes = [IsAnalystOrAbove]
    filterset_fields = ("case", "pinned")
    search_fields = ("body",)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
