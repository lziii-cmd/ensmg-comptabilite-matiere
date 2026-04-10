from django.utils.translation import gettext_lazy as _
from .external_stock_entry import ExternalStockEntry


class LegsEntry(ExternalStockEntry):
    """
    Proxy model pour les entrées de type Legs (legs/bequests).
    Partage la même table qu'ExternalStockEntry, filtré par source__source_type = LEGS.
    """

    class Meta:
        proxy = True
        verbose_name = _("Legs")
        verbose_name_plural = _("Legs")
