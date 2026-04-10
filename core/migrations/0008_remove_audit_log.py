# core/migrations/0008_remove_audit_log.py
#
# Supprime le modèle AuditLog de l'app core.
# Le journal d'audit est désormais géré par audit.models.AuditEntry.
#
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_alter_externalsource_source_type'),
    ]

    operations = [
        migrations.DeleteModel(
            name='AuditLog',
        ),
    ]
