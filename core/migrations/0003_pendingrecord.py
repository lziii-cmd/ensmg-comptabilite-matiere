# Generated migration for PendingRecord model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0002_externalsource'),
    ]

    operations = [
        migrations.CreateModel(
            name='PendingRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('submitted_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Soumis le')),
                ('app_label', models.CharField(max_length=50, verbose_name='Application')),
                ('model_name', models.CharField(max_length=100, verbose_name='Modele')),
                ('verbose_name', models.CharField(blank=True, max_length=200, verbose_name='Nom affiche')),
                ('data', models.JSONField(verbose_name='Donnees (JSON)')),
                ('status', models.CharField(choices=[('pending', 'En attente'), ('approved', 'Approuve'), ('rejected', 'Rejete')], default='pending', max_length=10, verbose_name='Statut')),
                ('reviewed_at', models.DateTimeField(blank=True, null=True, verbose_name='Revise le')),
                ('admin_comment', models.TextField(blank=True, verbose_name='Commentaire admin')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_pending', to=settings.AUTH_USER_MODEL, verbose_name='Revise par')),
                ('submitted_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pending_submissions', to=settings.AUTH_USER_MODEL, verbose_name='Soumis par')),
            ],
            options={
                'verbose_name': 'Enregistrement en attente',
                'verbose_name_plural': 'Enregistrements en attente',
                'ordering': ['-submitted_at'],
            },
        ),
    ]
