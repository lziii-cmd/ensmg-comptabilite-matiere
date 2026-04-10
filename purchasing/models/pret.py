from decimal import Decimal
from django.db import models
from django.utils import timezone

def _code_pret_for(service_code: str, d):
    year = d.year if d else timezone.now().year
    prefix = (service_code or "SERV").upper()
    return f"PRET-{prefix}-{year}-"

class Pret(models.Model):
    service = models.ForeignKey("core.Service", on_delete=models.PROTECT, related_name="prets")
    date_pret = models.DateField(default=timezone.now)
    depot = models.ForeignKey("core.Depot", on_delete=models.PROTECT, related_name="prets")
    commentaire = models.TextField(blank=True, default="")
    code = models.CharField(max_length=50, unique=True, blank=True, default="")
    est_clos = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date_pret", "-id"]
        verbose_name = "Prêt (sortie)"
        verbose_name_plural = "Prêts (sorties)"

    def __str__(self):
        return self.code or f"Prêt #{self.pk or '—'}"

    def _generate_code(self):
        base = _code_pret_for(getattr(self.service, "code", ""), self.date_pret)
        last = Pret.objects.filter(code__startswith=base).order_by("-code").values_list("code", flat=True).first()
        n = (int(last.split("-")[-1]) + 1) if last else 1
        return f"{base}{n:05d}"

    def recompute_closure(self):
        from decimal import Decimal
        from django.db.models import Sum
        mat_qte = self.lignes.values("matiere_id").annotate(qte=Sum("quantite"))
        if not mat_qte:
            self.est_clos = False
            return
        ret = (
            self.retours.values("lignes_retour_pret__matiere_id")
            .annotate(qr=Sum("lignes_retour_pret__quantite"))
        )
        ret_map = {r["lignes_retour_pret__matiere_id"]: (r["qr"] or Decimal("0")) for r in ret}
        ouvert = any((row["qte"] or Decimal("0")) - ret_map.get(row["matiere_id"], Decimal("0")) > 0 for row in mat_qte)
        self.est_clos = not ouvert

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.code:
            self.code = self._generate_code()
            super().save(update_fields=["code"])


class LignePret(models.Model):
    """ ⚠️ AUCUN prix unitaire pour un prêt. """
    pret = models.ForeignKey(Pret, on_delete=models.CASCADE, related_name="lignes")
    matiere = models.ForeignKey("catalog.Matiere", on_delete=models.PROTECT, related_name="lignes_pret")
    quantite = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))
    observation = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.matiere} • {self.quantite}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if (self.quantite or Decimal("0")) <= 0:
            raise ValidationError({"quantite": "La quantité doit être > 0."})
