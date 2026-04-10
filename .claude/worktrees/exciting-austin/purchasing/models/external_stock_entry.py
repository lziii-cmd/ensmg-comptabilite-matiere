from decimal import Decimal
from django.db import models
from django.utils import timezone


def upload_external_entry_file(instance, filename):
    year = instance.received_date.year if instance.received_date else timezone.now().year
    code = instance.code or "EXT-UNSET"
    return f"external_entries/{year}/{code}_{filename}"


class ExternalStockEntry(models.Model):
    source = models.ForeignKey(
        "core.ExternalSource",
        on_delete=models.PROTECT,
        related_name="stock_entries"
    )
    received_date = models.DateField(default=timezone.now)
    depot = models.ForeignKey(
        "core.Depot",
        on_delete=models.PROTECT,
        related_name="external_entries"
    )

    document_number = models.CharField(max_length=80, blank=True, default="")
    document_file = models.FileField(upload_to=upload_external_entry_file, null=True, blank=True)

    comment = models.TextField(blank=True, default="")
    code = models.CharField(max_length=60, unique=True, blank=True, default="")
    total_value = models.DecimalField(max_digits=16, decimal_places=6, default=Decimal("0"))

    class Meta:
        ordering = ["-received_date", "-id"]
        verbose_name = "External stock entry"
        verbose_name_plural = "External stock entries"

    def __str__(self):
        return self.code or f"External entry #{self.pk}"

    def recompute_totals(self):
        from django.db.models import Sum
        self.total_value = self.lines.aggregate(
            s=Sum("total_line")
        )["s"] or Decimal("0")

    def generate_code(self):
        year = self.received_date.year
        prefix = self.source.code_prefix
        base = f"EXT-{prefix}-{year}-"
        last = (
            ExternalStockEntry.objects
            .filter(code__startswith=base)
            .order_by("-code")
            .values_list("code", flat=True)
            .first()
        )
        n = int(last.split("-")[-1]) + 1 if last else 1
        return f"{base}{n:05d}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.recompute_totals()
        if not self.code:
            self.code = self.generate_code()
        super().save(update_fields=["total_value", "code"])
