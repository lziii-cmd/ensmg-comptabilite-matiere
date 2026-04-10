from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError


class ExternalStockEntryLine(models.Model):
    entry = models.ForeignKey(
        "purchasing.ExternalStockEntry",
        on_delete=models.CASCADE,
        related_name="lines"
    )
    matiere = models.ForeignKey(
        "catalog.Matiere",
        on_delete=models.PROTECT,
        related_name="external_entry_lines"
    )

    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit_price = models.DecimalField(max_digits=14, decimal_places=6, default=Decimal("0"))
    total_line = models.DecimalField(max_digits=16, decimal_places=6, default=Decimal("0"))
    note = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["id"]

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")

    def save(self, *args, **kwargs):
        self.total_line = (self.quantity or 0) * (self.unit_price or 0)
        super().save(*args, **kwargs)

        # 🔁 Stock synchronization
        from django.apps import apps
        Movement = apps.get_model("inventory", "MouvementStock")

        Movement.objects.update_or_create(
            source_doc_type="purchasing.ExternalStockEntryLine",
            source_doc_id=self.id,
            defaults=dict(
                type=Movement.Type.ENTREE,
                date=self.entry.received_date,
                matiere=self.matiere,
                depot=self.entry.depot,
                quantite=self.quantity,
                cout_unitaire=self.unit_price,
                reference=self.entry.code,
                commentaire=f"External entry from {self.entry.source}",
            )
        )

    def delete(self, *args, **kwargs):
        from django.apps import apps
        Movement = apps.get_model("inventory", "MouvementStock")
        Movement.objects.filter(
            source_doc_type="purchasing.ExternalStockEntryLine",
            source_doc_id=self.id
        ).delete()
        super().delete(*args, **kwargs)
