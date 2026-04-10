from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from django.db.models import F
from django.core.exceptions import ValidationError
from core.constants import PIECE_TYPE_CHOICES  # 👈


class Sequence(models.Model):
    """
    Compteurs par type de pièce et par exercice.
    Ex: type_piece="ACH", exercice=2025, dernier_numero=42 -> prochain code "ACH-2025-0043"
    """
    type_piece = models.CharField(_("Type de pièce"), max_length=16, choices=PIECE_TYPE_CHOICES)  # 👈 choices
    exercice = models.ForeignKey("core.Exercice", on_delete=models.CASCADE, related_name="sequences", verbose_name=_("Exercice"))
    dernier_numero = models.PositiveIntegerField(_("Dernier numéro"), default=0)

    class Meta:
        verbose_name = _("Séquence")
        verbose_name_plural = _("Séquences")
        unique_together = [("type_piece", "exercice")]
        indexes = [
            models.Index(fields=["type_piece", "exercice"]),
        ]

    def __str__(self):
        return f"{self.type_piece}-{self.exercice.annee} ({self.dernier_numero})"

    @classmethod
    def next_code(cls, type_piece: str, exercice, padding: int = 4) -> str:
        """
        Retourne un code unique atomiquement, format: TYPE-ANNEE-####

        Usage:
            code = Sequence.next_code("ACH", exercice_ouvert)
        """
        if not type_piece:
            raise ValidationError(_("Le type de pièce est requis."))

        with transaction.atomic():
            # Verrouille/initialise la ligne de séquence
            seq, created = cls.objects.select_for_update().get_or_create(
                type_piece=type_piece,
                exercice=exercice,
                defaults={"dernier_numero": 0},
            )
            # Incrémente en BDD de façon sûre
            seq.dernier_numero = F("dernier_numero") + 1
            seq.save(update_fields=["dernier_numero"])
            seq.refresh_from_db(fields=["dernier_numero"])

            numero = str(seq.dernier_numero).zfill(padding)
            return f"{type_piece}-{exercice.annee}-{numero}"
