from __future__ import annotations

from django.contrib.auth import update_session_auth_hash
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import User
from .permissions import IsAdmin
from .serializers import (
    PasswordChangeSerializer,
    RoleSerializer,
    UserCreateSerializer,
    UserSerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    """User management — list/create/update restricted to admins; users can read their own profile."""

    queryset = User.objects.all().order_by("username")
    search_fields = ("username", "email", "full_name")
    filterset_fields = ("role", "is_active")

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in {"list", "create", "destroy", "update", "partial_update"}:
            return [IsAdmin()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        return Response(UserSerializer(request.user).data)

    @action(detail=False, methods=["post"], url_path="change-password",
            permission_classes=[IsAuthenticated])
    def change_password(self, request):
        ser = PasswordChangeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(ser.validated_data["old_password"]):
            return Response({"detail": "Old password incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(ser.validated_data["new_password"])
        user.save()
        update_session_auth_hash(request, user)
        return Response({"detail": "Password updated."})

    @action(detail=False, methods=["get"], url_path="roles")
    def roles(self, request):
        return Response(RoleSerializer.all())
