from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.authentication.permissions import IsAnalystOrAbove

from .models import AnalysisJob, PluginResult
from .serializers import (
    AnalysisJobSerializer,
    PluginResultDetailSerializer,
    PluginResultSerializer,
)


class AnalysisJobViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = AnalysisJob.objects.all().select_related("evidence", "evidence__case", "requested_by")
    serializer_class = AnalysisJobSerializer
    permission_classes = [IsAnalystOrAbove]
    filterset_fields = ("status", "evidence", "evidence__case")
    ordering_fields = ("created_at", "completed_at", "risk_score")

    @action(detail=True, methods=["get"], url_path="result/(?P<plugin>[^/.]+)")
    def plugin_detail(self, request, pk=None, plugin=None):
        try:
            pr = PluginResult.objects.get(job_id=pk, plugin_name=plugin)
        except PluginResult.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        return Response(PluginResultDetailSerializer(pr).data)


class PluginResultViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = PluginResult.objects.select_related("job", "job__evidence")
    serializer_class = PluginResultDetailSerializer
    permission_classes = [IsAnalystOrAbove]
    filterset_fields = ("plugin_name", "status", "job")
