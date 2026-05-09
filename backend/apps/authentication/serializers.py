from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Role, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id", "username", "email", "full_name", "title", "phone",
            "role", "mfa_enabled", "is_active", "date_joined", "last_login",
        )
        read_only_fields = ("id", "date_joined", "last_login")


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ("id", "username", "email", "full_name", "title", "phone", "role", "password")

    def create(self, validated_data: dict) -> User:
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])


class RoleSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()

    @staticmethod
    def all() -> list[dict]:
        return [{"value": v, "label": l} for v, l in Role.choices]
