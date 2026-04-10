# inventory/models/operation_sortie.py

from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
    

def _upload_document_path(instance, filename: str) -> str:
    """
    Exemple: sorties/2025/SO-2025-00001_pv.pdf
    On utilise le code si disponible, sinon un placeholder.
    """
    year = instance.date_sortie.year if instance.date_sortie else timezone.now().year
    code = instance.code or "SORTIE-SANS-CODE"
    return f"sorties/{year}/{code}_{filename}"


class OperationSortie(models.Model):
    """
    Opérations de SORTIE DEFINITIVE impactant l'existant (stocks globaux).

    Types couverts :
    - réforme / destruction
    - pertes / vols / destructions accidentelles / déficit d’inventaire
    - consommation matières 2e groupe
    - sortie justifiée par certificat administratif
    - opérations de fin de gestion
    """

    class TypeSortie(models.TextChoices):
        REFORME_DESTRUCTION = "REFORME_DESTRUCTION", _(
            "Réforme / destruction définitive"
        )
        PERTE_VOL_DEFICIT = "PERTE_VOL_DEFICIT", _(
            "Pertes, vols, destructions accidentelles, déficit d’inventaire"
        )
        CONSOMMATION_2E_GROUPE = "CONSOMMATION_2E_GROUPE", _(
            "Consommation de matières du 2ᵉ groupe"
        )
        CERTIFICAT_ADMIN = "CERTIFICAT_ADMIN", _(
            "Sortie justifiée par certificat administratif"
        )
        FIN_GESTION = "FIN_GESTION", _(
            "Opérations de fin de gestion"
        )
        VENTE = "VENTE", _(
            "Vente"
        )

    code = models.CharField(
        _("Code"),
        max_length=40,
        unique=True,
        blank=True,
        default="",
        help_text=_("Généré automatiquement, ex : SO-2025-00001"),
    )

    type_sortie = models.CharField(
        _("Type de sortie"),
        max_length=40,
        choices=TypeSortie.choices,
        default=TypeSortie.REFORME_DESTRUCTION,
    )

    date_sortie = models.DateField(
        _("Date de sortie"),
        default=timezone.now,
    )

    depot = models.ForeignKey(
        "core.Depot",
        on_delete=models.PROTECT,
        related_name="operations_sortie",
        verbose_name=_("Dépôt"),
    )

    motif_principal = models.CharField( 
        _("Motif principal / libellé interne"),
        max_length=200,
        blank=True, 
        default="",
        help_text=_("Ex : Casse importante, réforme matériel obsolète, etc."),
    )

    commentaire = models.TextField(
        _("Description / Observations"),
        blank=True,
        default="",
    )

    # Justificatif (PV, certificat, etc.)
    numero_document = models.CharField(
        _("Numéro de document"),
        max_length=80,
        blank=True,
        default="",
        help_text=_("Numéro de PV / certificat / document justificatif, si applicable."),
    )
    fichier_document = models.FileField(
        _("Pièce justificative"),
        upload_to=_upload_document_path,
        blank=True,
        null=True,
        help_text=_("Scan du PV, certificat ou autre pièce justificative."),
    )

    # Total de valorisation (somme des lignes)
    total_valeur = models.DecimalField(
        _("Valeur totale"),
        max_digits=16,
        decimal_places=6,
        default=Decimal("0"),
    )

    class Meta:
        verbose_name = _("Opération de sortie de stock (définitive)")
        verbose_name_plural = _("Opérations de sortie de stock (définitives)")
        ordering = ["-date_sortie", "-id"]

    def __str__(self):
        base = self.code or f"Sortie #{self.pk or '—'}"
        return f"{base} — {self.get_type_sortie_display()}"

    # -------------------------------
    # Génération du code
    # -------------------------------
    def _generate_code(self) -> str:
        """
        Génère un code unique du type :
        SO-AAAA-00001

        Regroupé par année de la date de sortie.
        """
        year = self.date_sortie.year if self.date_sortie else timezone.now().year
        prefix = f"SO-{year}-"

        last = (
            OperationSortie.objects.filter(code__startswith=prefix)
            .order_by("-code")
            .values_list("code", flat=True)
            .first()
        )
        if last:
            # last = "SO-2025-00012" -> 12
            try:
                n = int(last.split("-")[-1]) + 1
            except Exception:
                n = 1
        else:
            n = 1
        return f"{prefix}{n:05d}"

    # -------------------------------
    # Totaux
    # -------------------------------
    def recompute_totaux(self):
        from django.db.models import Sum

        s = self.lignes.aggregate(s=Sum("total_ligne"))["s"] or Decimal("0")
        self.total_valeur = s

    # -------------------------------
    # Validation
    # -------------------------------
    def clean(self):
        errors = {}
        if not self.depot_id:
            errors["depot"] = _("Le dépôt est obligatoire.")
        if errors:
            raise ValidationError(errors)

    # -------------------------------
    # Save
    # -------------------------------
    def save(self, *args, **kwargs):
        creating = self.pk is None
        # 1er save pour avoir un PK
        super().save(*args, **kwargs)

        # Recalcul des totaux
        self.recompute_totaux()

        # Génération du code si nécessaire
        if not self.code:
            self.code = self._generate_code()

        super().save(update_fields=["total_valeur", "code"])


