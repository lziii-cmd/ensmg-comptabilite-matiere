from django.contrib import admin
from core.models.external_source import ExternalSource


@admin.register(ExternalSource)
class ExternalSourceAdmin(admin.ModelAdmin):
    list_display = ("source_type", "acronym", "name", "is_active")
    list_per_page = 20
    list_filter = ("source_type", "is_active")
    search_fields = ("name", "acronym")
    ordering = ("source_type", "name")
