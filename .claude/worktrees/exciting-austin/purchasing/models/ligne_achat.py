# purchasing/models/ligne_achat.py
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError

class LigneAchat(models.Model):
    achat = models.ForeignKey("purchasing.Achat", on_delete=models.CASCADE, related_name="lignes")
    matiere = models.ForeignKey("catalog.Matiere", on_delete=models.PROTECT, related_name="lignes_achat")
    quantite = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))
    prix_unitaire = models.DecimalField(max_digits=14, decimal_places=6, default=Decimal("0"))
    total_ligne_ht = models.DecimalField(max_digits=16, decimal_places=6, default=Decimal("0"))
    appreciation = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["id"]

    def clean(self):
        errors = {}
        if not self.matiere_id:
            errors["matiere"] = "Ce champ est obligatoire."
        if self.quantite is None or self.quantite <= 0:
            errors["quantite"] = "La quantité doit être > 0."
        if self.prix_unitaire is None or self.prix_unitaire < 0:
            errors["prix_unitaire"] = "Le prix unitaire doit être ≥ 0."
        if errors:
            raise ValidationError(errors)

    def _compute_total(self) -> Decimal:
        q = self.quantite or Decimal("0")
        pu = self.prix_unitaire or Decimal("0")
        return (q * pu).quantize(Decimal("0.000001"))

    def save(self, *args, **kwargs):
        self.total_ligne_ht = self._compute_total()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.matiere} • {self.quantite} × {self.prix_unitaire}"
