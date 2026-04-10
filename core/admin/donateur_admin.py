# core/admin/donateur_admin.py
from django.contrib import admin
from core.models import Donateur
from core.admin.detail_view_mixin import DetailViewMixin
from core.utils.exercices import selection_is_closed_only


@admin.register(Donateur)
class DonateurAdmin(DetailViewMixin, admin.ModelAdmin):
    list_display = ("identifiant", "raison_sociale", "code_prefix", "telephone", "courriel", "actif")
    list_filter = ("actif",)
    search_fields = ("identifiant", "raison_sociale", "code_prefix", "telephone", "courriel")
    detail_fields_sections = [
        {
            "titre": "Identification",
            "fields": [
                ("Identifiant",    "identifiant"),
                ("Raison sociale", "raison_sociale"),
                ("Code préfixe",   "code_prefix"),
                ("Actif",          lambda o: "✅ Oui" if o.actif else "❌ Non"),
            ],
        },
        {
            "titre": "Coordonnées",
            "fields": [
                ("Adresse",    "adresse"),
                ("Téléphone",  "telephone"),
                ("Courriel",   "courriel"),
            ],
        },
        {
            "titre": "Remarque",
            "obs_field": "remarque",
            "fields": [],
        },
    ]
    readonly_fields = ("identifiant",)

    fieldsets = (
        ("Identification", {"fields": ("identifiant", "raison_sociale", "code_prefix", "actif")}),
        ("Coordonnées", {"fields": ("adresse", "telephone", "courriel")}),
        ("Remarque", {"fields": ("remarque",)}),
    )

    # ─────────────────────────────────────────────
    # Lecture seule si exercices clos sélectionnés
    # ─────────────────────────────────────────────
    def _is_closed_context(self, request) -> bool:
        """True si tous les exercices cochés dans la barre 'Exercices' sont CLOS."""
        return selection_is_closed_only(request)

    def has_view_permission(self, request, obj=None):
        # Toujours consultable (liste + détail)
        return True

    def has_add_permission(self, request):
        # Interdit l'ajout si contexte clos
        if self._is_closed_context(request):
            return False
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        # Interdit la modification si contexte clos
        if self._is_closed_context(request):
            return False
        return super().has_change_permission(request, obj=obj)

    def has_delete_permission(self, request, obj=None):
        # Interdit la suppression si contexte clos
        if self._is_closed_context(request):
            return False
        return super().has_delete_permission(request, obj=obj)

    def get_readonly_fields(self, request, obj=None):
        # Tous les champs deviennent readonly si clos (en plus de 'identifiant')
        if self._is_closed_context(request):
            return sorted({*(f.name for f in self.model._meta.fields), *self.readonly_fields})
        return super().get_readonly_fields(request, obj)

    def get_actions(self, request):
        # Supprime les actions si clos
        if self._is_closed_context(request):
            return {}
        return super().get_actions(request)
