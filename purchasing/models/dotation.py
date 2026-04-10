# purchasing/models/dotation.py
"""
Dotation
========
Document unique remis à l'utilisateur (Bon de dotation).

Traitement en arrière-plan lors de la VALIDATION :
  - Lignes 2ème groupe (consommables)  → MouvementStock SORTIE  (sortie définitive)
  - Lignes 1er groupe (immobilisations) → MouvementStock AFFECTATION + FicheAffectation

Une dotation ne génère PAS de fiche d'inventaire contradictoire.
"""
from decimal import Decimal
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class Dotation(models.Model):

    # ------------------------------------------------------------------ #
    # Choix
    # ------------------------------------------------------------------ #
    class TypeDotation(models.TextChoices):
        PREMIER_GROUPE  = "1ER_GROUPE",  _("1er groupe — biens durables (affectation)")
        DEUXIEME_GROUPE = "2EME_GROUPE", _("2e groupe — consommables (sortie définitive)")
        MIXTE           = "MIXTE",       _("Mixte — 1er et 2e groupe")

    class Statut(models.TextChoices):
        BROUILLON = "BROUILLON", _("Brouillon")
        VALIDE    = "VALIDE",    _("Validée")
        ANNULE    = "ANNULE",    _("Annulée")

    # ------------------------------------------------------------------ #
    # Champs
    # ------------------------------------------------------------------ #
    code = models.CharField(
        _("Code"),
        max_length=60,
        unique=True,
        blank=True,
        default="",
        help_text=_("Généré automatiquement : DOT-AAAA-NNNNN"),
    )
    statut = models.CharField(
        _("Statut"),
        max_length=20,
        choices=Statut.choices,
        default=Statut.BROUILLON,
        db_index=True,
    )
    date = models.DateField(
        _("Date"),
        default=timezone.now,
    )
    depot = models.ForeignKey(
        "core.Depot",
        on_delete=models.PROTECT,
        related_name="dotations",
        verbose_name=_("Dépôt source"),
    )
    # type_dotation : auto-calculé depuis les lignes (ne pas saisir manuellement)
    type_dotation = models.CharField(
        _("Type de dotation"),
        max_length=20,
        choices=TypeDotation.choices,
        blank=True,
        default="",
        editable=False,
        help_text=_("Calculé automatiquement selon les groupes des matières distribuées."),
    )
    beneficiaire = models.CharField(
        _("Bénéficiaire (agent ou service)"),
        max_length=200,
    )
    service = models.ForeignKey(
        "core.Service",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dotations",
        verbose_name=_("Service bénéficiaire"),
    )
    document_number = models.CharField(
        _("N° document de référence"),
        max_length=80,
        blank=True,
        default="",
    )
    comment = models.TextField(
        _("Observations"),
        blank=True,
        default="",
    )
    total_value = models.DecimalField(
        _("Valeur totale"),
        max_digits=16,
        decimal_places=6,
        default=Decimal("0"),
        editable=False,
    )

    class Meta:
        ordering            = ["-date", "-id"]
        verbose_name        = _("Dotation")
        verbose_name_plural = _("Dotations")

    # ------------------------------------------------------------------ #
    # Représentation
    # ------------------------------------------------------------------ #
    def __str__(self):
        return self.code or f"Dotation #{self.pk}"

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _compute_type_dotation(self) -> str:
        """Détermine le type (1er groupe / 2e groupe / mixte) depuis les lignes."""
        types = set()
        for ligne in self.lignes.select_related("matiere").all():
            if ligne.matiere.type_matiere == "reutilisable":
                types.add(self.TypeDotation.PREMIER_GROUPE)
            else:
                types.add(self.TypeDotation.DEUXIEME_GROUPE)
        if len(types) == 2:
            return self.TypeDotation.MIXTE
        if types:
            return types.pop()
        return self.TypeDotation.DEUXIEME_GROUPE  # valeur par défaut si aucune ligne

    def recompute_totals(self):
        from django.db.models import Sum
        self.total_value  = self.lignes.aggregate(s=Sum("total_ligne"))["s"] or Decimal("0")
        self.type_dotation = self._compute_type_dotation()

    def generate_code(self) -> str:
        from datetime import date as _date
        d = self.date
        if isinstance(d, str):
            try:
                d = _date.fromisoformat(d)
            except ValueError:
                d = None
        year = d.year if d else timezone.now().year
        prefix = f"DOT-{year}-"
        last   = (
            Dotation.objects
            .filter(code__startswith=prefix)
            .order_by("-code")
            .values_list("code", flat=True)
            .first()
        )
        n = int(last.split("-")[-1]) + 1 if last else 1
        return f"{prefix}{n:05d}"

    # ------------------------------------------------------------------ #
    # Génération des documents (appelée lors de la validation)
    # ------------------------------------------------------------------ #
    @transaction.atomic
    def generer_documents(self):
        """
        Pour chaque ligne :
          - matiere.type_matiere == 'consommable'  → MouvementStock SORTIE
          - matiere.type_matiere == 'reutilisable' → MouvementStock AFFECTATION
                                                     + FicheAffectation
        Idempotente : ne recrée pas un document si la ligne en possède déjà un.
        """
        from datetime import datetime as _dt
        from inventory.models import MouvementStock, FicheAffectation

        if self.statut != self.Statut.VALIDE:
            raise ValidationError(_("La dotation doit être validée avant de générer les documents."))

        date_mvt = _dt.combine(self.date, _dt.min.time())

        for ligne in self.lignes.select_related("matiere").all():
            # Idempotence : on vérifie si un mouvement existe déjà pour cette ligne
            if MouvementStock.objects.filter(
                source_doc_type="LigneDotation",
                source_doc_id=ligne.pk,
            ).exists():
                continue

            is_immo = (ligne.matiere.type_matiere == "reutilisable")
            type_mvt = MouvementStock.Type.AFFECTATION if is_immo else MouvementStock.Type.SORTIE

            mvt = MouvementStock(
                matiere       = ligne.matiere,
                depot         = self.depot,
                type          = type_mvt,
                quantite      = ligne.quantity,
                cout_unitaire = ligne.unit_price if ligne.unit_price else None,
                date          = date_mvt,
                reference     = self.code,
                commentaire   = f"Dotation {self.code} — {self.beneficiaire}",
                source_doc_type = "LigneDotation",
                source_doc_id   = ligne.pk,
            )
            mvt.save()

            if is_immo:
                FicheAffectation.objects.create(
                    dotation         = self,
                    ligne_dotation   = ligne,
                    matiere          = ligne.matiere,
                    quantite         = ligne.quantity,
                    depot            = self.depot,
                    beneficiaire     = self.beneficiaire,
                    service          = self.service,
                    date_affectation = self.date,
                    mouvement_stock  = mvt,
                )

    # ------------------------------------------------------------------ #
    # Save
    # ------------------------------------------------------------------ #
    def save(self, *args, **kwargs):
        # Génère le code AVANT le premier INSERT pour éviter un conflit UNIQUE("")
        if not self.pk and not self.code:
            self.code = self.generate_code()
        super().save(*args, **kwargs)
        # Recalcul des totaux et du type depuis les lignes
        self.recompute_totals()
        super().save(update_fields=["total_value", "type_dotation", "code"])


