# catalog/models/matiere.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from core.models import Unite
from .categorie import Categorie
from .souscategorie import SousCategorie
from .compte import SousCompte

class Matiere(models.Model):
    class TypeMatiere(models.TextChoices):
        CONSOMMABLE = "consommable", _("Consommable")
        REUTILISABLE = "reutilisable", _("Réutilisable")

    code_court = models.CharField(
        _("Code matière (court)"), max_length=12, unique=True,
        help_text=_("Ex: ORD, BURE, LED20")
    )
    designation = models.CharField(_("Libellé / Désignation"), max_length=200)

    type_matiere = models.CharField(
        _("Type de matière"),
        max_length=20,
        choices=TypeMatiere.choices,
        default=TypeMatiere.REUTILISABLE,
        help_text=_("Permet de distinguer les biens durables des consommables.")
    )

    sous_categorie = models.ForeignKey(
        SousCategorie, on_delete=models.PROTECT, related_name="matieres",
        verbose_name=_("Sous-catégorie")
    )
    categorie = models.ForeignKey(
        Categorie, on_delete=models.PROTECT, related_name="matieres",
        verbose_name=_("Catégorie"), editable=False
    )

    sous_compte = models.ForeignKey(
        SousCompte, on_delete=models.PROTECT, related_name="matieres",
        verbose_name=_("Sous-compte"),
        help_text=_("Sous-compte d’imputation comptable de cette matière.")
    )

    unite = models.ForeignKey(
        Unite, on_delete=models.PROTECT, related_name="matieres",
        verbose_name=_("Unité"), null=True, blank=True
    )
    seuil_min = models.DecimalField(_("Seuil minimum"), max_digits=12, decimal_places=2, default=0, blank=True)
    actif = models.BooleanField(_("Actif"), default=True)

    # 👉 NOUVEAU : drapeau utilisé par la page “Stocks initiaux”
    est_stocke = models.BooleanField(
        _("Est stocké (initial saisi)"),
        default=False,
        help_text=_("Coché automatiquement après l’enregistrement du stock initial.")
    )

    class Meta:
        verbose_name = _("Matière")
        verbose_name_plural = _("Matières")
        ordering = ["code_court"]

    def clean(self):
        if self.sous_categorie and self.categorie_id and self.sous_categorie.categorie_id != self.categorie_id:
            raise ValidationError(_("La sous-catégorie sélectionnée n’appartient pas à la catégorie."))

    def save(self, *args, **kwargs):
        if self.sous_categorie and (not self.categorie_id or self.categorie_id != self.sous_categorie.categorie_id):
            self.categorie = self.sous_categorie.categorie
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code_court} — {self.designation}"
