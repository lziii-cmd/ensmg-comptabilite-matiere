# purchasing/models/retour_pret.py
from decimal import Decimal
from django.db import models
from django.utils import timezone

def _code_retour_for(service_code: str, d):
    year = d.year if d else timezone.now().year
    prefix = (service_code or "SERV").upper()
    return f"RET-{prefix}-{year}-"

# ✅ Réintroduction pour compatibilité avec la migration 0003
def _upload_piece_path(instance, filename):
    """
    Chemin d’upload compatible avec la migration existante.
    Exemple: retours/2025/RET-SERV-2025-00001_facture.pdf
    Si le code n’est pas encore généré lors du premier save: on met un placeholder.
    Le fichier pourra être réuploadé une fois le code généré si besoin.
    """
    year = instance.date_retour.year if instance.date_retour else timezone.now().year
    code = instance.code or "RET-SANS-CODE"
    return f"retours/{year}/{code}_{filename}"

class RetourPret(models.Model):
    """ Retour lié à un prêt existant. Service & dépôt hérités du prêt. """
    pret = models.ForeignKey("purchasing.Pret", on_delete=models.PROTECT, related_name="retours")
    date_retour = models.DateField(default=timezone.now)
    commentaire = models.TextField(blank=True, default="")
    numero_piece = models.CharField(max_length=80, blank=True, default="")
    # ✅ IMPORTANT: garder le même nom de fonction pour 'upload_to'
    fichier_piece = models.FileField(upload_to=_upload_piece_path, null=True, blank=True)
    code = models.CharField(max_length=50, unique=True, blank=True, default="")
    total_qte = models.DecimalField(max_digits=16, decimal_places=3, default=Decimal("0"))

    class Meta:
        ordering = ["-date_retour", "-id"]
        verbose_name = "Retour de prêt (entrée)"
        verbose_name_plural = "Retours de prêt (entrées)"

    def __str__(self):
        return self.code or f"Retour #{self.pk or '—'}"

    @property
    def service(self):
        return getattr(self.pret, "service", None)

    @property
    def depot(self):
        return getattr(self.pret, "depot", None)

    def _generate_code(self):
        base = _code_retour_for(getattr(self.pret.service, "code", ""), self.date_retour)
        last = (
            RetourPret.objects.filter(code__startswith=base)
            .order_by("-code")
            .values_list("code", flat=True)
            .first()
        )
        n = (int(last.split("-")[-1]) + 1) if last else 1
        return f"{base}{n:05d}"

    def recompute_total(self):
        from django.db.models import Sum
        self.total_qte = self.lignes_retour_pret.aggregate(s=Sum("quantite"))["s"] or Decimal("0")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.recompute_total()
        if not self.code:
            self.code = self._generate_code()
        super().save(update_fields=["total_qte", "code"])


class LigneRetourPret(models.Model):
    """
    ⚠️ AUCUN prix unitaire saisi ici.
    La valorisation ENTREE se fera au CUMP courant en back-office.
    """
    retour = models.ForeignKey(RetourPret, on_delete=models.CASCADE, related_name="lignes_retour_pret")
    matiere = models.ForeignKey("catalog.Matiere", on_delete=models.PROTECT, related_name="lignes_retour_pret")
    quantite = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))
    observation = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.matiere} • {self.quantite}"

    def clean(self):
        """
        - matière doit exister dans les lignes du prêt,
        - quantité ≤ solde prêté non encore retourné.
        """
        from django.core.exceptions import ValidationError
        from django.db.models import Sum

        if (self.quantite or Decimal("0")) <= 0:
            raise ValidationError({"quantite": "La quantité doit être > 0."})

        pret = getattr(self.retour, "pret", None)
        pret_id = getattr(pret, "id", None)
        if not pret_id:
            raise ValidationError("Retour sans prêt lié.")

        # Quantité prêtée pour cette matière
        q_pret = (
            pret.lignes.filter(matiere_id=self.matiere_id)
            .aggregate(s=Sum("quantite"))["s"] or Decimal("0")
        )
        if q_pret <= 0:
            raise ValidationError({"matiere": "Cette matière n’a pas été prêtée dans ce prêt."})

        # Déjà retourné (autres lignes de retours de ce prêt)
        deja = (
            LigneRetourPret.objects
            .filter(retour__pret_id=pret_id, matiere_id=self.matiere_id)
            .exclude(id=self.id)
            .aggregate(s=Sum("quantite"))["s"] or Decimal("0")
        )
        solde = q_pret - deja
        if self.quantite > solde:
            raise ValidationError({"quantite": f"Quantité > solde ({solde}) pour cette matière."})
