from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import EvidenceViewSet, UploadSessionViewSet

upload_router = SimpleRouter()
upload_router.register(r"uploads", UploadSessionViewSet, basename="upload-session")

evidence_router = SimpleRouter()
evidence_router.register(r"", EvidenceViewSet, basename="evidence")

urlpatterns = [
    path("", include(upload_router.urls)),
    path("", include(evidence_router.urls)),
]