class LigneOperationSortie(models.Model):
    """
    Détail des matières sorties définitivement.
    """

    operation = models.ForeignKey(
        OperationSortie,
        on_delete=models.CASCADE,
        related_name="lignes",
        verbose_name=_("Opération de sortie"),
    )

    matiere = models.ForeignKey(
        "catalog.Matiere",
        on_delete=models.PROTECT,
        related_name="lignes_operation_sortie",
        verbose_name=_("Matière"),
    )

    quantite = models.DecimalField(
        _("Quantité à sortir"),
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
    )

    prix_unitaire = models.DecimalField(
        _("Prix unitaire (valorisation)"),
        max_digits=14,
        decimal_places=6,
        default=Decimal("0"),
        help_text=_("Utilisé pour valoriser la sortie (optionnel)."),
    )

    total_ligne = models.DecimalField(
        _("Total ligne"),
        max_digits=16,
        decimal_places=6,
        default=Decimal("0"),
    )

    commentaire = models.CharField(
        _("Commentaire"),
        max_length=255,
        blank=True,
        default="",
    )

    class Meta:
        verbose_name = _("Ligne d'opération de sortie de stock")
        verbose_name_plural = _("Lignes d'opération de sortie de stock")
        ordering = ["id"]

    def __str__(self):
        return f"{self.matiere} — {self.quantite}"

    # -------------------------------
    # Validation
    # -------------------------------
    def clean(self):
        errors = {}
        if not self.matiere_id:
            errors["matiere"] = _("Ce champ est obligatoire.")
        if self.quantite is None or self.quantite <= 0:
            errors["quantite"] = _("La quantité doit être > 0.")
        if self.prix_unitaire is None or self.prix_unitaire < 0:
            errors["prix_unitaire"] = _("Le prix unitaire doit être ≥ 0.")
        if errors:
            raise ValidationError(errors)

    # -------------------------------
    # Total ligne
    # -------------------------------
    def _compute_total(self) -> Decimal:
        q = self.quantite or Decimal("0")
        pu = self.prix_unitaire or Decimal("0")
        return (q * pu).quantize(Decimal("0.000001"))

    def save(self, *args, **kwargs):
        self.total_ligne = self._compute_total()
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Proxy models (pages dédiées dans l'admin)
# ─────────────────────────────────────────────────────────────────────────────

class _SortieCertificatAdminManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(type_sortie=OperationSortie.TypeSortie.CERTIFICAT_ADMIN)


class SortieCertificatAdmin(OperationSortie):
    """
    Proxy — Sorties par certificat administratif (Art. 17b, 18c).
    Partage la même table qu'OperationSortie, filtrée sur CERTIFICAT_ADMIN.
    """
    objects = _SortieCertificatAdminManager()

    class Meta:
        proxy = True
        verbose_name = "Sortie par certificat administratif"
        verbose_name_plural = "Sorties par certificat administratif"


class _SortieFinGestionManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(type_sortie=OperationSortie.TypeSortie.FIN_GESTION)


class SortieFinGestion(OperationSortie):
    """
    Proxy — Opérations de fin de gestion.
    Partage la même table qu'OperationSortie, filtrée sur FIN_GESTION.
    """
    objects = _SortieFinGestionManager()

    class Meta:
        proxy = True
        verbose_name = "Opération de fin de gestion"
        verbose_name_plural = "Opérations de fin de gestion"
