# inventory/models/mouvement_stock.py
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class MouvementStock(models.Model):
    class Type(models.TextChoices):
        ENTREE      = "ENTREE",      "Entrée"
        SORTIE      = "SORTIE",      "Sortie"
        TRANSFERT   = "TRANSFERT",   "Transfert"
        AJUSTEMENT  = "AJUSTEMENT",  "Ajustement"
        AFFECTATION = "AFFECTATION", "Affectation (1er groupe)"

    # Typage & période
    type = models.CharField(max_length=12, choices=Type.choices)
    date = models.DateTimeField(default=timezone.now)
    exercice = models.ForeignKey(
        "core.Exercice",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="mouvements_stock",
        help_text="Renseigné automatiquement via la date si possible.",
    )

    # Matière & dépôts
    matiere = models.ForeignKey("catalog.Matiere", on_delete=models.PROTECT, related_name="mouvements_stock")
    depot = models.ForeignKey("core.Depot", on_delete=models.PROTECT, null=True, blank=True, related_name="mouvements_depot")
    source_depot = models.ForeignKey("core.Depot", on_delete=models.PROTECT, null=True, blank=True, related_name="mouvements_source")
    destination_depot = models.ForeignKey("core.Depot", on_delete=models.PROTECT, null=True, blank=True, related_name="mouvements_destination")

    # Quantités & coûts
    quantite = models.DecimalField(max_digits=14, decimal_places=3)
    cout_unitaire = models.DecimalField(max_digits=14, decimal_places=6, null=True, blank=True)
    cout_total = models.DecimalField(max_digits=16, decimal_places=6, editable=False)

    # Traçabilité & marquage
    is_stock_initial = models.BooleanField(
        default=False,
        help_text="Auto: la 1ère ENTREE (par exercice, matière, dépôt) est marquée stock initial.",
    )
    reference = models.CharField(max_length=80, blank=True, default="")
    commentaire = models.TextField(blank=True, default="")
    source_doc_type = models.CharField(max_length=60, blank=True, default="")
    source_doc_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["matiere", "depot"]),
            models.Index(fields=["source_doc_type", "source_doc_id"]),
            models.Index(fields=["exercice", "matiere", "depot"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["exercice", "matiere", "depot"],
                condition=models.Q(is_stock_initial=True, type="ENTREE"),
                name="uniq_stock_initial_par_exercice_matiere_depot",
            ),
            models.UniqueConstraint(
                fields=["source_doc_type", "source_doc_id"],
                name="uniq_mvt_stock_" \
                "source_doc",
            ),
        ]
        ordering = ["-date", "-id"]
        verbose_name = "Mouvement de stock"
        verbose_name_plural = "Mouvements de stock"

    # -------------------------
    # Validation métier
    # -------------------------
    def clean(self):
        # Règles dépôts selon type
        if self.type == self.Type.TRANSFERT:
            if not self.source_depot_id or not self.destination_depot_id:
                raise ValidationError("TRANSFERT : source_depot et destination_depot requis.")
            if self.depot_id:
                raise ValidationError("TRANSFERT : 'depot' doit être vide.")
            if self.source_depot_id == self.destination_depot_id:
                raise ValidationError("TRANSFERT : dépôts source et destination doivent être différents.")
        else:
            if not self.depot_id:
                raise ValidationError(f"{self.type} : le champ 'depot' est requis.")
            if self.source_depot_id or self.destination_depot_id:
                raise ValidationError(f"{self.type} : source/destination doivent être vides.")

        # Quantité & coût
        if self.quantite is None or self.quantite <= 0:
            raise ValidationError("La quantité doit être > 0.")
        if self.type in {self.Type.ENTREE, self.Type.AJUSTEMENT}:
            if self.cout_unitaire is None or self.cout_unitaire < 0:
                raise ValidationError(f"{self.type} : 'cout_unitaire' requis et ≥ 0.")

        # Stock initial = une entrée uniquement
        if self.is_stock_initial and self.type != self.Type.ENTREE:
            raise ValidationError("Un stock initial doit être de type ENTREE.")

        # Validation : stock suffisant avant toute sortie / affectation / transfert
        # (règle critique — jamais de stock négatif)
        if self.type in {self.Type.SORTIE, self.Type.AFFECTATION, self.Type.TRANSFERT}:
            from django.apps import apps as django_apps
            StockCourant = django_apps.get_model("inventory", "StockCourant")
            depot_a_verifier = (
                self.source_depot_id if self.type == self.Type.TRANSFERT else self.depot_id
            )
            if depot_a_verifier and self.matiere_id and self.exercice_id:
                courant = StockCourant.objects.filter(
                    exercice_id=self.exercice_id,
                    matiere_id=self.matiere_id,
                    depot_id=depot_a_verifier,
                ).first()
                qte_disponible = courant.quantite if courant else Decimal("0")
                # Exclure le mouvement lui-même en cas de modification
                if self.pk:
                    ancien = MouvementStock.objects.filter(pk=self.pk).values_list(
                        "quantite", flat=True
                    ).first()
                    if ancien and self.type not in {self.Type.TRANSFERT}:
                        qte_disponible += ancien
                if self.quantite > qte_disponible:
                    raise ValidationError(
                        f"Stock insuffisant : {qte_disponible} disponible(s), "
                        f"{self.quantite} demandée(s)."
                    )

    # -------------------------
    # Helpers internes
    # -------------------------
    def _ensure_exercice_from_date(self):
        if self.exercice_id is not None:
            return
        from django.apps import apps
        Exercice = apps.get_model("core", "Exercice")
        if Exercice and self.date:
            self.exercice = (
                Exercice.objects
                .filter(date_debut__lte=self.date, date_fin__gte=self.date)
                .order_by("-date_debut")
                .first()
            )

    def _apply_first_entry_as_initial_rule(self):
        """
        1ère ENTREE (par exercice, matière, dépôt) => is_stock_initial=True
        On se base sur l'historique des mouvements, pas sur StockCourant.
        """
        if self.type != self.Type.ENTREE:
            return
        if not self.exercice_id or not self.matiere_id or not self.depot_id:
            return

        qs = MouvementStock.objects.filter(
            type=self.Type.ENTREE,
            exercice_id=self.exercice_id,
            matiere_id=self.matiere_id,
            depot_id=self.depot_id,
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)

        self.is_stock_initial = (not qs.exists())

    # -------------------------
    # Save
    # -------------------------
    def save(self, *args, **kwargs):
        # 1) Exercice auto
        self._ensure_exercice_from_date()

        # 2) règle 1ère entrée => stock initial
        self._apply_first_entry_as_initial_rule()

        # 3) coût total — quantize à 6 décimales max (contrainte du champ)
        if self.cout_unitaire is not None:
            self.cout_total = (
                Decimal(self.cout_unitaire) * Decimal(self.quantite or 0)
            ).quantize(Decimal("0.000001"))
        else:
            self.cout_total = Decimal("0")

        # 4) valider
        self.full_clean()

        # 5) enregistrer — la mise à jour du StockCourant est gérée
        #    exclusivement par les signaux dans inventory/signals.py
        #    (post_save → recompute_stock_courant) pour éviter un double calcul.
        super().save(*args, **kwargs)

    def __str__(self):
        flag = " (initial)" if self.is_stock_initial else ""
        return f"[{self.type}{flag}] {self.matiere} q={self.quantite} ref={self.reference or '-'}"


# Proxies admin
class EntreeStock(MouvementStock):
    class Meta:
        proxy = True
        verbose_name = "Entrée de stock"
        verbose_name_plural = "Entrées de stock"


class SortieStock(MouvementStock):
    class Meta:
        proxy = True
        verbose_name = "Sortie de stock"
        verbose_name_plural = "Sorties de stock"


class StockInitial(MouvementStock):
    class Meta:
        proxy = True
        verbose_name = "Stock initial"
        verbose_name_plural = "Stocks initiaux"
