from django.contrib import admin
from .models import AIInsight


@admin.register(AIInsight)
class AIInsightAdmin(admin.ModelAdmin):
    list_display = ("case", "kind", "title", "model_used", "confidence", "created_at")
    list_filter = ("kind", "model_used")
