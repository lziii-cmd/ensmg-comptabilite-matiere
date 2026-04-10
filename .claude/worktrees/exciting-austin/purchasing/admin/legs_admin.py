from django.contrib import admin
from core.admin.mixins import AgentRestrictedMixin
from core.admin.detail_view_mixin import DetailViewMixin
from core.models.external_source import ExternalSource
from purchasing.models.legs_entry import LegsEntry
from purchasing.models.external_stock_entry_line import ExternalStockEntryLine


class LegsEntryLineInline(admin.TabularInline):
    model = ExternalStockEntryLine
    extra = 1
    readonly_fields = ("total_line",)
    verbose_name        = "Article reçu"
    verbose_name_plural = "Articles reçus"


@admin.register(LegsEntry)
class LegsEntryAdmin(DetailViewMixin, AgentRestrictedMixin, admin.ModelAdmin):

    list_display   = ("code", "received_date", "source", "depot", "total_value")
    list_filter    = ("source", "depot")
    search_fields  = ("code", "document_number", "source__name", "source__acronym")
    date_hierarchy = "received_date"
    inlines        = [LegsEntryLineInline]
    readonly_fields = ("code", "total_value")

    def get_queryset(self, request):
        """Afficher uniquement les entrées de type Legs."""
        return super().get_queryset(request).filter(source__source_type="LEGS")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limiter les sources aux sources de type Legs."""
        if db_field.name == "source":
            kwargs["queryset"] = ExternalSource.objects.filter(source_type="LEGS")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    detail_print_buttons = [
        {"url_name": "documents:dotation_bon_entree", "label": "BE", "icon": "📋"},
    ]

    detail_fields_sections = [
        {
            "titre": "Informations du legs",
            "fields": [
                ("Code",               "code"),
                ("Source (légataire)", "source"),
                ("Date de réception",  lambda o: o.received_date.strftime("%d/%m/%Y") if o.received_date else "—"),
                ("Dépôt",              "depot"),
                ("N° acte / document", "document_number"),
                ("Valeur totale",      lambda o: f"{int(o.total_value or 0):,} F CFA".replace(",", "\u202f"), "montant"),
            ],
        },
        {
            "titre": "Commentaire",
            "obs_field": "comment",
            "fields": [],
        },
    ]

    detail_inline_models = [
        {
            "titre": "Biens reçus par legs",
            "qs": lambda obj: obj.lines.select_related("matiere").all(),
            "colonnes": [
                {"label": "Désignation",   "accessor": lambda l: l.matiere,                                                  "css": "td-primary"},
                {"label": "Quantité",      "accessor": "quantity",                                                           "css": "td-num center"},
                {"label": "Prix unitaire", "accessor": lambda l: f"{int(l.unit_price or 0):,} F CFA".replace(",", "\u202f"), "css": "td-num right"},
                {"label": "Total",         "accessor": lambda l: f"{int(l.total_line or 0):,} F CFA".replace(",", "\u202f"), "css": "td-num right"},
                {"label": "Note",          "accessor": lambda l: l.note or "—",                                              "css": ""},
            ],
            "total_value_fn": lambda obj, items: f"{int(obj.total_value or 0):,} F CFA".replace(",", "\u202f"),
            "total_label": "TOTAL VALEUR",
        }
    ]
