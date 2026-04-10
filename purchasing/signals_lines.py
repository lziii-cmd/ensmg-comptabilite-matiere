# purchasing/signals_lines.py
from decimal import Decimal
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.apps import apps
from purchasing.models import LigneAchat

# ---------- util: totaux achat ----------
def _recompute_parent(achat):
    try:
        achat.recompute_totaux()
        achat.save(update_fields=["total_ht", "total_tva", "total_ttc"])
    except Exception:
        pass

# ---------- util: trouver depot par défaut ----------
def _get_default_depot():
    Depot = apps.get_model("core", "Depot")
    # à adapter selon ton modèle: principal=True, code="PRINCIPAL", etc.
    depot = getattr(Depot.objects.filter(principal=True).first(), "id", None)
    if depot:
        return Depot.objects.get(id=depot)
    # fallback: premier dépôt trouvé
    return Depot.objects.order_by("id").first()

# ---------- util: créer/maj/supprimer mvt pour la ligne ----------
def _update_stock_for_ligne(ligne: LigneAchat):
    if not ligne.achat or not ligne.matiere:
        return

    MouvementStock = apps.get_model("inventory", "MouvementStock")
    from inventory.services.exercice import exercice_courant

    exo = exercice_courant(getattr(ligne.achat, "date_achat", None))

    # dépôt requis pour ENTREE; on prend celui de l'achat, sinon un défaut
    depot = getattr(ligne.achat, "depot", None)
    if depot is None:
        depot = _get_default_depot()
        if depot is None:
            # aucun dépôt disponible → on ne crée pas de mouvement
            return

    # quantité > 0 ?
    if (ligne.quantite or Decimal("0")) <= 0:
        MouvementStock.objects.filter(
            source_doc_type="purchasing.LigneAchat",
            source_doc_id=ligne.id,
        ).delete()
        return

    ref = f"ACH-{getattr(ligne.achat, 'code', '')}".rstrip("-")

    try:
        mvt, created = MouvementStock.objects.get_or_create(
            source_doc_type="purchasing.LigneAchat",
            source_doc_id=ligne.id,
            defaults=dict(
                type="ENTREE",
                exercice=exo,
                matiere=ligne.matiere,
                depot=depot,
                quantite=ligne.quantite,
                cout_unitaire=ligne.prix_unitaire or Decimal("0"),
                reference=ref,
                commentaire=f"Entrée de stock suite à l'achat {getattr(ligne.achat, 'code', '')}",
            ),
        )

        need_update = False
        if mvt.exercice_id != (exo.id if exo else None):
            mvt.exercice = exo; need_update = True
        if mvt.depot_id != getattr(depot, "id", None):
            mvt.depot = depot; need_update = True
        if mvt.matiere_id != ligne.matiere_id:
            mvt.matiere = ligne.matiere; need_update = True
        if mvt.quantite != ligne.quantite:
            mvt.quantite = ligne.quantite; need_update = True
        cu = ligne.prix_unitaire or Decimal("0")
        if mvt.cout_unitaire != cu:
            mvt.cout_unitaire = cu; need_update = True
        if (mvt.reference or "") != ref:
            mvt.reference = ref; need_update = True

        if need_update:
            mvt.save()

    except Exception:
        # évite de casser la sauvegarde de l'achat en cas d'anomalie stock
        pass

def _delete_stock_for_ligne(ligne: LigneAchat):
    MouvementStock = apps.get_model("inventory", "MouvementStock")
    MouvementStock.objects.filter(
        source_doc_type="purchasing.LigneAchat",
        source_doc_id=ligne.id,
    ).delete()

# ---------- signaux ----------
@receiver(post_save, sender=LigneAchat)
def _ligne_achat_saved(sender, instance: LigneAchat, **kwargs):
    if instance.achat_id:
        _recompute_parent(instance.achat)
        _update_stock_for_ligne(instance)

@receiver(post_delete, sender=LigneAchat)
def _ligne_achat_deleted(sender, instance: LigneAchat, **kwargs):
    if instance.achat_id:
        _recompute_parent(instance.achat)
        _delete_stock_for_ligne(instance)
