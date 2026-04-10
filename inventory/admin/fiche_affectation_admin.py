# inventory/admin/fiche_affectation_admin.py
from django.contrib import admin
from django.utils.html import format_html
from core.admin.mixins import AgentRestrictedMixin
from core.admin.detail_view_mixin import DetailViewMixin
from inventory.models import FicheAffectation


@admin.register(FicheAffectation)
class FicheAffectationAdmin(DetailViewMixin, AgentRestrictedMixin, admin.ModelAdmin):

    list_display   = ("code", "date_affectation", "statut_badge", "matiere", "quantite", "beneficiaire", "depot")
    list_filter    = ("statut", "depot", "date_affectation")
    search_fields  = ("code", "beneficiaire", "matiere__designation", "matiere__code_court")
    date_hierarchy = "date_affectation"
    readonly_fields = (
        "code", "dotation", "ligne_dotation", "matiere", "quantite",
        "depot", "date_affectation", "mouvement_stock",
    )

    fieldsets = (
        ("Identification", {
            "fields": ("code", "statut", "date_affectation"),
        }),
        ("Bien affecté", {
            "fields": ("matiere", "quantite", "depot"),
        }),
        ("Bénéficiaire", {
            "fields": ("beneficiaire", "service"),
        }),
        ("Source", {
            "fields": ("dotation", "ligne_dotation", "mouvement_stock"),
            "classes": ("collapse",),
        }),
        ("Observations", {
            "fields": ("observations",),
        }),
    )

    # ── Badge statut ──────────────────────────────────────────
    @admin.display(description="Statut", ordering="statut")
    def statut_badge(self, obj):
        colours = {
            "AFFECTE":   ("#1e3a5f", "#dbeafe"),   # bleu marine
            "REINTEGRE": ("#166534", "#dcfce7"),   # vert
            "REFORME":   ("#991b1b", "#fee2e2"),   # rouge
        }
        fg, bg = colours.get(obj.statut, ("#000", "#f3f4f6"))
        return format_html(
            '<span style="padding:2px 10px;border-radius:12px;font-size:11px;'
            'font-weight:600;color:{};background:{}">{}</span>',
            fg, bg, obj.get_statut_display(),
        )

    # ─────────────────────────────────────────────────────────
    # Vue détail
    # ─────────────────────────────────────────────────────────
    detail_print_buttons = [
        {
            "url_name": "documents:fiche_affectation_document",
            "label":    "Fiche d'affectation",
            "icon":     "📋",
        },
    ]

    detail_fields_sections = [
        {
            "titre": "Fiche d'affectation",
            "fields": [
                ("Code FA",            "code"),
                ("Statut",             lambda o: o.get_statut_display()),
                ("Date d'affectation", lambda o: o.date_affectation.strftime("%d/%m/%Y")),
                ("Matière",            "matiere"),
                ("Quantité",           "quantite"),
                ("Dépôt source",       "depot"),
                ("Agent bénéficiaire", "beneficiaire"),
                ("Service",            lambda o: str(o.service) if o.service else "—"),
                ("Dotation source",    "dotation"),
            ],
        },
        {
            "titre": "Observations",
            "obs_field": "observations",
            "fields": [],
        },
    ]
