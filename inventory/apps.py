# inventory/apps.py
from django.apps import AppConfig

class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventory"
    verbose_name = "Inventaire"

    def ready(self):
        from . import signals  # noqa
