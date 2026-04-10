# inventory/services/stock.py
from decimal import Decimal
from django.db import transaction
from django.apps import apps


def _get_sc_model():
    return apps.get_model("inventory", "StockCourant")


def _get_ms_model():
    return apps.get_model("inventory", "MouvementStock")


def _get_or_create_courant(exercice_id, matiere_id, depot_id):
    StockCourant = _get_sc_model()
    obj, _ = StockCourant.objects.get_or_create(
        exercice_id=exercice_id,
        matiere_id=matiere_id,
        depot_id=depot_id,
        defaults={
            "quantite": Decimal("0"),
            "cump": Decimal("0"),
            "stock_initial_qte": Decimal("0"),
            "stock_initial_cu": Decimal("0"),
        },
    )
    return obj


@transaction.atomic
def recompute_stock_courant(exercice_id, matiere_id, depot_id):
    """
    Recalcule entièrement le StockCourant (quantité + CUMP) à partir
    de *tous* les mouvements du triplet (exercice, matière, dépôt).
    Si la matière n’a pas de stock initial, le premier mouvement d’entrée
    devient le stock initial automatique.
    """
    if not (exercice_id and matiere_id and depot_id):
        return

    MouvementStock = _get_ms_model()
    StockCourant = _get_sc_model()

    mouvements = (
        MouvementStock.objects
        .filter(exercice_id=exercice_id, matiere_id=matiere_id, depot_id=depot_id)
        .order_by("date", "id")
        .only("type", "quantite", "cout_unitaire", "is_stock_initial")
    )

    q = Decimal("0")
    value = Decimal("0")
    cump = Decimal("0")
    init_q = Decimal("0")
    init_cu = Decimal("0")
    init_done = False

    for m in mouvements:
        # ---- ENTRÉES ----
        if m.type in ("ENTREE", "AJUSTEMENT"):
            cu = m.cout_unitaire or Decimal("0")
            value += (m.quantite * cu)
            q += m.quantite
            cump = (value / q) if q > 0 else Decimal("0")

            # ✅ Si aucun stock initial enregistré, on prend le premier mouvement ENTREE comme initial
            if not init_done:
                init_q = m.quantite
                init_cu = cu
                init_done = True

        # ---- SORTIES & AFFECTATIONS (1er groupe) ----
        # L'affectation sort le bien du dépôt (responsabilité change),
        # mais le patrimoine reste dans FicheAffectation.
        elif m.type in ("SORTIE", "AFFECTATION"):
            out = m.quantite
            if out > q:
                out = q
            value -= (out * cump)
            q -= out
            if q == 0:
                value = Decimal("0")
                cump = Decimal("0")

    # ---- Mise à jour / création du StockCourant ----
    sc = _get_or_create_courant(exercice_id, matiere_id, depot_id)
    sc.quantite = q
    sc.cump = cump
    sc.stock_initial_qte = init_q
    sc.stock_initial_cu = init_cu
    sc.save(update_fields=["quantite", "cump", "stock_initial_qte", "stock_initial_cu"])

    # ✅ Si matière obtient un stock positif, on la marque comme stockée
    try:
        if q > 0:
            Matiere = apps.get_model("catalog", "Matiere")
            Matiere.objects.filter(id=matiere_id, est_stocke=False).update(est_stocke=True)
    except Exception:
        pass


@transaction.atomic
def appliquer_mouvement_sur_courant(mvt):
    """
    API appelée par les signaux : on recalcule complètement le stock courant
    pour le triplet concerné.
    """
    if mvt and mvt.exercice_id and mvt.matiere_id and mvt.depot_id:
        recompute_stock_courant(mvt.exercice_id, mvt.matiere_id, mvt.depot_id)
