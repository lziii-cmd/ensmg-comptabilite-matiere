# audit/models/audit_entry.py
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class AuditEntry(models.Model):
    """
    Entrée du journal d'audit.

    Enregistre chaque création, modification, suppression, connexion et
    action métier qui survient dans l'application. Le champ `changes` stocke
    le diff champ-par-champ au format :
        { "champ": { "avant": valeur_avant, "apres": valeur_apres } }

    Ne jamais créer une AuditEntry manuellement depuis les vues :
    utiliser audit.services.recorder.record() ou record_action().
    """

    class Action(models.TextChoices):
        CREATION        = 'CREATION',       _('Création')
        MODIFICATION    = 'MODIFICATION',   _('Modification')
        SUPPRESSION     = 'SUPPRESSION',    _('Suppression')
        VALIDATION      = 'VALIDATION',     _('Validation')
        CONNEXION       = 'CONNEXION',      _('Connexion')
        DECONNEXION     = 'DECONNEXION',    _('Déconnexion')
        ECHEC_CONNEXION = 'ECHEC_CNX',      _('Échec de connexion')
        EXPORT          = 'EXPORT',         _('Export')
        IMPRESSION      = 'IMPRESSION',     _('Impression document')

    # ── Qui ──────────────────────────────────────────────────────────────────
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_entries',
        verbose_name=_('Utilisateur'),
    )
    user_repr = models.CharField(
        _('Nom (snapshot)'), max_length=150, blank=True,
        help_text=_(
            "Valeur figée au moment de l'action ; reste lisible même si "
            "le compte est supprimé ultérieurement."
        ),
    )
    ip_address = models.GenericIPAddressField(
        _('Adresse IP'), null=True, blank=True,
    )
    session_key = models.CharField(
        _('Clé de session'), max_length=40, blank=True,
    )

    # ── Quoi ─────────────────────────────────────────────────────────────────
    action = models.CharField(
        _('Action'), max_length=20, choices=Action.choices, db_index=True,
    )
    app_label = models.CharField(
        _('Application'), max_length=50, blank=True, db_index=True,
    )
    model_name = models.CharField(
        _('Modèle'), max_length=100, blank=True, db_index=True,
    )
    object_id = models.CharField(
        _('ID objet'), max_length=50, blank=True, db_index=True,
    )
    object_repr = models.CharField(
        _('Représentation'), max_length=300, blank=True,
        help_text=_("str(instance) au moment de l'action."),
    )

    # ── Diff ─────────────────────────────────────────────────────────────────
    changes = models.JSONField(
        _('Changements'), null=True, blank=True,
        help_text=_('{ "champ": { "avant": valeur, "apres": valeur } }'),
    )
    details = models.TextField(_('Détails'), blank=True)

    # ── Quand ─────────────────────────────────────────────────────────────────
    timestamp = models.DateTimeField(
        _('Horodatage'), auto_now_add=True, db_index=True,
    )

    class Meta:
        verbose_name        = _("Entrée d'audit")
        verbose_name_plural = _("Journal d'audit")
        ordering            = ['-timestamp']
        indexes = [
            models.Index(fields=['app_label', 'model_name'],  name='audit_app_model_idx'),
            models.Index(fields=['user', 'timestamp'],        name='audit_user_time_idx'),
            models.Index(fields=['action', 'timestamp'],      name='audit_action_time_idx'),
            models.Index(fields=['object_id', 'model_name'],  name='audit_obj_model_idx'),
        ]

    def __str__(self):
        who = self.user_repr or '(système)'
        ts  = self.timestamp.strftime('%d/%m/%Y %H:%M') if self.timestamp else '?'
        return f"[{self.get_action_display()}] {self.object_repr[:60]} — {who} le {ts}"
