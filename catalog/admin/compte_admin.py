# catalog/admin/compte_admin.py
# ───────────────────────────────────────────────────────────────
# Admin Comptes avec verrouillage lecture seule si exercices clos
# ───────────────────────────────────────────────────────────────

from django import forms
from django.contrib import admin
from core.admin.detail_view_mixin import DetailViewMixin
from django.core.exceptions import ValidationError
from core.utils.exercices import selection_is_closed_only

from catalog.models import ComptePrincipal, CompteDivisionnaire, SousCompte


# ===============================================================
# Compte Principal
# ===============================================================
class ComptePrincipalForm(forms.ModelForm):
    class Meta:
        model = ComptePrincipal
        fields = ("libelle", "groupe", "description", "actif")

    def clean(self):
        cleaned = super().clean()
        groupe = cleaned.get("groupe")
        if not groupe:
            raise ValidationError({"groupe": "Le groupe est obligatoire."})
        return cleaned


@admin.register(ComptePrincipal)
class ComptePrincipalAdmin(DetailViewMixin, admin.ModelAdmin):
    form = ComptePrincipalForm
    list_display = ("code", "libelle", "groupe", "actif")
    search_fields = ("code", "libelle", "description")
    list_filter = ("groupe", "actif")
    ordering = ("code",)
    readonly_fields = tuple(f for f in ("code", "pin") if hasattr(ComptePrincipal, f))

    def get_fieldsets(self, request, obj=None):
        sys_fields = tuple(f for f in ("code", "pin") if f in self.readonly_fields)
        return (
            ("Identification", {"fields": ("libelle", "groupe", "description", "actif")}),
            ("Système", {
                "fields": sys_fields,
                "description": (
                    "<ul>"
                    "<li><b>Groupe 1</b> → codes 10, 11, 12, …</li>"
                    "<li><b>Groupe 2</b> → codes 20, 21, 22, …</li>"
                    "</ul>"
                ),
            }),
        )

    # ---------- Lecture seule si exercice clos ----------
    def _is_closed_context(self, request) -> bool:
        return selection_is_closed_only(request)

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


# ===============================================================
# Compte Divisionnaire
# ===============================================================
@admin.register(CompteDivisionnaire)
class CompteDivisionnaireAdmin(DetailViewMixin, admin.ModelAdmin):
    list_display = ("code", "libelle", "compte_principal", "actif")
    search_fields = ("code", "libelle", "description", "compte_principal__libelle")
    list_filter = ("compte_principal", "actif")
    ordering = ("code",)
    readonly_fields = tuple(f for f in ("code", "pin") if hasattr(CompteDivisionnaire, f))
    autocomplete_fields = ("compte_principal",)
    fields = ("compte_principal", "libelle", "description", "actif") + readonly_fields
    list_select_related = ("compte_principal",)

    # ---------- Lecture seule si exercice clos ----------
    def _is_closed_context(self, request) -> bool:
        return selection_is_closed_only(request)

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


# ===============================================================
# Sous-compte
# ===============================================================
@admin.register(SousCompte)
class SousCompteAdmin(DetailViewMixin, admin.ModelAdmin):
    list_display = ("code", "libelle", "compte_divisionnaire", "actif")
    search_fields = ("code", "libelle", "description", "compte_divisionnaire__libelle")
    list_filter = ("compte_divisionnaire", "actif")
    ordering = ("code",)
    readonly_fields = tuple(f for f in ("code", "pin") if hasattr(SousCompte, f))
    autocomplete_fields = ("compte_divisionnaire",)
    fields = ("compte_divisionnaire", "libelle", "description", "actif") + readonly_fields
    list_select_related = ("compte_divisionnaire",)

    detail_fields_sections = [
        {
            "titre": "Identification",
            "fields": [
                ("Code",       "code"),
                ("Libelle",    "libelle"),
                ("Description", "description"),
                ("Actif",      lambda o: "✅ Oui" if o.actif else "❌ Non"),
            ],
        },
        {
            "titre": "Hiérarchie comptable",
            "fields": [
                ("Compte principal", lambda o: (
                    f"{o.compte_divisionnaire.compte_principal.code} — {o.compte_divisionnaire.compte_principal.libelle}"
                    if o.compte_divisionnaire and o.compte_divisionnaire.compte_principal else "—"
                )),
                ("Compte divisionnaire", lambda o: (
                    f"{o.compte_divisionnaire.code} — {o.compte_divisionnaire.libelle}"
                    if o.compte_divisionnaire else "—"
                )),
            ],
        },
    ]

    # ---------- Lecture seule si exercice clos ----------
    def _is_closed_context(self, request) -> bool:
        return selection_is_closed_only(request)

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
