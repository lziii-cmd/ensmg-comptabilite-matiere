from django.contrib import admin
from core.models import Sequence

@admin.register(Sequence)
class SequenceAdmin(admin.ModelAdmin):
    list_display = ("type_piece", "exercice", "dernier_numero")
    list_per_page = 20
    list_filter = ("type_piece", "exercice")
    search_fields = ("type_piece",)
