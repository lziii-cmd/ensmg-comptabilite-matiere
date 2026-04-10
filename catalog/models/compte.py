# catalog/models/compte.py
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

def _zp(n: int, width: int = 2) -> str:
    return str(n).zfill(width)

class ComptePrincipal(models.Model):
    class Groupe(models.TextChoices):
        G1 = "G1", _("1er groupe (codes 10, 11, 12, …)")
        G2 = "G2", _("2e groupe (codes 20, 21, 22, …)")

    pin = models.PositiveSmallIntegerField(_("PIN principal"), unique=True, editable=False)
    code = models.CharField(_("Code"), max_length=2, unique=True, editable=False)  # "10", "11", ..., "20", "21", ...
    libelle = models.CharField(_("Libellé"), max_length=200)
    groupe = models.CharField(_("Groupe"), max_length=2, choices=Groupe.choices)
    description = models.TextField(_("Description"), blank=True)
    actif = models.BooleanField(_("Actif"), default=True)

    class Meta:
        verbose_name = _("Compte principal")
        verbose_name_plural = _("Comptes principaux")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.libelle}"

    def _next_code_for_group(self) -> str:
        """Retourne le prochain code à 2 chiffres dans la ‘dizaine’ du groupe (10..19 ou 20..29)."""
        decade = 1 if self.groupe == self.Groupe.G1 else 2
        base = decade * 10  # 10 ou 20
        # chercher le plus grand code existant dans la même dizaine
        last = (
            ComptePrincipal.objects
            .filter(code__regex=rf'^{decade}\d$')
            .order_by('-code')
            .values_list('code', flat=True)
            .first()
        )
        if last:
            n = int(last) + 1
        else:
            n = base
        # borne simple (optionnelle) si tu veux rester strictement sur 10..19 / 20..29
        if n >= (base + 10):
            # tu peux lever une ValidationError si tu veux empêcher d’aller au-delà
            # from django.core.exceptions import ValidationError
            # raise ValidationError(_("Plage de codes épuisée pour ce groupe."))
            # sinon on laisse passer (mais code > 29 ne rentrera pas dans 2 caractères)
            pass
        return _zp(n, 2)

    def save(self, *args, **kwargs):
        if not self.groupe:
            raise ValueError("Le groupe est obligatoire (G1 ou G2).")

        if self.pk is None:
            with transaction.atomic():
                # PIN séquentiel global (compat)
                last_pin = ComptePrincipal.objects.order_by("-pin").values_list("pin", flat=True).first()
                self.pin = (last_pin + 1) if last_pin else 1
                # Code séquentiel dans la dizaine du groupe (10.., 20..)
                self.code = self._next_code_for_group()
        super().save(*args, **kwargs)


class CompteDivisionnaire(models.Model):
    compte_principal = models.ForeignKey(
        ComptePrincipal, on_delete=models.PROTECT, related_name="divisionnaires", verbose_name=_("Compte principal")
    )
    pin = models.PositiveSmallIntegerField(_("PIN divisionnaire (local au principal)"), editable=False)
    code = models.CharField(_("Code"), max_length=5, unique=True, editable=False)  # "10.01"
    libelle = models.CharField(_("Libellé"), max_length=200)
    description = models.TextField(_("Description"), blank=True)
    actif = models.BooleanField(_("Actif"), default=True)

    class Meta:
        verbose_name = _("Compte divisionnaire")
        verbose_name_plural = _("Comptes divisionnaires")
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["compte_principal", "pin"], name="uniq_divisionnaire_pin_par_principal"),
        ]

    def __str__(self):
        return f"{self.code} — {self.libelle}"

    def save(self, *args, **kwargs):
        if self.pk is None:
            with transaction.atomic():
                last = (
                    CompteDivisionnaire.objects
                    .filter(compte_principal=self.compte_principal)
                    .order_by("-pin")
                    .first()
                )
                self.pin = (last.pin + 1) if last else 1
                self.code = f"{self.compte_principal.code}.{_zp(self.pin, 2)}"
        super().save(*args, **kwargs)


class SousCompte(models.Model):
    compte_divisionnaire = models.ForeignKey(
        CompteDivisionnaire, on_delete=models.PROTECT, related_name="sous_comptes", verbose_name=_("Compte divisionnaire")
    )
    pin = models.PositiveSmallIntegerField(_("PIN sous-compte (local au divisionnaire)"), editable=False)
    code = models.CharField(_("Code"), max_length=8, unique=True, editable=False)  # "10.01.01"
    libelle = models.CharField(_("Libellé"), max_length=200)
    description = models.TextField(_("Description"), blank=True)
    actif = models.BooleanField(_("Actif"), default=True)

    class Meta:
        verbose_name = _("Sous-compte")
        verbose_name_plural = _("Sous-comptes")
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["compte_divisionnaire", "pin"], name="uniq_souscompte_pin_par_divisionnaire"),
        ]

    def __str__(self):
        return f"{self.code} — {self.libelle}"

    def save(self, *args, **kwargs):
        if self.pk is None:
            with transaction.atomic():
                last = (
                    SousCompte.objects
                    .filter(compte_divisionnaire=self.compte_divisionnaire)
                    .order_by("-pin")
                    .first()
                )
                self.pin = (last.pin + 1) if last else 1
                self.code = f"{self.compte_divisionnaire.code}.{_zp(self.pin, 2)}"
        super().save(*args, **kwargs)
