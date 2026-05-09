from django.contrib import admin
from .models import TimelineEvent


@admin.register(TimelineEvent)
class TimelineEventAdmin(admin.ModelAdmin):
    list_display = ("case", "kind", "title", "occurred_at_text", "created_at")
    list_filter = ("kind",)
