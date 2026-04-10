# purchasing/apps.py
from django.apps import AppConfig
  
class PurchasingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "purchasing"
    verbose_name = "Achats"

    def ready(self):
        # Petits signaux sûrs pour garder les totaux à jour si les lignes changent ailleurs que via l’admin
        from . import signals_lines  # noqa: F401