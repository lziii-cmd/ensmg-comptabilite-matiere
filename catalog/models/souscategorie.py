from django.db import models
from django.utils.translation import gettext_lazy as _
import re
from .categorie import Categorie

def _auto_code_from_label(label: str, max_len: int = 12) -> str:
    words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+", label or "")
    initials = "".join(w[0] for w in words).upper()
    base = (initials or (label or "")[:max_len]).upper()[:max_len]


    
    return base

class SousCategorie(models.Model):
    code = models.CharField(_("Code"), max_length=20, unique=True, help_text=_("Ex: BURE, ORDI…"), blank=True)
    libelle = models.CharField(_("Libellé"), max_length=100)
    categorie = models.ForeignKey(Categorie, on_delete=models.PROTECT, related_name="sous_categories", verbose_name=_("Catégorie"))
    description = models.TextField(_("Description"), blank=True)  # ← NEW
    actif = models.BooleanField(_("Actif"), default=True)

    class Meta:
        verbose_name = _("Sous-catégorie")
        verbose_name_plural = _("Sous-catégories")
        ordering = ["categorie__code", "code"]
        constraints = [
            models.UniqueConstraint(fields=["categorie", "libelle"], name="uniq_souscat_categorie_libelle"),
        ]

    def save(self, *args, **kwargs):
        if not self.code:
            base = _auto_code_from_label(self.libelle, 12)
            candidate, i = base, 1
            while SousCategorie.objects.filter(code=candidate).exclude(pk=self.pk).exists():
                i += 1
                candidate = f"{base}{i}"
            self.code = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.categorie.code}/{self.code} — {self.libelle}"
