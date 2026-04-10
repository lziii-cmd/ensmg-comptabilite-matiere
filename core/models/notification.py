# core/models/notification.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Notification(models.Model):
    class Type(models.TextChoices):
        STOCK_BAS = 'STOCK_BAS', 'Stock bas'
        VALIDATION = 'VALIDATION', 'Validation requise'
        REJET = 'REJET', 'Saisie rejetée'
        VALIDEE = 'VALIDEE', 'Saisie validée'
        INFO = 'INFO', 'Information'
    
    destinataire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type_notif = models.CharField(max_length=20, choices=Type.choices)
    titre = models.CharField(max_length=200)
    message = models.TextField()
    lue = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Link to related object (generic)
    app_label = models.CharField(max_length=50, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['destinataire', 'lue']),
        ]
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
    
    def __str__(self):
        return f"{self.get_type_notif_display()} - {self.titre} ({self.destinataire.username})"
    
    def mark_as_read(self):
        """Mark this notification as read."""
        self.lue = True
        self.save(update_fields=['lue'])
    
    @classmethod
    def create_or_get_today(cls, destinataire, type_notif, titre, message, app_label='', model_name='', object_id=None):
        """
        Create a notification if it doesn't already exist today for this user and type.
        Returns (notification, created) tuple.
        """
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)
        
        # Check if notification exists today
        existing = cls.objects.filter(
            destinataire=destinataire,
            type_notif=type_notif,
            created_at__gte=today,
            created_at__lt=tomorrow
        ).first()
        
        if existing:
            return existing, False
        
        # Create new notification
        notification = cls.objects.create(
            destinataire=destinataire,
            type_notif=type_notif,
            titre=titre,
            message=message,
            app_label=app_label,
            model_name=model_name,
            object_id=object_id
        )
        return notification, True
