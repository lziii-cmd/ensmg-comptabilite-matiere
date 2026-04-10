# inventory/admin/inventaire_admin.py
from decimal import Decimal
from django.contrib import admin
from django.db.models import Sum
from django.apps import apps
from catalog.models import Matiere
from inventory.services.exercice import exercice_courant

class InventaireMatiere(Matiere):
    class Meta:
        proxy = True
        verbose_name = "Inventaire"
        verbose_name_plural = "Inventaire (matières)"

@admin.register(InventaireMatiere)
class InventaireMatiereAdmin(admin.ModelAdmin):
    list_display = ("designation", "stock_initial_total", "stock_actuel_total")
    list_per_page = 20
    search_fields = ("designation",)
    list_filter = ("est_stocke", "type_matiere")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(est_stocke=True, actif=True)

    def _calc_for_matiere(self, matiere):
        StockCourant = apps.get_model("inventory", "StockCourant")
        exo = exercice_courant()
        qs = StockCourant.objects.filter(exercice=exo, matiere=matiere)
        agg = qs.aggregate(q_init=Sum("stock_initial_qte"), q_cur=Sum("quantite"))
        return (agg["q_init"] or Decimal("0"), agg["q_cur"] or Decimal("0"))

    def stock_initial_total(self, obj):
        q_init, _ = self._calc_for_matiere(obj)
        return q_init
    stock_initial_total.short_description = "Stock initial"

    def stock_actuel_total(self, obj):
        _, q_cur = self._calc_for_matiere(obj)
        return q_cur
    stock_actuel_total.short_description = "Stock actuel"
