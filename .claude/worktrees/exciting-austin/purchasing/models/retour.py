# purchasing/models/retour.py
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from core.models import Fournisseur, FournisseurSequence

class RetourFournisseur(models.Model):
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.PROTECT, related_name="retours")
    date_retour = models.DateField(default=timezone.now)
    code = models.CharField(max_length=40, unique=True, blank=True, default="")  # généré auto
    depot = models.ForeignKey("core.Depot", on_delete=models.PROTECT, null=True, blank=True, related_name="retours")
    commentaire = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-date_retour", "-id"]
        verbose_name = "Retour fournisseur"
        verbose_name_plural = "Retours fournisseurs"

    def __str__(self):
        return self.code or f"Retour #{self.pk or '—'}"

    def clean(self):
        if not self.fournisseur_id:
            raise ValidationError({"fournisseur": "Fournisseur obligatoire."})

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if not self.code:
            annee = (self.date_retour.year if self.date_retour else timezone.now().year)
            self.code = FournisseurSequence.generate_code(self.fournisseur, annee, type_doc="RET")
            super().save(update_fields=["code"])
