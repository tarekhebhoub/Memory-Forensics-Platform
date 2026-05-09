from rest_framework.routers import DefaultRouter
from .views import IOCViewSet

router = DefaultRouter()
router.register(r"", IOCViewSet, basename="ioc")
urlpatterns = router.urls
