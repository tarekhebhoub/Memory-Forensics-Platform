from rest_framework import viewsets
from apps.authentication.permissions import IsAnalystOrAbove

from .models import IOC
from .serializers import IOCSerializer


class IOCViewSet(viewsets.ModelViewSet):
    queryset = IOC.objects.all().select_related("case", "first_seen_evidence")
    serializer_class = IOCSerializer
    permission_classes = [IsAnalystOrAbove]
    filterset_fields = ("case", "kind", "severity", "source_plugin")
    search_fields = ("value", "description", "tags")
    ordering_fields = ("discovered_at", "severity", "confidence")
