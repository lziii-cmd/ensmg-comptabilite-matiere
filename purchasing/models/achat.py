# purchasing/models/achat.py
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from core.models import Fournisseur, FournisseurSequence

TVA_TAUX = Decimal("0.18")

# >>> IMPORTANT : la fonction doit être définie avant la classe Achat
def _upload_facture_path(instance, filename):
    """
    Exemple: invoices/2025/ACH-ELECTRO-2025-00042_facture.pdf
    On utilise code si déjà généré, sinon un placeholder.
    """
    year = instance.date_achat.year if instance.date_achat else timezone.now().year
    code = instance.code or "ACH-SANS-CODE"
    return f"invoices/{year}/{code}_{filename}"

class Achat(models.Model):
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.PROTECT, related_name="achats")
    date_achat = models.DateField(default=timezone.now)

    # Champs facture saisis au formulaire
    numero_facture = models.CharField(max_length=80, blank=True, default="")
    fichier_facture = models.FileField(upload_to=_upload_facture_path, blank=True, null=True)

    # Généré automatiquement
    code = models.CharField(max_length=40, unique=True, blank=True, default="")
    tva_active = models.BooleanField(default=False)

    # Totaux calculés (cachés dans le formulaire)
    total_ht = models.DecimalField(max_digits=16, decimal_places=6, default=Decimal("0"))
    total_tva = models.DecimalField(max_digits=16, decimal_places=6, default=Decimal("0"))
    total_ttc = models.DecimalField(max_digits=16, decimal_places=6, default=Decimal("0"))

    depot = models.ForeignKey("core.Depot", on_delete=models.PROTECT, null=True, blank=True, related_name="achats")
    commentaire = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-date_achat", "-id"]

    def __str__(self):
        return self.code or f"Achat #{self.pk or '—'}"

    def recompute_totaux(self):
        from django.db.models import Sum
        s = self.lignes.aggregate(s=Sum("total_ligne_ht"))["s"] or Decimal("0")
        self.total_ht = s
        self.total_tva = (s * TVA_TAUX).quantize(Decimal("0.000001")) if self.tva_active else Decimal("0")
        self.total_ttc = (self.total_ht + self.total_tva).quantize(Decimal("0.000001"))

    def clean(self):
        if not self.fournisseur_id:
            raise ValidationError({"fournisseur": "Fournisseur obligatoire."})

    def save(self, *args, **kwargs):
        creating = self.pk is None
        # 1er save pour avoir un PK
        super().save(*args, **kwargs)
        # Recalcul + génération du code si manquant
        self.recompute_totaux()
        if not self.code:
            annee = self.date_achat.year if self.date_achat else timezone.now().year
            self.code = FournisseurSequence.generate_code(self.fournisseur, annee, type_doc="ACH")
        super().save(update_fields=["total_ht", "total_tva", "total_ttc", "code"])
