# audit/services/recorder.py
"""
Service centralisé d'enregistrement du journal d'audit.

Fonctions publiques :
    record(instance, action, changes=None, details='')
        → Enregistre une CREATION / MODIFICATION / SUPPRESSION sur un objet Django.
          Capture automatiquement l'utilisateur et l'IP via le middleware.

    record_action(request_or_user, action, obj, details='')
        → Enregistre une action métier manuelle (validation, impression, export…).

    record_login(user, request)  /  record_logout(user, request)
        → Connexion / déconnexion.

    record_login_failed(request, username)
        → Tentative de connexion échouée.

    take_snapshot(instance) → dict
        → Capture tous les champs traçables d'une instance.

    compute_diff(before, after) → dict | None
        → Compare deux snapshots et retourne les changements.
"""
import logging
from decimal import Decimal
from datetime import date, datetime

from django.db import models as django_models

from audit.middleware import get_current_request, get_client_ip

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Sérialisation et snapshot
# ═══════════════════════════════════════════════════════════════════════════

def _serialize(value):
    """Convertit les types non-JSON-sérialisables en représentation lisible."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _should_track(field) -> bool:
    """
    Retourne True si ce champ doit être inclus dans les snapshots.
    On exclut : clé primaire, auto_now/auto_now_add, fichiers, binaires.
    """
    if not hasattr(field, 'attname'):
        return False
    if getattr(field, 'primary_key', False):
        return False
    if getattr(field, 'auto_now', False) or getattr(field, 'auto_now_add', False):
        return False
    if isinstance(field, (django_models.FileField, django_models.BinaryField)):
        return False
    return True


def take_snapshot(instance) -> dict:
    """
    Retourne un dict { attname: valeur_sérialisée } pour tous les champs
    traçables de l'instance.

    Pour les ForeignKey, enrichit la valeur avec la repr de la relation :
        { "fournisseur_id": { "id": 42, "repr": "ELECTRO SARL" } }
    """
    snapshot = {}
    for field in instance._meta.get_fields():
        if not _should_track(field):
            continue
        try:
            raw = getattr(instance, field.attname)
            if isinstance(field, django_models.ForeignKey) and raw is not None:
                related = getattr(instance, field.name, None)
                value = {
                    'id':   _serialize(raw),
                    'repr': str(related)[:100] if related is not None else None,
                }
            else:
                value = _serialize(raw)
            snapshot[field.attname] = value
        except Exception:
            pass
    return snapshot


def compute_diff(before: dict, after: dict) -> dict | None:
    """
    Compare deux snapshots et retourne les champs modifiés sous la forme :
        { "champ": { "avant": v1, "apres": v2 } }
    Retourne None s'il n'y a aucun changement.
    """
    changes = {}
    for key in set(before) | set(after):
        v_before = before.get(key)
        v_after  = after.get(key)
        if v_before != v_after:
            changes[key] = {'avant': v_before, 'apres': v_after}
    return changes or None


# ═══════════════════════════════════════════════════════════════════════════
# Contexte de la requête courante
# ═══════════════════════════════════════════════════════════════════════════

def _request_context():
    """
    Extrait (user, user_repr, ip, session_key) depuis la requête courante.
    Retourne des valeurs vides/None si hors contexte HTTP.
    """
    request     = get_current_request()
    user        = None
    user_repr   = ''
    ip          = None
    session_key = ''

    if request:
        raw_user = getattr(request, 'user', None)
        if raw_user and getattr(raw_user, 'is_authenticated', False):
            user      = raw_user
            user_repr = (raw_user.get_full_name() or raw_user.username)[:150]
        ip          = get_client_ip(request)
        session_key = (getattr(request.session, 'session_key', '') or '')[:40]

    return user, user_repr, ip, session_key


# ═══════════════════════════════════════════════════════════════════════════
# Enregistrement
# ═══════════════════════════════════════════════════════════════════════════

def record(instance, action: str, changes=None, details: str = '') -> None:
    """
    Crée une AuditEntry pour l'instance et l'action données.
    Capture automatiquement user / IP depuis la requête courante.
    Ne lève jamais d'exception : toute erreur est loguée sans interrompre
    la transaction en cours.
    """
    from audit.models import AuditEntry  # import local → évite les imports circulaires
    try:
        user, user_repr, ip, session = _request_context()
        AuditEntry.objects.create(
            user=user,
            user_repr=user_repr,
            ip_address=ip,
            session_key=session,
            action=action,
            app_label=instance._meta.app_label,
            model_name=instance._meta.model_name,
            object_id=str(instance.pk or ''),
            object_repr=str(instance)[:300],
            changes=changes,
            details=details,
        )
    except Exception:
        logger.error(
            "Audit recorder : erreur création AuditEntry pour %s pk=%s action=%s",
            instance.__class__.__name__,
            getattr(instance, 'pk', None),
            action,
            exc_info=True,
        )


def record_action(request_or_user, action: str, obj, details: str = '') -> None:
    """
    Enregistre une action métier manuelle (validation, impression, export…).
    Peut être appelé depuis les vues avec la request ou directement avec un user.

    Exemple :
        from audit.services.recorder import record_action
        from audit.models import AuditEntry
        record_action(request, AuditEntry.Action.VALIDATION, achat,
                      details='Achat validé manuellement')
    """
    from audit.models import AuditEntry
    try:
        if hasattr(request_or_user, 'user'):
            # C'est une Request
            req     = request_or_user
            raw     = getattr(req, 'user', None)
            user    = raw if (raw and getattr(raw, 'is_authenticated', False)) else None
            user_repr  = (raw.get_full_name() or raw.username)[:150] if user else ''
            ip         = get_client_ip(req)
            session    = (getattr(req.session, 'session_key', '') or '')[:40]
        else:
            # C'est directement un User
            user       = request_or_user
            user_repr  = (user.get_full_name() or user.username)[:150] if user else ''
            ip         = None
            session    = ''

        AuditEntry.objects.create(
            user=user,
            user_repr=user_repr,
            ip_address=ip,
            session_key=session,
            action=action,
            app_label=obj._meta.app_label,
            model_name=obj._meta.model_name,
            object_id=str(obj.pk or ''),
            object_repr=str(obj)[:300],
            details=details,
        )
    except Exception:
        logger.error(
            "Audit recorder : erreur record_action %s sur %s",
            action, obj.__class__.__name__,
            exc_info=True,
        )


def record_login(user, request=None) -> None:
    """Enregistre une connexion réussie."""
    from audit.models import AuditEntry
    try:
        ip      = get_client_ip(request)
        session = (getattr(getattr(request, 'session', None), 'session_key', '') or '')[:40]
        AuditEntry.objects.create(
            user=user,
            user_repr=(user.get_full_name() or user.username)[:150],
            ip_address=ip,
            session_key=session,
            action=AuditEntry.Action.CONNEXION,
            app_label='auth',
            model_name='user',
            object_id=str(user.pk),
            object_repr=str(user)[:300],
            details=f'Connexion réussie — {user.username}',
        )
    except Exception:
        logger.error("Audit recorder : erreur CONNEXION", exc_info=True)


def record_logout(user, request=None) -> None:
    """Enregistre une déconnexion."""
    from audit.models import AuditEntry
    try:
        ip      = get_client_ip(request)
        session = (getattr(getattr(request, 'session', None), 'session_key', '') or '')[:40]
        AuditEntry.objects.create(
            user=user,
            user_repr=getattr(user, 'username', str(user))[:150],
            ip_address=ip,
            session_key=session,
            action=AuditEntry.Action.DECONNEXION,
            app_label='auth',
            model_name='user',
            object_id=str(getattr(user, 'pk', '')),
            object_repr=str(user)[:300],
            details=f'Déconnexion — {getattr(user, "username", str(user))}',
        )
    except Exception:
        logger.error("Audit recorder : erreur DECONNEXION", exc_info=True)


def record_login_failed(request, username: str) -> None:
    """Enregistre une tentative de connexion échouée (sans lever d'exception)."""
    from audit.models import AuditEntry
    try:
        ip = get_client_ip(request)
        AuditEntry.objects.create(
            user=None,
            user_repr=username[:150],
            ip_address=ip,
            action=AuditEntry.Action.ECHEC_CONNEXION,
            app_label='auth',
            model_name='user',
            object_id='',
            object_repr=f'Tentative échouée : "{username}"'[:300],
            details=f'Échec de connexion pour le nom d\'utilisateur : {username}',
        )
    except Exception:
        logger.error("Audit recorder : erreur ECHEC_CONNEXION", exc_info=True)
