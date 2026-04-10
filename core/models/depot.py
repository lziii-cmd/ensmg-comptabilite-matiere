from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class Depot(models.Model):
    """
    Depot = lieu.
    - DEPOT : magasin/stock physique
    - BUREAU : lieu d'affectation interne (service obligatoire)
    """

    class TypeLieu(models.TextChoices):
        DEPOT = "DEPOT", _("Dépôt / Magasin")
        BUREAU = "BUREAU", _("Bureau / Service")

    identifiant = models.CharField(_("Identifiant"), max_length=16, unique=True)  # ex: "111"
    nom = models.CharField(_("Nom"), max_length=128, unique=True)

    # ✅ Un SEUL champ de type (on supprime is_bureau)
    type_lieu = models.CharField(
        _("Type de lieu"),
        max_length=10,
        choices=TypeLieu.choices,
        default=TypeLieu.DEPOT,
    )

    # Bureau uniquement
    service = models.ForeignKey(
        "core.Service",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="lieux",
        verbose_name=_("Service"),
    )
    responsable = models.CharField(_("Responsable"), max_length=128, blank=True, default="")

    # Optionnel
    localisation = models.CharField(_("Localisation"), max_length=128, blank=True, default="")
    actif = models.BooleanField(_("Actif"), default=True)

    class Meta:
        verbose_name = _("Dépôt / Bureau")
        verbose_name_plural = _("Dépôts / Bureaux")
        ordering = ["identifiant", "nom"]

    def __str__(self):
        suffix = "" if self.actif else " (inactif)"
        return f"{self.identifiant} — {self.nom} [{self.type_lieu}]{suffix}"

    def clean(self):
        errors = {}

        if self.type_lieu == self.TypeLieu.BUREAU:
            if not self.service_id:
                errors["service"] = _("Le service est obligatoire pour un bureau.")
        else:
            # DEPOT : service interdit
            if self.service_id:
                errors["service"] = _("Ne doit pas être renseigné pour un dépôt.")

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Synchroniser responsable depuis service (si bureau)
        if self.type_lieu == self.TypeLieu.BUREAU and self.service_id:
            self.responsable = self.service.responsable or ""
        else:
            # DEPOT : on nettoie
            self.service = None
            self.responsable = ""
        super().save(*args, **kwargs)
