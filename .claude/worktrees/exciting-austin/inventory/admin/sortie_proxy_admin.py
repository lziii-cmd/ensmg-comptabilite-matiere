# inventory/admin/sortie_proxy_admin.py
"""
Admins dédiés aux proxy models SortieCertificatAdmin et SortieFinGestion.
Ces classes héritent entièrement d'OperationSortieAdmin et se distinguent
par :
  - un get_queryset filtré sur le type_sortie correspondant
  - un save_model qui force le bon type_sortie à la création
  - des labels/titres adaptés
  - des boutons de document spécifiques
"""

from django.contrib import admin
from django.urls import resolve

from core.utils.exercices import filter_qs_by_exercices_dates
from inventory.admin.operation_sortie_admin import (
    OperationSortieAdmin,
    LigneOperationSortieInline,
    _OperationSortieAdminForm,
)
from inventory.models import (
    SortieCertificatAdmin,
    SortieFinGestion,
    OperationSortie,
)


# ─────────────────────────────────────────────────────────────────────────────
# Sortie par certificat administratif
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(SortieCertificatAdmin)
class SortieCertificatAdminAdmin(OperationSortieAdmin):
    """
    Page dédiée aux sorties justifiées par certificat administratif
    (Instruction Générale Art. 17b, 18c — Modèle n°9).
    """

    # ── Documents disponibles ──
    detail_print_buttons = [
        {"url_name": "documents:sortie_document",          "label": "Bon de sortie",            "icon": "🖨"},
        {"url_name": "documents:certificat_administratif", "label": "Certificat administratif", "icon": "📄"},
    ]

    # ── Colonnes de liste ──
    list_display = ("code_or_temp", "date_sortie", "depot", "motif_principal", "total_valeur")
    list_filter = ("depot", "date_sortie")

    # ── Fieldsets : on masque le champ type_sortie (fixé automatiquement) ──
    fieldsets = (
        ("Informations générales", {
            "fields": (
                "code",
                "date_sortie",
                "depot",
                "motif_principal",
                "commentaire",
            ),
        }),
        ("Justificatif", {
            "fields": ("numero_document", "fichier_document", "document_link"),
        }),
        ("Valorisation", {
            "fields": ("total_valeur",),
        }),
    )

    # ── Force le type à la création ──
    def save_model(self, request, obj, form, change):
        obj.type_sortie = OperationSortie.TypeSortie.CERTIFICAT_ADMIN
        super().save_model(request, obj, form, change)

    # ── Filtre le queryset ──
    def get_queryset(self, request):
        qs = super(OperationSortieAdmin, self).get_queryset(request).select_related("depot")
        qs = qs.filter(type_sortie=OperationSortie.TypeSortie.CERTIFICAT_ADMIN)
        try:
            view_name = (resolve(request.path_info).url_name or "")
        except Exception:
            view_name = ""
        if view_name.endswith("_add") or view_name.endswith("_change") or view_name.endswith("_history"):
            return qs
        return filter_qs_by_exercices_dates(qs, request, date_field="date_sortie")


# ─────────────────────────────────────────────────────────────────────────────
# Opérations de fin de gestion
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(SortieFinGestion)
class SortieFinGestionAdmin(OperationSortieAdmin):
    """
    Page dédiée aux opérations de fin de gestion.
    """

    # ── Documents disponibles ──
    detail_print_buttons = [
        {"url_name": "documents:sortie_document", "label": "Bon de sortie", "icon": "🖨"},
    ]

    # ── Colonnes de liste ──
    list_display = ("code_or_temp", "date_sortie", "depot", "motif_principal", "total_valeur")
    list_filter = ("depot", "date_sortie")

    # ── Fieldsets ──
    fieldsets = (
        ("Informations générales", {
            "fields": (
                "code",
                "date_sortie",
                "depot",
                "motif_principal",
                "commentaire",
            ),
        }),
        ("Justificatif", {
            "fields": ("numero_document", "fichier_document", "document_link"),
        }),
        ("Valorisation", {
            "fields": ("total_valeur",),
        }),
    )

    # ── Force le type à la création ──
    def save_model(self, request, obj, form, change):
        obj.type_sortie = OperationSortie.TypeSortie.FIN_GESTION
        super().save_model(request, obj, form, change)

    # ── Filtre le queryset ──
    def get_queryset(self, request):
        qs = super(OperationSortieAdmin, self).get_queryset(request).select_related("depot")
        qs = qs.filter(type_sortie=OperationSortie.TypeSortie.FIN_GESTION)
        try:
            view_name = (resolve(request.path_info).url_name or "")
        except Exception:
            view_name = ""
        if view_name.endswith("_add") or view_name.endswith("_change") or view_name.endswith("_history"):
            return qs
        return filter_qs_by_exercices_dates(qs, request, date_field="date_sortie")
