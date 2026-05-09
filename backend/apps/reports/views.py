from __future__ import annotations

import os
from pathlib import Path

from django.http import FileResponse, Http404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.authentication.permissions import IsAnalystOrAbove

from .models import Report
from .serializers import ReportSerializer
from .tasks import generate_report_task


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all().select_related("case", "created_by")
    serializer_class = ReportSerializer
    permission_classes = [IsAnalystOrAbove]
    filterset_fields = ("case", "format", "status")
    ordering_fields = ("created_at", "completed_at")

    def perform_create(self, serializer):
        report = serializer.save(created_by=self.request.user, status=Report.Status.QUEUED)
        generate_report_task.delay(report.id)

    @action(detail=True, methods=["post"], url_path="regenerate")
    def regenerate(self, request, pk=None):
        report = self.get_object()
        report.status = Report.Status.QUEUED
        report.error = ""
        report.save(update_fields=["status", "error"])
        generate_report_task.delay(report.id)
        return Response(ReportSerializer(report).data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        report = self.get_object()
        if report.status != Report.Status.READY or not report.file_path:
            raise Http404("Report not ready.")
        path = Path(report.file_path)
        if not path.exists():
            raise Http404("Report file missing.")
        ctype = "application/pdf" if report.format == Report.Format.PDF else "text/html"
        return FileResponse(open(path, "rb"), as_attachment=True,
                            filename=os.path.basename(path), content_type=ctype)