class LigneDotation(models.Model):
    dotation   = models.ForeignKey(
        Dotation,
        on_delete=models.CASCADE,
        related_name="lignes",
    )
    matiere    = models.ForeignKey(
        "catalog.Matiere",
        on_delete=models.PROTECT,
        verbose_name=_("Matière"),
    )
    quantity   = models.DecimalField(
        _("Quantité"),
        max_digits=12,
        decimal_places=3,
    )
    unit_price = models.DecimalField(
        _("Prix unitaire"),
        max_digits=14,
        decimal_places=4,
        default=Decimal("0"),
    )
    total_ligne = models.DecimalField(
        _("Total ligne"),
        max_digits=16,
        decimal_places=4,
        default=Decimal("0"),
        editable=False,
    )
    note = models.CharField(
        _("Note"),
        max_length=200,
        blank=True,
        default="",
    )

    class Meta:
        verbose_name        = _("Ligne de dotation")
        verbose_name_plural = _("Lignes de dotation")

    def __str__(self):
        return f"{self.matiere} × {self.quantity}"

    def _groupe_display(self) -> str:
        if not self.matiere_id:
            return "—"
        return (
            _("1er groupe (immobilisation)")
            if self.matiere.type_matiere == "reutilisable"
            else _("2e groupe (consommable)")
        )

    def save(self, *args, **kwargs):
        self.total_ligne = (self.quantity or Decimal("0")) * (self.unit_price or Decimal("0"))
        super().save(*args, **kwargs)
