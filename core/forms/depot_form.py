from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class Depot(models.Model):
    class TypeLieu(models.TextChoices):
        DEPOT = "DEPOT", _("Dépôt / Magasin")
        BUREAU = "BUREAU", _("Bureau / Service")

    identifiant = models.CharField(_("Identifiant"), max_length=16, unique=True)
    nom = models.CharField(_("Nom"), max_length=128, unique=True)

    type_lieu = models.CharField(
        _("Type de lieu"),
        max_length=12,
        choices=TypeLieu.choices,
        default=TypeLieu.DEPOT,
    )

    # Spécifique BUREAU
    service = models.ForeignKey(
        "core.Service",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="bureaux",
        verbose_name=_("Service"),
    )
    responsable = models.CharField(_("Responsable"), max_length=128, blank=True, default="")

    localisation = models.CharField(_("Localisation"), max_length=128, blank=True)
    actif = models.BooleanField(_("Actif"), default=True)

    class Meta:
        verbose_name = _("Dépôt")
        verbose_name_plural = _("Dépôts")
        ordering = ["identifiant", "nom"]

    def __str__(self):
        suffix = "" if self.actif else " (inactif)"
        return f"{self.identifiant} — {self.nom}{suffix}"

    def clean(self):
        errors = {}

        if self.type_lieu == self.TypeLieu.BUREAU:
            if not self.service_id:
                errors["service"] = _("Le service est obligatoire pour un bureau.")
        else:
            # DEPOT : pas de service
            if self.service_id:
                errors["service"] = _("Un dépôt/magasin ne doit pas être rattaché à un service.")

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Responsable auto depuis le service si BUREAU
        if self.type_lieu == self.TypeLieu.BUREAU and self.service_id:
            self.responsable = self.service.responsable or ""
        if self.type_lieu != self.TypeLieu.BUREAU:
            # Nettoyage cohérent
            self.service = None
            self.responsable = ""
        super().save(*args, **kwargs)
