# core/models/exercice.py
from datetime import date
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils.translation import gettext_lazy as _


class Exercice(models.Model):
    class Statut(models.TextChoices):
        OUVERT = "OUVERT", _("Ouvert")
        CLOS = "CLOS", _("Clos")

    annee = models.PositiveIntegerField(_("Année"), unique=True)
    # bornes auto-dérivées de l'année
    date_debut = models.DateField(_("Date de début"), editable=False)
    date_fin = models.DateField(_("Date de fin"), editable=False)
    statut = models.CharField(_("Statut"), max_length=10, choices=Statut.choices, default=Statut.OUVERT)
    code = models.CharField(_("Code"), max_length=16, unique=True, editable=False)

    class Meta:
        verbose_name = _("Exercice")
        verbose_name_plural = _("Exercices")
        ordering = ["-annee"]
        constraints = [
            # si tu veux autoriser plusieurs "courants" en même temps, enlève/assouplis cette contrainte
            UniqueConstraint(
                fields=["statut"],
                condition=Q(statut="OUVERT"),
                name="unique_exercice_ouvert",
            )
        ]

    def save(self, *args, **kwargs):
        # bornes et code générés à partir de l'année
        if self.annee:
            self.date_debut = date(self.annee, 1, 1)
            self.date_fin = date(self.annee, 12, 31)
        if not self.code and self.annee:
            self.code = f"EX-{self.annee}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} ({self.statut})"

    @property
    def est_courant(self) -> bool:
        today = date.today()
        return bool(self.date_debut and self.date_fin and self.date_debut <= today <= self.date_fin)

    # ======= les 2 méthodes attendues par tes templates/context =======

    @classmethod
    def courants(cls):
        """
        Par défaut : exercices marqués 'OUVERT'.
        Si tu préfères te baser sur la date du jour, remplace par:
            return cls.objects.filter(date_debut__lte=today, date_fin__gte=today)
        """
        return cls.objects.filter(statut=cls.Statut.OUVERT).order_by("-annee")

    @classmethod
    def courant_label(cls):
        qs = cls.courants()
        if not qs.exists():
            return "Aucun exercice actif"
        return ", ".join(str(e.annee) for e in qs)
