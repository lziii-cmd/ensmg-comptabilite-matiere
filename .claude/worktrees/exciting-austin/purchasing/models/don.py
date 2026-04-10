# purchasing/models/don.py
from decimal import Decimal
from django.db import models, transaction
from django.utils import timezone

def _upload_piece_path(instance, filename):
    year = instance.date_don.year if instance.date_don else timezone.now().year
    code = instance.code or "DON-SANS-CODE"
    return f"donations/{year}/{code}_{filename}"

class Don(models.Model):
    donateur = models.ForeignKey("core.Donateur", on_delete=models.PROTECT, related_name="dons")
    date_don = models.DateField(default=timezone.now)
    depot = models.ForeignKey("core.Depot", on_delete=models.PROTECT, related_name="dons")
    commentaire = models.TextField(blank=True, default="")

    numero_piece = models.CharField(max_length=80, blank=True, default="")
    fichier_piece = models.FileField(upload_to=_upload_piece_path, null=True, blank=True)

    code = models.CharField(max_length=50, unique=True, blank=True, default="")
    total_valeur = models.DecimalField(max_digits=16, decimal_places=6, default=Decimal("0"))

    class Meta:
        ordering = ["-date_don", "-id"]
        verbose_name = "Don"
        verbose_name_plural = "Dons"

    def __str__(self):
        return self.code or f"Don #{self.pk or '—'}"

    def recompute_totaux(self):
        from django.db.models import Sum
        s = self.lignes.aggregate(s=Sum("total_ligne"))["s"] or Decimal("0")
        self.total_valeur = s

    def _generate_code(self) -> str:
        """
        Génère un code unique pour ce don, de la forme : DON-{PREFIX}-{YEAR}-{N:05d}
        Utilise select_for_update() pour éviter les collisions en cas d'accès concurrent.
        Doit être appelé à l'intérieur d'une transaction atomique.
        """
        year = self.date_don.year if self.date_don else timezone.now().year
        prefix = (self.donateur.code_prefix or "DONATEUR").upper()
        base = f"DON-{prefix}-{year}-"
        # Verrou row-level sur le dernier don ayant ce préfixe pour éviter les doublons
        last = (
            Don.objects
            .filter(code__startswith=base)
            .select_for_update()
            .order_by("-code")
            .values_list("code", flat=True)
            .first()
        )
        try:
            n = (int(last.split("-")[-1]) + 1) if last else 1
        except (ValueError, IndexError):
            n = 1
        return f"{base}{n:05d}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.recompute_totaux()
        if not self.code:
            with transaction.atomic():
                self.code = self._generate_code()
        super().save(update_fields=["total_valeur", "code"])


class LigneDon(models.Model):
    don = models.ForeignKey(Don, on_delete=models.CASCADE, related_name="lignes")
    matiere = models.ForeignKey("catalog.Matiere", on_delete=models.PROTECT, related_name="lignes_don")
    quantite = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))
    # valorisation facultative: 0 par défaut
    prix_unitaire = models.DecimalField(max_digits=14, decimal_places=6, default=Decimal("0"))
    total_ligne = models.DecimalField(max_digits=16, decimal_places=6, default=Decimal("0"))
    observation = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.matiere} • {self.quantite} × {self.prix_unitaire}"

    def save(self, *args, **kwargs):
        self.total_ligne = (self.quantite or 0) * (self.prix_unitaire or 0)
        super().save(*args, **kwargs)
