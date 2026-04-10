from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'audit'
    verbose_name = "Audit & Traçabilité"

    def ready(self):
        """
        Connecte tous les signaux d'audit au démarrage de l'application.
        Cette méthode est appelée une seule fois par Django après que toutes
        les apps sont chargées, garantissant que les modèles cibles existent.
        """
        from audit import signals as audit_signals  # noqa: F401
        audit_signals.connect_all()
