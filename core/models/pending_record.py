# core/models/pending_record.py
"""
Modèle tampon pour les ajouts soumis par les agents simples.
L'administrateur doit valider chaque enregistrement avant qu'il soit
effectivement sauvegardé dans la base de données.
"""
import json
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone


class PendingRecord(models.Model):
    class Status(models.TextChoices):
        PENDING  = 'pending',  'En attente'
        APPROVED = 'approved', 'Approuvé'
        REJECTED = 'rejected', 'Rejeté'

    submitted_by  = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, null=True,
        related_name='pending_submissions', verbose_name='Soumis par'
    )
    submitted_at  = models.DateTimeField('Soumis le', default=timezone.now)
    app_label     = models.CharField('Application', max_length=50)
    model_name    = models.CharField('Modèle', max_length=100)
    verbose_name  = models.CharField('Nom affiché', max_length=200, blank=True)
    data          = models.JSONField('Données (JSON)')
    status        = models.CharField('Statut', max_length=10, choices=Status.choices, default=Status.PENDING)
    reviewed_by   = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_pending', verbose_name='Révisé par'
    )
    reviewed_at   = models.DateTimeField('Révisé le', null=True, blank=True)
    admin_comment = models.TextField('Commentaire admin', blank=True)

    class Meta:
        verbose_name = 'Enregistrement en attente'
        verbose_name_plural = 'Enregistrements en attente'
        ordering = ['-submitted_at']

    def __str__(self):
        return f'[{self.get_status_display()}] {self.verbose_name} par {self.submitted_by} le {self.submitted_at:%d/%m/%Y %H:%M}'
