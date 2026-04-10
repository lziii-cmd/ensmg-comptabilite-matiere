# inventory/models/fiche_affectation.py
"""
FicheAffectation
================
Générée automatiquement lors de la validation d'une dotation de matières
du **1er groupe** (biens durables / immobilisations).

Rôle : tracer la responsabilité de garde d'un bien sorti du dépôt et affecté
à un agent.  Le bien reste dans le patrimoine de l'institution ; seule la
responsabilité change.

Cycle de vie :
  AFFECTE  → bien remis à l'agent, hors dépôt
  REINTEGRE → bien rendu au dépôt (retour d'affectation)
  REFORME   → bien réformé en fin de vie
"""
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class FicheAffectation(models.Model):

    class Statut(models.TextChoices):
        AFFECTE   = "AFFECTE",   _("Affecté")
        REINTEGRE = "REINTEGRE", _("Réintégré au dépôt")
        REFORME   = "REFORME",   _("Réformé")

    # ------------------------------------------------------------------ #
    # Identification
    # ------------------------------------------------------------------ #
    code = models.CharField(
        _("Code"),
        max_length=30,
        unique=True,
        blank=True,
        default="",
        help_text=_("Généré automatiquement : FA-AAAA-NNNNN"),
    )

    # ------------------------------------------------------------------ #
    # Source : dotation ayant déclenché l'affectation
    # ------------------------------------------------------------------ #
    dotation = models.ForeignKey(
        "purchasing.Dotation",
        on_delete=models.PROTECT,
        related_name="fiches_affectation",
        verbose_name=_("Dotation source"),
    )
    ligne_dotation = models.OneToOneField(
        "purchasing.LigneDotation",
        on_delete=models.PROTECT,
        related_name="fiche_affectation",
        verbose_name=_("Ligne de dotation"),
        null=True,
        blank=True,
    )

    # ------------------------------------------------------------------ #
    # Bien affecté
    # ------------------------------------------------------------------ #
    matiere = models.ForeignKey(
        "catalog.Matiere",
        on_delete=models.PROTECT,
        related_name="fiches_affectation",
        verbose_name=_("Matière"),
    )
    quantite = models.DecimalField(
        _("Quantité"),
        max_digits=12,
        decimal_places=3,
        default=Decimal("1"),
    )
    depot = models.ForeignKey(
        "core.Depot",
        on_delete=models.PROTECT,
        related_name="fiches_affectation",
        verbose_name=_("Dépôt source"),
    )

    # ------------------------------------------------------------------ #
    # Bénéficiaire
    # ------------------------------------------------------------------ #
    beneficiaire = models.CharField(
        _("Agent bénéficiaire"),
        max_length=200,
    )
    service = models.ForeignKey(
        "core.Service",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fiches_affectation",
        verbose_name=_("Service bénéficiaire"),
    )

    # ------------------------------------------------------------------ #
    # Dates & statut
    # ------------------------------------------------------------------ #
    date_affectation = models.DateField(
        _("Date d'affectation"),
        default=timezone.now,
    )
    statut = models.CharField(
        _("Statut"),
        max_length=20,
        choices=Statut.choices,
        default=Statut.AFFECTE,
    )

    # ------------------------------------------------------------------ #
    # Lien vers le mouvement de stock généré
    # ------------------------------------------------------------------ #
    mouvement_stock = models.OneToOneField(
        "inventory.MouvementStock",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="fiche_affectation",
        verbose_name=_("Mouvement de stock"),
    )

    # ------------------------------------------------------------------ #
    # Divers
    # ------------------------------------------------------------------ #
    observations = models.TextField(_("Observations"), blank=True, default="")

    class Meta:
        verbose_name        = _("Fiche d'affectation")
        verbose_name_plural = _("Fiches d'affectation")
        ordering            = ["-date_affectation", "-id"]

    # ------------------------------------------------------------------ #
    # Code auto
    # ------------------------------------------------------------------ #
    def _generate_code(self) -> str:
        year   = self.date_affectation.year if self.date_affectation else timezone.now().year
        prefix = f"FA-{year}-"
        last   = (
            FicheAffectation.objects
            .filter(code__startswith=prefix)
            .order_by("-code")
            .values_list("code", flat=True)
            .first()
        )
        n = int(last.split("-")[-1]) + 1 if last else 1
        return f"{prefix}{n:05d}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.code:
            self.code = self._generate_code()
            super().save(update_fields=["code"])

    def __str__(self):
        return f"{self.code or f'FA #{self.pk}'} — {self.matiere} → {self.beneficiaire}"
