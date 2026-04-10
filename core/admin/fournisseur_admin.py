# core/admin/fournisseur_admin.py
# =============================================================================
# Admin Fournisseur & FournisseurSequence
#  - Toujours visibles
#  - Lecture seule si la sélection d’exercices est uniquement CLOS
#  - Boutons d’enregistrement/ajout/suppression/actions masqués quand clos
# =============================================================================
from django.contrib import admin
from core.models import Fournisseur, FournisseurSequence
from core.utils.exercices import selection_is_closed_only
from core.admin.detail_view_mixin import DetailViewMixin


# ----------------------------------------------------------------------------- 
# Utils communs
# -----------------------------------------------------------------------------
class _ClosedContextMixin:
    """Mixin pour verrouiller l'admin en lecture seule si contexte clos."""
    def _is_closed_context(self, request) -> bool:
        return selection_is_closed_only(request)

    def has_view_permission(self, request, obj=None):
        # Toujours consultable (liste + détail)
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
            # Tous les champs en lecture seule (en plus des readonly définis)
            return sorted({*(f.name for f in self.model._meta.fields), *super().get_readonly_fields(request, obj)})
        return super().get_readonly_fields(request, obj)

    def get_actions(self, request):
        if self._is_closed_context(request):
            return {}
        return super().get_actions(request)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        # Alimente le template avec le flag pour masquer les boutons via HTML
        extra_context = extra_context or {}
        extra_context["closed_context"] = self._is_closed_context(request)
        return super().changeform_view(request, object_id, form_url, extra_context)


# ----------------------------------------------------------------------------- 
# Fournisseur
# -----------------------------------------------------------------------------
@admin.register(Fournisseur)
class FournisseurAdmin(DetailViewMixin, _ClosedContextMixin, admin.ModelAdmin):
    list_display = ("identifiant", "raison_sociale", "ninea", "numero", "courriel", "code_prefix","adresse")
    list_filter = ("ninea","adresse")
    search_fields = ("identifiant", "raison_sociale", "ninea", "code_prefix", "courriel", "numero")
    ordering = ("raison_sociale",)

    readonly_fields = ("identifiant",)

    fieldsets = (
        ("Identité", {"fields": ("identifiant", "raison_sociale", "ninea", "code_prefix")}),
        #("Identité", {"fields": ("identifiant", "raison_sociale", "ninea", "code_prefix", "actif")}),
        ("Coordonnées", {"fields": ("adresse", "numero", "courriel")}),
    )


# ----------------------------------------------------------------------------- 
# FournisseurSequence (numérotation document par fournisseur/année)
# -----------------------------------------------------------------------------
@admin.register(FournisseurSequence)
class FournisseurSequenceAdmin(DetailViewMixin, _ClosedContextMixin, admin.ModelAdmin):
    list_display = ("fournisseur", "type_doc", "annee", "next_seq")
    list_filter = ("type_doc", "annee", "fournisseur")
    search_fields = ("fournisseur__raison_sociale", "fournisseur__code_prefix")
    ordering = ("-annee", "fournisseur__raison_sociale", "type_doc")

    fields = ("fournisseur", "type_doc", "annee", "next_seq")
    autocomplete_fields = ("fournisseur",)
