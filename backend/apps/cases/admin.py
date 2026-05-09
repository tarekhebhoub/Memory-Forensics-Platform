from django.contrib import admin
from .models import Case, CaseNote, ChainOfCustody


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "status", "severity", "lead_analyst", "opened_at")
    list_filter = ("status", "severity")
    search_fields = ("code", "title", "description")


@admin.register(CaseNote)
class CaseNoteAdmin(admin.ModelAdmin):
    list_display = ("case", "author", "pinned", "created_at")
    list_filter = ("pinned",)


@admin.register(ChainOfCustody)
class CustodyAdmin(admin.ModelAdmin):
    list_display = ("case", "actor_username", "action", "timestamp")
    list_filter = ("action",)
    readonly_fields = [f.name for f in ChainOfCustody._meta.fields]
