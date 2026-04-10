from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Les signaux d'audit sont gérés par AuditConfig.ready() dans audit/apps.py
        pass
