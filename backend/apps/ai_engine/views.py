from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.authentication.permissions import IsAnalystOrAbove
from apps.cases.models import Case

from . import services
from .models import AIInsight
from .serializers import AIInsightSerializer


class AIInsightViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AIInsight.objects.all().select_related("case", "created_by")
    serializer_class = AIInsightSerializer
    permission_classes = [IsAnalystOrAbove]
    filterset_fields = ("case", "kind")

    @action(detail=False, methods=["post"], url_path=r"summarize/(?P<case_id>\d+)")
    def summarize(self, request, case_id=None):
        try:
            case = Case.objects.get(pk=case_id)
        except Case.DoesNotExist:
            return Response({"detail": "Case not found."}, status=status.HTTP_404_NOT_FOUND)
        insight = services.summarize_case(case, actor=request.user)
        return Response(AIInsightSerializer(insight).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path=r"classify/(?P<case_id>\d+)")
    def classify(self, request, case_id=None):
        try:
            case = Case.objects.get(pk=case_id)
        except Case.DoesNotExist:
            return Response({"detail": "Case not found."}, status=status.HTTP_404_NOT_FOUND)
        insight = services.classify_threat(case, actor=request.user)
        return Response(AIInsightSerializer(insight).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path=r"recommend/(?P<case_id>\d+)")
    def recommend(self, request, case_id=None):
        try:
            case = Case.objects.get(pk=case_id)
        except Case.DoesNotExist:
            return Response({"detail": "Case not found."}, status=status.HTTP_404_NOT_FOUND)
        insight = services.recommend_next_steps(case, actor=request.user)
        return Response(AIInsightSerializer(insight).data, status=status.HTTP_201_CREATED)
