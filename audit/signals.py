# audit/signals.py
"""
Signaux universels d'audit.

Pour chaque modèle de AUDITED_MODELS, trois handlers sont connectés :
  - pre_save   → capture l'état AVANT modification dans instance._audit_snapshot
  - post_save  → enregistre CREATION (si créé) ou MODIFICATION (avec diff si changements)
  - post_delete → enregistre SUPPRESSION

Les signaux d'authentification (connexion / déconnexion / échec) sont aussi
connectés ici et appelés dans AuditConfig.ready().

Ajouter un nouveau modèle à auditer : il suffit d'ajouter ('app', 'Modele')
dans AUDITED_MODELS ci-dessous. Aucune autre modification n'est nécessaire.
"""
import logging

from django.apps import apps
from django.db.models.signals import pre_save, post_save, post_delete
from django.contrib.auth.signals import (
    user_logged_in, user_logged_out, user_login_failed,
)

from audit.models import AuditEntry
from audit.services import recorder

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Registre des modèles à auditer
# ═══════════════════════════════════════════════════════════════════════════
# Format : (app_label, NomDuModele)
# Tous les champs non-exclus (pas PK, pas auto_now, pas fichiers) sont tracés.

AUDITED_MODELS = [
    # ── Catalogue ──────────────────────────────────────────────────────────
    ('catalog', 'Matiere'),
    ('catalog', 'Categorie'),
    ('catalog', 'SousCategorie'),
    ('catalog', 'ComptePrincipal'),
    ('catalog', 'CompteDivisionnaire'),
    ('catalog', 'SousCompte'),

    # ── Référentiels core ──────────────────────────────────────────────────
    ('core', 'Fournisseur'),
    ('core', 'Depot'),
    ('core', 'Service'),
    ('core', 'Exercice'),
    ('core', 'Donateur'),
    ('core', 'Unite'),

    # ── Achats & entrées ───────────────────────────────────────────────────
    ('purchasing', 'Achat'),
    ('purchasing', 'LigneAchat'),
    ('purchasing', 'Don'),
    ('purchasing', 'LigneDon'),
    ('purchasing', 'Pret'),
    ('purchasing', 'LignePret'),
    ('purchasing', 'RetourFournisseur'),
    ('purchasing', 'LigneRetour'),
    ('purchasing', 'RetourPret'),
    ('purchasing', 'LigneRetourPret'),
    ('purchasing', 'Dotation'),
    ('purchasing', 'LigneDotation'),
    ('purchasing', 'ExternalStockEntry'),
    ('purchasing', 'ExternalStockEntryLine'),
    ('purchasing', 'LegsEntry'),

    # ── Stock & opérations ─────────────────────────────────────────────────
    ('inventory', 'MouvementStock'),
    ('inventory', 'StockCourant'),
    ('inventory', 'OperationSortie'),
    ('inventory', 'LigneOperationSortie'),
    ('inventory', 'OperationTransfert'),
    ('inventory', 'LigneOperationTransfert'),
    ('inventory', 'FicheAffectation'),
]


# ═══════════════════════════════════════════════════════════════════════════
# Fabriques de handlers (évite les problèmes de closure en boucle)
# ═══════════════════════════════════════════════════════════════════════════

def _make_pre_save(model_cls):
    """
    Handler pre_save : capture l'état courant de l'objet en base
    avant qu'il ne soit écrasé par le save().
    """
    def handler(sender, instance, **kwargs):
        if not instance.pk:
            # Nouvel objet : pas d'état avant
            instance._audit_snapshot = {}
            return
        try:
            old = model_cls.objects.get(pk=instance.pk)
            instance._audit_snapshot = recorder.take_snapshot(old)
        except model_cls.DoesNotExist:
            instance._audit_snapshot = {}
        except Exception:
            logger.error(
                "Audit pre_save : erreur snapshot %s pk=%s",
                model_cls.__name__, instance.pk, exc_info=True,
            )
            instance._audit_snapshot = {}

    handler.__name__ = f'_audit_pre_save_{model_cls.__name__.lower()}'
    return handler


def _make_post_save(model_cls):
    """
    Handler post_save :
      - Si created=True → CREATION
      - Sinon           → MODIFICATION uniquement si le diff est non vide
    """
    def handler(sender, instance, created, **kwargs):
        try:
            if created:
                recorder.record(instance, AuditEntry.Action.CREATION)
            else:
                old_snap  = getattr(instance, '_audit_snapshot', {})
                new_snap  = recorder.take_snapshot(instance)
                changes   = recorder.compute_diff(old_snap, new_snap)
                if changes:
                    recorder.record(
                        instance,
                        AuditEntry.Action.MODIFICATION,
                        changes=changes,
                    )
        except Exception:
            logger.error(
                "Audit post_save : erreur %s pk=%s",
                model_cls.__name__, getattr(instance, 'pk', None), exc_info=True,
            )

    handler.__name__ = f'_audit_post_save_{model_cls.__name__.lower()}'
    return handler


def _make_post_delete(model_cls):
    """Handler post_delete : SUPPRESSION avec mention de l'ID et du str()."""
    def handler(sender, instance, **kwargs):
        try:
            recorder.record(
                instance,
                AuditEntry.Action.SUPPRESSION,
                details=f'Suppression de {model_cls.__name__} #{instance.pk}',
            )
        except Exception:
            logger.error(
                "Audit post_delete : erreur %s pk=%s",
                model_cls.__name__, getattr(instance, 'pk', None), exc_info=True,
            )

    handler.__name__ = f'_audit_post_delete_{model_cls.__name__.lower()}'
    return handler


# ═══════════════════════════════════════════════════════════════════════════
# Handlers d'authentification
# ═══════════════════════════════════════════════════════════════════════════

def _on_login(sender, request, user, **kwargs):
    recorder.record_login(user, request)


def _on_logout(sender, request, user, **kwargs):
    recorder.record_logout(user, request)


def _on_login_failed(sender, credentials, request, **kwargs):
    recorder.record_login_failed(request, credentials.get('username', ''))


# ═══════════════════════════════════════════════════════════════════════════
# Point d'entrée — appelé par AuditConfig.ready()
# ═══════════════════════════════════════════════════════════════════════════

def connect_all() -> None:
    """
    Connecte les signaux pre_save / post_save / post_delete pour chaque modèle
    de AUDITED_MODELS, ainsi que les signaux d'authentification.
    Appelé une seule fois depuis AuditConfig.ready().
    """
    connected = 0
    skipped   = 0

    for app_label, model_name in AUDITED_MODELS:
        try:
            model_cls = apps.get_model(app_label, model_name)
        except LookupError:
            logger.warning(
                "Audit : modèle %s.%s introuvable — signal ignoré.",
                app_label, model_name,
            )
            skipped += 1
            continue

        pre_save.connect(
            _make_pre_save(model_cls),
            sender=model_cls,
            weak=False,                 # weak=False → référence forte, évite le GC
        )
        post_save.connect(
            _make_post_save(model_cls),
            sender=model_cls,
            weak=False,
        )
        post_delete.connect(
            _make_post_delete(model_cls),
            sender=model_cls,
            weak=False,
        )
        connected += 1

    # Signaux d'authentification (une seule connexion suffit)
    user_logged_in.connect(_on_login,        weak=False)
    user_logged_out.connect(_on_logout,      weak=False)
    user_login_failed.connect(_on_login_failed, weak=False)

    logger.info(
        "Audit : signaux connectés pour %d modèles (%d ignorés).",
        connected, skipped,
    )
