import re
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.core.validators import RegexValidator


def _slug_upper(s: str, max_len: int = 14) -> str:
    """
    "Amis de l'ENSMG" -> "AMISDELENSMG"
    """
    base = slugify(s or "", allow_unicode=False).replace("-", "").upper()
    base = re.sub(r"[^A-Z0-9]", "", base)
    return (base[:max_len] or "DONATEUR")


ident_validator = RegexValidator(r"^[A-Z0-9\-]+$", "Utilisez lettres majuscules, chiffres et tirets.")


class Donateur(models.Model):
    identifiant = models.CharField(
        max_length=40,  # ↑ augmenté (DON-NOM-2025-0001)
        unique=True,
        validators=[ident_validator],
        editable=False,
        blank=True,
        default="",
    )
    code_prefix = models.CharField(
        max_length=12,
        default="",
        blank=True,
        help_text="Préfixe utilisé dans le code des dons (ex: AMIS, ONG01).",
    )
    raison_sociale = models.CharField(max_length=200, help_text="Raison sociale / Nom du donateur")
    adresse = models.CharField(max_length=255, blank=True, default="")
    telephone = models.CharField(max_length=50, blank=True, default="")
    courriel = models.EmailField(blank=True, default="")
    remarque = models.TextField(blank=True, default="")
    actif = models.BooleanField(default=True)
    date_creation = models.DateField(default=timezone.now, editable=False)

    class Meta:
        verbose_name = "Donateur"
        verbose_name_plural = "Donateurs"
        ordering = ["raison_sociale"]

    def save(self, *args, **kwargs):
        if not self.identifiant:
            year = timezone.now().year
            slug = _slug_upper(self.raison_sociale, max_len=14)  # NOMDONATEUR
            base = f"DON-{slug}-{year}-"

            last = (
                Donateur.objects.filter(identifiant__startswith=base)
                .order_by("-identifiant")
                .values_list("identifiant", flat=True)
                .first()
            )
            n = (int(last.split("-")[-1]) + 1) if last else 1
            self.identifiant = f"{base}{n:04d}"  # ✅ 0001

        super().save(*args, **kwargs)

    def __str__(self):
        return self.raison_sociale
