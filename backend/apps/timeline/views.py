from rest_framework import viewsets
from apps.authentication.permissions import IsAnalystOrAbove
from .models import TimelineEvent
from .serializers import TimelineEventSerializer


class TimelineEventViewSet(viewsets.ModelViewSet):
    queryset = TimelineEvent.objects.all().select_related("case", "evidence")
    serializer_class = TimelineEventSerializer
    permission_classes = [IsAnalystOrAbove]
    filterset_fields = ("case", "kind", "evidence")
    search_fields = ("title", "description", "occurred_at_text")
    ordering_fields = ("occurred_at", "created_at")
