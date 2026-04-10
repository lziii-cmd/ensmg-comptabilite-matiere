# core/models/fournisseur.py
from django.db import models
from django.utils.text import slugify

def _gen_prefix_from_name(name: str) -> str:
    """
    Génère un prefix lisible à partir de la raison sociale.
    - Uppercase
    - Garde uniquement lettres/chiffres
    - Coupe à 12 chars max
    """
    if not name:
        return "FOU"
    # slugify → "ma-societe-2000"; on retire les tirets puis on garde A-Z0-9
    base = slugify(name, allow_unicode=False).replace("-", "").upper()
    base = "".join(ch for ch in base if ch.isalnum())
    return (base[:12] or "FOU")

class Fournisseur(models.Model):
    # Identifiant fonctionnel interne, généré par le système (ex: FRS-00001)
    identifiant = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        blank=True,
        help_text="Généré automatiquement par le système."
    )

    # Raison sociale / nom
    raison_sociale = models.CharField(
        max_length=255,
        help_text="Nom légal de l'entreprise ou nom du fournisseur."
    )

    # Coordonnées
    adresse = models.CharField(max_length=255, blank=True, default="")
    numero = models.CharField(max_length=30, blank=True, default="", help_text="Numéro de téléphone.")
    courriel = models.EmailField(blank=True, default="")

    # NINEA (souvent unique)
    ninea = models.CharField(max_length=50, null=True, blank=True, unique=True)

    # Préfixe utilisé pour la numérotation des documents (ACH/RET)
    code_prefix = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Préfixe utilisé dans les codes documents (ex: ELECTRO). Sera auto-généré si vide."
    )

    class Meta:
        verbose_name = "Fournisseur"
        verbose_name_plural = "Fournisseurs"
        ordering = ["raison_sociale"]

    def __str__(self):
        return f"{self.raison_sociale} ({self.identifiant or '—'})"

    def save(self, *args, **kwargs):
        creating = self.pk is None
        # 1er save pour obtenir un PK si création
        super().save(*args, **kwargs)

        updates = []

        # Génération identifiant si absent (ex: FRS-00001)
        if not self.identifiant:
            self.identifiant = f"FRS-{self.pk:05d}"
            updates.append("identifiant")

        # Génération code_prefix si vide → dérivé de la raison sociale
        if not self.code_prefix:
            self.code_prefix = _gen_prefix_from_name(self.raison_sociale)
            updates.append("code_prefix")

        if updates:
            super().save(update_fields=updates)
