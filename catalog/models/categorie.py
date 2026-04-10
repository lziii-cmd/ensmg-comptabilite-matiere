from django.db import models
from django.utils.translation import gettext_lazy as _
import re

def _auto_code_from_label(label: str, max_len: int = 8) -> str:
    # MOB, INF, ENT… (initiales)
    words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+", label or "")
    initials = "".join(w[0] for w in words).upper()
    base = (initials or (label or "")[:max_len]).upper()[:max_len]
    return base

class Categorie(models.Model):
    code = models.CharField(_("Code"), max_length=16, unique=True, help_text=_("Ex: MOB, INF…"), blank=True)
    libelle = models.CharField(_("Libellé"), max_length=100, unique=True)
    description = models.TextField(_("Description"), blank=True)
    actif = models.BooleanField(_("Actif"), default=True)

    class Meta:
        verbose_name = _("Catégorie")
        verbose_name_plural = _("Catégories")
        ordering = ["code"]

    def save(self, *args, **kwargs):
        if not self.code:
            base = _auto_code_from_label(self.libelle, 8)
            candidate, i = base, 1
            while Categorie.objects.filter(code=candidate).exclude(pk=self.pk).exists():
                i += 1 
                candidate = f"{base}{i}"
            self.code = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} — {self.libelle}"
