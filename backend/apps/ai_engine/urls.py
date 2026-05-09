from rest_framework.routers import DefaultRouter
from .views import AIInsightViewSet

router = DefaultRouter()
router.register(r"insights", AIInsightViewSet, basename="ai-insight")
urlpatterns = router.urls
