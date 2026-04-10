from django.contrib import admin
from core.admin.mixins import AgentRestrictedMixin
from core.admin.detail_view_mixin import DetailViewMixin
from purchasing.models.external_stock_entry import ExternalStockEntry
from purchasing.models.external_stock_entry_line import ExternalStockEntryLine


class ExternalStockEntryLineInline(admin.TabularInline):
    model = ExternalStockEntryLine
    extra = 1
    readonly_fields = ("total_line",)


@admin.register(ExternalStockEntry)
class ExternalStockEntryAdmin(DetailViewMixin, AgentRestrictedMixin, admin.ModelAdmin):
    list_display = ("code", "received_date", "source", "depot", "total_value")
    list_filter = ("source__source_type", "source", "depot")
    search_fields = ("code", "document_number", "source__name", "source__acronym")
    date_hierarchy = "received_date"
    inlines = [ExternalStockEntryLineInline]
    readonly_fields = ("code", "total_value")
    detail_print_buttons = [
        {
            "url_name":  "documents:dotation_document",
            "label":     "PVR",
            "icon":      "🖨",
            "condition": lambda obj: (obj.total_value or 0) >= 300_000,
        },
        {"url_name": "documents:dotation_bon_entree", "label": "BE", "icon": "📋"},
    ]

    detail_fields_sections = [
        {
            "titre": "Informations de l'entrée externe",
            "fields": [
                ("Code",            "code"),
                ("Source",          "source"),
                ("Date de réception", lambda o: o.received_date.strftime("%d/%m/%Y") if o.received_date else "—"),
                ("Dépôt",           "depot"),
                ("N° document",     "document_number"),
                ("Valeur totale",   lambda o: f"{int(o.total_value or 0):,} F CFA".replace(",", "\u202f"), "montant"),
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
            "titre": "Articles reçus",
            "qs": lambda obj: obj.lines.select_related("matiere").all(),
            "colonnes": [
                {"label": "Désignation",   "accessor": lambda l: l.matiere,                                                     "css": "td-primary"},
                {"label": "Quantité",      "accessor": "quantity",                                                                    "css": "td-num center"},
                {"label": "Prix unitaire", "accessor": lambda l: f"{int(l.unit_price or 0):,} F CFA".replace(",", "\u202f"),        "css": "td-num right"},
                {"label": "Total",         "accessor": lambda l: f"{int(l.total_line or 0):,} F CFA".replace(",", "\u202f"),        "css": "td-num right"},
                {"label": "Note",          "accessor": lambda l: l.note or "—",                                                      "css": ""},
            ],
            "total_value_fn": lambda obj, items: f"{int(obj.total_value or 0):,} F CFA".replace(",", "\u202f"),
            "total_label": "TOTAL VALEUR",
        }
    ]
