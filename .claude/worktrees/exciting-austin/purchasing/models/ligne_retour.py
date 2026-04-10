# purchasing/models/ligne_retour.py
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError

class LigneRetour(models.Model):
    """
    Ligne de retour fournisseur. Deux modes possibles :
    - retour ciblé : lien direct vers une LigneAchat (valorisation = PU d'origine)
    - retour global : pas de lien, on utilisera le CUMP courant (valorisé côté service/stock)
    """
    retour = models.ForeignKey("purchasing.RetourFournisseur", on_delete=models.CASCADE, related_name="lignes")
    matiere = models.ForeignKey("catalog.Matiere", on_delete=models.PROTECT, related_name="lignes_retour")
    quantite = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))
    ligne_achat_origine = models.ForeignKey(
        "purchasing.LigneAchat",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="Optionnel : si renseigné, la valorisation prend le PU de l'achat d'origine."
    )

    class Meta:
        ordering = ["id"]

    def clean(self):
        errors = {}
        if not self.matiere_id:
            errors["matiere"] = "Ce champ est obligatoire."
        if self.quantite is None or self.quantite <= 0:
            errors["quantite"] = "La quantité doit être > 0."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"Retour {self.retour_id} • {self.matiere} • -{self.quantite}"
