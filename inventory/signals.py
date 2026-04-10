# inventory/signals.py
import logging

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.apps import apps
from .services.stock import appliquer_mouvement_sur_courant, recompute_stock_courant

logger = logging.getLogger(__name__)


def _ms_model():
    return apps.get_model("inventory", "MouvementStock")


def _is_mouvement(instance) -> bool:
    MS = _ms_model()
    return isinstance(instance, MS)  # ok avec les proxies


@receiver(pre_save)
def _mvt_presave_capture_old(sender, instance, **kwargs):
    """
    Avant sauvegarde, capture l'ancien triplet (exercice, matière, dépôt) pour
    pouvoir recalculer l'ancien StockCourant si ces clés changent.
    """
    if not _is_mouvement(instance) or not instance.pk:
        return
    try:
        MS = _ms_model()
        old = MS.objects.filter(pk=instance.pk).values(
            "exercice_id", "matiere_id", "depot_id"
        ).first()
        if old:
            instance._old_tuple = (old["exercice_id"], old["matiere_id"], old["depot_id"])
    except Exception:
        logger.error(
            "Erreur dans le signal pre_save (capture old_tuple) pour MouvementStock pk=%s",
            instance.pk,
            exc_info=True,
        )
        instance._old_tuple = None


@receiver(post_save)
def _mvt_saved(sender, instance, created, **kwargs):
    if not _is_mouvement(instance):
        return
    # Recalcule pour le nouveau triplet
    try:
        appliquer_mouvement_sur_courant(instance)
    except Exception:
        logger.error(
            "Erreur dans le signal post_save (appliquer_mouvement_sur_courant) "
            "pour MouvementStock pk=%s",
            instance.pk,
            exc_info=True,
        )

    # Si les clés ont changé, recalculer aussi l'ancien triplet
    old_tuple = getattr(instance, "_old_tuple", None)
    if old_tuple:
        exo_id, mat_id, dep_id = old_tuple
        if (exo_id, mat_id, dep_id) != (instance.exercice_id, instance.matiere_id, instance.depot_id):
            try:
                if exo_id and mat_id and dep_id:
                    recompute_stock_courant(exo_id, mat_id, dep_id)
            except Exception:
                logger.error(
                    "Erreur dans le signal post_save (recompute ancien triplet) "
                    "pour MouvementStock pk=%s — ancien triplet=(%s, %s, %s)",
                    instance.pk, exo_id, mat_id, dep_id,
                    exc_info=True,
                )


@receiver(post_delete)
def _mvt_deleted(sender, instance, **kwargs):
    if not _is_mouvement(instance):
        return
    # Recalcule pour le triplet affecté par la suppression
    try:
        if instance.exercice_id and instance.matiere_id and instance.depot_id:
            recompute_stock_courant(instance.exercice_id, instance.matiere_id, instance.depot_id)
    except Exception:
        logger.error(
            "Erreur dans le signal post_delete (recompute_stock_courant) "
            "pour MouvementStock pk=%s",
            instance.pk,
            exc_info=True,
        )
