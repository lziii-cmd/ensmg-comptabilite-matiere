from django.contrib import admin
from core.models import Unite

@admin.register(Unite)
class UniteAdmin(admin.ModelAdmin):
    list_display = ("abreviation", "libelle")
    list_per_page = 20
    search_fields = ("abreviation", "libelle")
    ordering = ("abreviation",)
