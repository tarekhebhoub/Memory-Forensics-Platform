from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.authentication.permissions import IsAnalystOrAbove
from apps.cases.models import Case

from . import services
from .models import Evidence, UploadSession
from .serializers import (
    EvidenceSerializer,
    EvidenceUploadSerializer,
    UploadChunkSerializer,
    UploadFinalizeSerializer,
    UploadSessionInitSerializer,
    UploadSessionSerializer,
)


class EvidenceViewSet(viewsets.ModelViewSet):
    queryset = Evidence.objects.all().select_related("case", "uploaded_by")
    serializer_class = EvidenceSerializer
    permission_classes = [IsAnalystOrAbove]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filterset_fields = ("case", "kind", "status", "os_profile_hint")
    search_fields = ("name", "sha256", "md5")
    ordering_fields = ("uploaded_at", "size_bytes")

    @action(detail=False, methods=["post"], url_path="upload",
            parser_classes=[MultiPartParser, FormParser])
    def upload(self, request):
        ser = EvidenceUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            case = Case.objects.get(pk=ser.validated_data["case"])
        except Case.DoesNotExist:
            return Response({"detail": "Case not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            evidence = services.store_uploaded_file(
                case=case,
                uploaded_file=ser.validated_data["file"],
                uploader=request.user,
                description=ser.validated_data.get("description", ""),
                os_hint=ser.validated_data.get("os_hint", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EvidenceSerializer(evidence).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="verify")
    def verify(self, request, pk=None):
        evidence = self.get_object()
        ok = services.verify_integrity(evidence)
        return Response({"ok": ok, "status": evidence.status, "sha256": evidence.sha256})

    @action(detail=True, methods=["post"], url_path="analyze")
    def analyze(self, request, pk=None):
        """Trigger Volatility analysis. Pass ``?mode=deep`` (or ``mode`` in body)
        to run the full kernel + persistence + credential plugin sweep.
        Returns the AnalysisJob id."""
        from apps.analysis.services import enqueue_full_analysis
        evidence = self.get_object()
        mode = (request.query_params.get("mode")
                or request.data.get("mode")
                or "standard").lower()
        if mode not in ("standard", "deep"):
            mode = "standard"
        job = enqueue_full_analysis(evidence=evidence, requested_by=request.user,
                                    mode=mode)
        return Response({"job_id": job.id, "uid": str(job.uid),
                         "status": job.status, "mode": mode,
                         "plugin_count": len(job.plugins)},
                        status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"], url_path="deep-analyze")
    def deep_analyze(self, request, pk=None):
        """Convenience endpoint: same as analyze with mode=deep."""
        from apps.analysis.services import enqueue_full_analysis
        evidence = self.get_object()
        job = enqueue_full_analysis(evidence=evidence, requested_by=request.user,
                                    mode="deep")
        return Response({"job_id": job.id, "uid": str(job.uid),
                         "status": job.status, "mode": "deep",
                         "plugin_count": len(job.plugins)},
                        status=status.HTTP_202_ACCEPTED)


class UploadSessionViewSet(viewsets.GenericViewSet):
    """Chunked upload protocol for very large memory dumps."""
    queryset = UploadSession.objects.all()
    serializer_class = UploadSessionSerializer
    permission_classes = [IsAnalystOrAbove]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    lookup_field = "uid"

    def list(self, request):
        qs = self.get_queryset().filter(initiated_by=request.user)
        return Response(UploadSessionSerializer(qs, many=True).data)

    def retrieve(self, request, uid=None):
        session = self.get_object()
        return Response(UploadSessionSerializer(session).data)

    @action(detail=False, methods=["post"], url_path="init")
    def init(self, request):
        ser = UploadSessionInitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            case = Case.objects.get(pk=ser.validated_data["case"])
        except Case.DoesNotExist:
            return Response({"detail": "Case not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            session = services.init_chunked_upload(
                case=case,
                filename=ser.validated_data["filename"],
                total_size=ser.validated_data["total_size"],
                chunk_size=ser.validated_data["chunk_size"],
                uploader=request.user,
                expected_sha256=ser.validated_data.get("expected_sha256", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UploadSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="chunk",
            parser_classes=[MultiPartParser, FormParser])
    def chunk(self, request, uid=None):
        session = self.get_object()
        ser = UploadChunkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            services.append_chunk(
                session,
                chunk_index=ser.validated_data["chunk_index"],
                chunk=ser.validated_data["chunk"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UploadSessionSerializer(session).data)

    @action(detail=True, methods=["post"], url_path="finalize")
    def finalize(self, request, uid=None):
        session = self.get_object()
        ser = UploadFinalizeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            evidence = services.finalize_chunked_upload(
                session, uploader=request.user,
                description=ser.validated_data.get("description", ""),
                os_hint=ser.validated_data.get("os_hint", ""),
            )
        except (ValueError, FileNotFoundError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EvidenceSerializer(evidence).data, status=status.HTTP_201_CREATED)
