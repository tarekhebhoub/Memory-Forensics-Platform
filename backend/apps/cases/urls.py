from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import CaseNoteViewSet, CaseViewSet

notes_router = SimpleRouter()
notes_router.register(r"notes", CaseNoteViewSet, basename="case-note")

cases_router = SimpleRouter()
cases_router.register(r"", CaseViewSet, basename="case")

urlpatterns = [
    path("", include(notes_router.urls)),
    path("", include(cases_router.urls)),
]
