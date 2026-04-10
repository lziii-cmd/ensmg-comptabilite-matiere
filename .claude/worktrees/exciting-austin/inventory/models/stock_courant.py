# inventory/models/stock_courant.py
from decimal import Decimal
from django.db import models

class StockCourant(models.Model):
    """ Vue matérialisée en table, mise à jour après chaque mouvement. """
    exercice = models.ForeignKey("core.Exercice", on_delete=models.PROTECT, null=True, blank=True, related_name="stocks_courants")
    matiere = models.ForeignKey("catalog.Matiere", on_delete=models.PROTECT, related_name="stocks_courants")
    depot = models.ForeignKey("core.Depot", on_delete=models.PROTECT, related_name="stocks_courants")

    # États
    quantite = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))
    cump = models.DecimalField(max_digits=14, decimal_places=6, default=Decimal("0"))
    # Mémo stock initial (facilite les rapports)
    stock_initial_qte = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))
    stock_initial_cu = models.DecimalField(max_digits=14, decimal_places=6, default=Decimal("0"))

    class Meta:
        unique_together = (("exercice", "matiere", "depot"),)
        indexes = [
            models.Index(fields=["exercice", "matiere", "depot"]),
            models.Index(fields=["matiere", "depot"]),
        ]
        verbose_name = "État de stock"
        verbose_name_plural = "États de stock"

    @property
    def valeur(self):
        return (self.quantite or 0) * (self.cump or 0)

    def __str__(self):
        return f"{self.matiere} @ {self.depot} [{self.exercice_id or '—'}] q={self.quantite} CUMP={self.cump}"
