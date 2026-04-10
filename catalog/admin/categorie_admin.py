# catalog/admin/categorie_admin.py
from django.contrib import admin
from django.utils.html import format_html
from core.admin.detail_view_mixin import DetailViewMixin

from catalog.models import Categorie  # ✅ bon import
from core.utils.exercices import selection_is_closed_only


@admin.register(Categorie)
class CategorieAdmin(DetailViewMixin, admin.ModelAdmin):
    list_display = ("code", "libelle", "actif", "description_short")
    list_filter = ("actif",)
    search_fields = ("code", "libelle", "description")

    fieldsets = (
        ("Informations principales", {
            "fields": ("code", "libelle", "description", "actif"),
        }),
    )

    # ---------- Contexte clos = lecture seule ----------
    def _is_closed_context(self, request) -> bool:
        return selection_is_closed_only(request)

    def has_view_permission(self, request, obj=None):
        # Toujours consultable
        return True

    def has_add_permission(self, request):
        if self._is_closed_context(request):
            return False
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if self._is_closed_context(request):
            return False
        return super().has_change_permission(request, obj=obj)

    def has_delete_permission(self, request, obj=None):
        if self._is_closed_context(request):
            return False
        return super().has_delete_permission(request, obj=obj)

    def get_readonly_fields(self, request, obj=None):
        if self._is_closed_context(request):
            return [f.name for f in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)

    def get_actions(self, request):
        if self._is_closed_context(request):
            return {}
        return super().get_actions(request)

    # ---------- Helpers ----------
    def description_short(self, obj):
        if not obj.description:
            return "-"
        txt = obj.description.strip()
        return txt if len(txt) <= 60 else f"{txt[:60]}…"
    description_short.short_description = "Description"
