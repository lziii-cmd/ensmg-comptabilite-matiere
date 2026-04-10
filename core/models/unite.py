from django.db import models
from django.utils.translation import gettext_lazy as _


class Unite(models.Model):
    abreviation = models.CharField(_("Abréviation"), max_length=16, unique=True)
    libelle = models.CharField(_("Libellé"), max_length=64, unique=True)

    class Meta:
        verbose_name = _("Unité")
        verbose_name_plural = _("Unités")
        ordering = ["abreviation", "libelle"]

    def __str__(self):
        return f"{self.abreviation} — {self.libelle}"
