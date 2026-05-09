from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AnalysisJobViewSet, PluginResultViewSet

results_router = DefaultRouter()
results_router.register(r"results", PluginResultViewSet, basename="plugin-result")

jobs_router = DefaultRouter()
jobs_router.register(r"jobs", AnalysisJobViewSet, basename="analysis-job")

urlpatterns = [
    path("", include(results_router.urls)),
    path("", include(jobs_router.urls)),
]
