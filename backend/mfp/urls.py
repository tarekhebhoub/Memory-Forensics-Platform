"""Root URL configuration for the MFP backend."""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

api_v1 = [
    # Auth
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("auth/", include("apps.authentication.urls")),

    # Domain
    path("cases/", include("apps.cases.urls")),
    path("evidence/", include("apps.evidence.urls")),
    path("analysis/", include("apps.analysis.urls")),
    path("reports/", include("apps.reports.urls")),
    path("timeline/", include("apps.timeline.urls")),
    path("ioc/", include("apps.ioc.urls")),
    path("ai/", include("apps.ai_engine.urls")),
    path("audit/", include("apps.audit.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include((api_v1, "api"), namespace="v1")),

    # OpenAPI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
