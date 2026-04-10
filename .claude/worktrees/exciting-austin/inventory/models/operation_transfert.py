# inventory/models/operation_transfert.py
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class OperationTransfert(models.Model):
    """
    Document métier : Affectation / Mutation interne
    => génère des mouvements MouvementStock de type TRANSFERT (1 par ligne)
    """

    class Motif(models.TextChoices):
        AFFECTATION = "AFFECTATION", _("Affectation à un bureau/service")
        MUTATION = "MUTATION", _("Mutation interne (changement d'emplacement)")
        RETOUR = "RETOUR", _("Retour vers magasin")
        AUTRE = "AUTRE", _("Autre")

    code = models.CharField(
        _("Code"),
        max_length=40,
        unique=True,
        blank=True,
        default="",
        help_text=_("Généré automatiquement, ex : TR-2025-00001"),
    )
    date_operation = models.DateField(_("Date"), default=timezone.now)

    depot_source = models.ForeignKey(
        "core.Depot",
        on_delete=models.PROTECT,
        related_name="operations_transfert_sortantes",
        verbose_name=_("Dépôt source"),
    )
    depot_destination = models.ForeignKey(
        "core.Depot",
        on_delete=models.PROTECT,
        related_name="operations_transfert_entrantes",
        verbose_name=_("Dépôt destination"),
    )

    motif = models.CharField(_("Motif"), max_length=20, choices=Motif.choices, default=Motif.AFFECTATION)
    description = models.TextField(_("Description / Observations"), blank=True, default="")

    total_valeur = models.DecimalField(_("Valeur totale"), max_digits=16, decimal_places=6, default=Decimal("0"))

    class Meta:
        verbose_name = _("Opération de transfert (Affectation/Mutation)")
        verbose_name_plural = _("Opérations de transfert (Affectations/Mutations)")
        ordering = ["-date_operation", "-id"]

    def __str__(self):
        base = self.code or f"Transfert #{self.pk or '—'}"
        return f"{base} — {self.depot_source} → {self.depot_destination}"

    def clean(self):
        errors = {}
        if not self.depot_source_id:
            errors["depot_source"] = _("Le dépôt source est obligatoire.")
        if not self.depot_destination_id:
            errors["depot_destination"] = _("Le dépôt destination est obligatoire.")
        if self.depot_source_id and self.depot_destination_id and self.depot_source_id == self.depot_destination_id:
            errors["depot_destination"] = _("Le dépôt destination doit être différent du dépôt source.")
        if errors:
            raise ValidationError(errors)

    def _generate_code(self) -> str:
        year = self.date_operation.year if self.date_operation else timezone.now().year
        prefix = f"TR-{year}-"
        last = (
            OperationTransfert.objects.filter(code__startswith=prefix)
            .order_by("-code")
            .values_list("code", flat=True)
            .first()
        )
        if last:
            try:
                n = int(last.split("-")[-1]) + 1
            except Exception:
                n = 1
        else:
            n = 1
        return f"{prefix}{n:05d}"

    def recompute_totaux(self):
        from django.db.models import Sum
        s = self.lignes.aggregate(s=Sum("total_ligne"))["s"] or Decimal("0")
        self.total_valeur = s

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # pk
        self.recompute_totaux()
        if not self.code:
            self.code = self._generate_code()
        super().save(update_fields=["total_valeur", "code"])


class LigneOperationTransfert(models.Model):
    operation = models.ForeignKey(
        OperationTransfert,
        on_delete=models.CASCADE,
        related_name="lignes",
        verbose_name=_("Opération"),
    )
    matiere = models.ForeignKey(
        "catalog.Matiere",
        on_delete=models.PROTECT,
        related_name="lignes_operation_transfert",
        verbose_name=_("Matière"),
    )
    quantite = models.DecimalField(_("Quantité"), max_digits=14, decimal_places=3, default=Decimal("0"))
    cout_unitaire = models.DecimalField(_("Coût unitaire (optionnel)"), max_digits=14, decimal_places=6, default=Decimal("0"))
    total_ligne = models.DecimalField(_("Total ligne"), max_digits=16, decimal_places=6, default=Decimal("0"))
    commentaire = models.CharField(_("Commentaire"), max_length=255, blank=True, default="")

    class Meta:
        verbose_name = _("Ligne opération transfert")
        verbose_name_plural = _("Lignes opération transfert")
        ordering = ["id"]

    def __str__(self):
        return f"{self.matiere} — {self.quantite}"

    def clean(self):
        errors = {}
        if not self.matiere_id:
            errors["matiere"] = _("Champ obligatoire.")
        if self.quantite is None or self.quantite <= 0:
            errors["quantite"] = _("La quantité doit être > 0.")
        if self.cout_unitaire is None or self.cout_unitaire < 0:
            errors["cout_unitaire"] = _("Le coût unitaire doit être ≥ 0.")
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        q = self.quantite or Decimal("0")
        cu = self.cout_unitaire or Decimal("0")
        self.total_ligne = (q * cu).quantize(Decimal("0.000001"))
        super().save(*args, **kwargs)
              
            