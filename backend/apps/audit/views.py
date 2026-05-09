from rest_framework import mixins, viewsets

from apps.authentication.permissions import IsAdmin

from .models import AuditEvent
from .serializers import AuditEventSerializer


class AuditEventViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Audit log is read-only and admin-restricted."""
    queryset = AuditEvent.objects.all()
    serializer_class = AuditEventSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ("action", "target_type", "severity", "actor_username")
    search_fields = ("action", "path", "actor_username", "target_id")
    ordering_fields = ("timestamp", "severity")
