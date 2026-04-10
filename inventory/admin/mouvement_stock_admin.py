# inventory/admin/mouvement_stock_admin.py
from django.contrib import admin
from inventory.models import MouvementStock, EntreeStock, SortieStock
from core.admin.detail_view_mixin import DetailViewMixin

_MVT_SECTIONS = [
    {
        "titre": "Informations du mouvement",
        "fields": [
            ("Référence",      "reference"),
            ("Type",           lambda o: o.get_type_display() if hasattr(o, "get_type_display") else str(o.type)),
            ("Date",           lambda o: o.date.strftime("%d/%m/%Y") if o.date else "—"),
            ("Exercice",       "exercice"),
            ("Matière",        "matiere"),
            ("Dépôt",          "depot"),
            ("Dépôt source",   lambda o: str(o.source_depot) if o.source_depot else "—"),
            ("Dépôt dest.",    lambda o: str(o.destination_depot) if o.destination_depot else "—"),
            ("Quantité",       lambda o: str(int(o.quantite or 0))),
            ("Coût unitaire",  lambda o: f"{int(o.cout_unitaire or 0):,} F CFA".replace(",", "\u202f") if o.cout_unitaire else "—", "montant"),
            ("Coût total",     lambda o: f"{int(o.cout_total or 0):,} F CFA".replace(",", "\u202f"), "montant"),
            ("Stock initial",  lambda o: "✅ Oui" if o.is_stock_initial else "❌ Non"),
        ],
    },
    {
        "titre": "Commentaire",
        "obs_field": "commentaire",
        "fields": [],
    },
]

@admin.register(MouvementStock)
class MouvementStockAdmin(DetailViewMixin, admin.ModelAdmin):
    list_display = (
        "date", "type", "is_stock_initial", "exercice", "matiere",
        "depot", "source_depot", "destination_depot",
        "quantite", "cout_unitaire", "cout_total", "reference",
    )
    list_filter = ("type", "is_stock_initial", "exercice", "matiere",
                   "depot", "source_depot", "destination_depot")
    search_fields = ("reference", "commentaire", "source_doc_type", "source_doc_id")
    readonly_fields = ("cout_total",)
    ordering = ("-date", "-id")
    detail_fields_sections = _MVT_SECTIONS

@admin.register(EntreeStock)
class EntreeStockAdmin(MouvementStockAdmin):
    detail_fields_sections = _MVT_SECTIONS
    def get_queryset(self, request):
        return super().get_queryset(request).filter(type="ENTREE")

@admin.register(SortieStock)
class SortieStockAdmin(MouvementStockAdmin):
    detail_fields_sections = _MVT_SECTIONS
    def get_queryset(self, request):
        return super().get_queryset(request).filter(type="SORTIE")
