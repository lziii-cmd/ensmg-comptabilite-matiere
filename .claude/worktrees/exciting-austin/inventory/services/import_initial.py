# inventory/services/import_initial.py
from decimal import Decimal
from django.db import transaction
from django.apps import apps

@transaction.atomic
def importer_stocks_initiaux_depuis_precedent(exercice_cible):
    """
    Pour chaque (matiere, depot) ayant un StockCourant en fin d'exercice précédent,
    créer un MouvementStock ENTREE is_stock_initial=True pour l'exercice cible
    s'il n'existe pas déjà.
    - quantité = quantite du StockCourant précédent
    - cout_unitaire = CUMP du StockCourant précédent
    """
    if not exercice_cible:
        return 0

    Exercice = apps.get_model("core", "Exercice")
    StockCourant = apps.get_model("inventory", "StockCourant")
    MouvementStock = apps.get_model("inventory", "MouvementStock")

    # Trouver l'exercice précédent
    exo_prev = (
        Exercice.objects.filter(date_fin__lt=exercice_cible.date_debut)
        .order_by("-date_fin")
        .first()
    )
    if not exo_prev:
        return 0

    rows = StockCourant.objects.filter(exercice=exo_prev, quantite__gt=0)
    created = 0
    for sc in rows:
        exists = MouvementStock.objects.filter(
            type="ENTREE",
            is_stock_initial=True,
            exercice=exercice_cible,
            matiere=sc.matiere,
            depot=sc.depot,
        ).exists()
        if exists:
            continue

        m = MouvementStock(
            type="ENTREE",
            is_stock_initial=True,
            exercice=exercice_cible,
            matiere=sc.matiere,
            depot=sc.depot,
            quantite=sc.quantite,
            cout_unitaire=sc.cump or Decimal("0"),
            reference=f"IMPORT-{exo_prev.id}->{exercice_cible.id}",
            commentaire="Import automatique des stocks initiaux depuis l'exercice précédent",
        )
        m.save()
        created += 1
    return created
