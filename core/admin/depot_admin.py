from django.contrib import admin
from django import forms
from django.utils.translation import gettext_lazy as _

from core.models import Depot, Service
from core.utils.exercices import selection_is_closed_only
from core.admin.detail_view_mixin import DetailViewMixin


class DepotAdminForm(forms.ModelForm):
    class Meta:
        model = Depot
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # service uniquement si bureau
        # (JS fera le masquage, mais côté serveur on garde clean() du modèle)
        self.fields["service"].queryset = Service.objects.filter(actif=True).order_by("code")


@admin.register(Depot)
class DepotAdmin(DetailViewMixin, admin.ModelAdmin):
    form = DepotAdminForm

    list_display = ("identifiant", "nom", "type_lieu", "service", "responsable", "localisation", "actif")
    list_filter = ("actif", "type_lieu", "service")
    search_fields = ("identifiant", "nom", "localisation", "service__code", "service__libelle", "responsable")
    ordering = ("identifiant",)

    readonly_fields = ("responsable",)

    fieldsets = (
        (_("Type de lieu"), {"fields": ("type_lieu",)}),  # ✅ tout en haut
        (_("Identification"), {"fields": ("identifiant", "nom", "actif")}),
        (_("Bureau / Service"), {"fields": ("service", "responsable")}),
        (_("Localisation"), {"fields": ("localisation",)}),
    )

    class Media:
        js = ("js/depot_admin.js",)

    # ─────────────────────────────────────────────
    # Lecture seule si exercices clos sélectionnés
    # ─────────────────────────────────────────────
    def _is_closed_context(self, request) -> bool:
        return selection_is_closed_only(request)

    def has_view_permission(self, request, obj=None):
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
