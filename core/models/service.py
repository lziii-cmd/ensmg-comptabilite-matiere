from django.db import models
from django.utils.translation import gettext_lazy as _


class Service(models.Model):
    code = models.CharField(_("Code"), max_length=16, unique=True)
    libelle = models.CharField(_("Libellé"), max_length=128, unique=True)
    responsable = models.CharField(_("Responsable"), max_length=128)
    actif = models.BooleanField(_("Actif"), default=True)

    class Meta:
        verbose_name = _("Service")
        verbose_name_plural = _("Services")
        ordering = ["code", "libelle"]

    def __str__(self):
        suffix = "" if self.actif else " (inactif)"
        return f"{self.code} — {self.libelle}{suffix}"
