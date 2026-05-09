from rest_framework import serializers
from .models import IOC


class IOCSerializer(serializers.ModelSerializer):
    class Meta:
        model = IOC
        fields = "__all__"
