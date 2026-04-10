from django.db import models
from django.utils.translation import gettext_lazy as _


class ExternalSource(models.Model):
    class SourceType(models.TextChoices):
        MINISTRY = "MINISTRY", _("Ministère")
        SCHOOL = "SCHOOL", _("École / Université")
        PARTNER = "PARTNER", _("Partenaire")
        LEGS = "LEGS", _("Legs")
        DOTATION = "DOTATION", _("Dotation")
        OTHER = "OTHER", _("Autre")

    source_type = models.CharField(max_length=16, choices=SourceType.choices)
    name = models.CharField(max_length=160)
    acronym = models.CharField(max_length=30, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Structure source")
        verbose_name_plural = _("Structures sources")
        ordering = ["source_type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_type", "name"],
                name="uniq_external_source_type_name"
            )
        ]

    def __str__(self):
        if self.acronym:
            return f"{self.get_source_type_display()} — {self.acronym}"
        return f"{self.get_source_type_display()} — {self.name}"

    @property
    def code_prefix(self) -> str:
        """
        Used for document codes (MEN, UCAD, UNESCO, etc.)
        """
        if self.acronym:
            return self.acronym.upper()
        return (self.name.upper().replace(" ", "")[:10] or "SRC")
