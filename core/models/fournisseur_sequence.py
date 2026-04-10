# core/models/fournisseur_sequence.py
from django.db import models, transaction

class FournisseurSequence(models.Model):
    """
    Séquence par (fournisseur, année, type_doc) pour générer les codes:
      ACH-<PREFIX>-<ANNEE>-<SEQ_5>
      RET-<PREFIX>-<ANNEE>-<SEQ_5>
    """
    TYPE_CHOICES = (("ACH", "Achat"), ("RET", "Retour fournisseur"))

    fournisseur = models.ForeignKey("core.Fournisseur", on_delete=models.CASCADE, related_name="sequences")
    annee = models.PositiveIntegerField()
    type_doc = models.CharField(max_length=3, choices=TYPE_CHOICES) 
    next_seq = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = (("fournisseur", "annee", "type_doc"),)
        indexes = [models.Index(fields=["fournisseur", "annee", "type_doc"])]
        verbose_name = "Séquence fournisseur"
        verbose_name_plural = "Séquences fournisseurs"

    def __str__(self):
        return f"{self.fournisseur} · {self.type_doc}-{self.annee} · next={self.next_seq}"

    @classmethod
    @transaction.atomic
    def generate_code(cls, fournisseur, annee: int, type_doc: str) -> str:
        seq_obj, _ = cls.objects.select_for_update().get_or_create(
            fournisseur=fournisseur, annee=annee, type_doc=type_doc, defaults={"next_seq": 1}
        )
        current = seq_obj.next_seq
        seq_obj.next_seq = current + 1
        seq_obj.save(update_fields=["next_seq"])

        prefix = (getattr(fournisseur, "code_prefix", "") or "FOU").upper()
        return f"{type_doc}-{prefix}-{annee}-{current:05d}"
