# documents/views/stock_views.py
from decimal import Decimal
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404
from django.utils import timezone

from documents.utils import render_pdf
from catalog.models import Matiere
from core.models import Exercice
from inventory.models import MouvementStock, StockCourant


@staff_member_required
def fiche_stock(request, matiere_pk, exercice_pk=None):
    matiere = get_object_or_404(
        Matiere.objects.select_related(
            "sous_compte__compte_divisionnaire__compte_principal",
            "sous_categorie__categorie",
            "unite",
        ),
        pk=matiere_pk,
    )

    # Exercice : celui fourni, ou le courant
    if exercice_pk:
        exercice = get_object_or_404(Exercice, pk=exercice_pk)
    else:
        exercice = Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
        if not exercice:
            exercice = Exercice.objects.order_by("-annee").first()

    # Stock initial agrégé sur tous les dépôts
    stocks = StockCourant.objects.filter(
        matiere=matiere, exercice=exercice
    ).select_related("depot")

    stock_initial_qte = sum(s.stock_initial_qte for s in stocks)
    stock_initial_cu = (
        stocks.first().stock_initial_cu if stocks.exists() else Decimal("0")
    )
    valeur_initiale = stock_initial_qte * stock_initial_cu

    # Mouvements de l'exercice
    mouvements_qs = (
        MouvementStock.objects.filter(matiere=matiere, exercice=exercice)
        .select_related("depot", "source_depot", "destination_depot")
        .order_by("date", "pk")
    )

    # Construire les lignes enrichies avec libellé et stock cumulé
    mouvements = []
    stock_courant = stock_initial_qte
    total_entrees = Decimal("0")
    total_sorties = Decimal("0")

    for m in mouvements_qs:
        if m.is_stock_initial:
            continue  # déjà dans le solde initial

        if m.type == "ENTREE":
            stock_courant += m.quantite
            total_entrees += m.quantite
            libelle = f"Entrée — {m.reference or m.source_doc_type or ''}"
            depot_label = m.depot.nom if m.depot else "—"
        elif m.type == "SORTIE":
            stock_courant -= m.quantite
            total_sorties += m.quantite
            libelle = f"Sortie — {m.reference or m.source_doc_type or ''}"
            depot_label = m.depot.nom if m.depot else "—"
        elif m.type == "TRANSFERT":
            libelle = (
                f"Transfert : {m.source_depot.nom if m.source_depot else '?'}"
                f" → {m.destination_depot.nom if m.destination_depot else '?'}"
            )
            depot_label = "—"
            # Le transfert sort d'un dépôt et entre dans un autre
            # Pour la fiche globale on l'affiche comme entrée si dest, sortie si source
            total_entrees += m.quantite  # transfert interne neutre en qté globale
        else:
            libelle = f"Ajustement — {m.commentaire or ''}"
            depot_label = m.depot.nom if m.depot else "—"
            stock_courant += m.quantite  # peut être négatif

        mouvements.append({
            "date": m.date,
            "reference": m.reference or m.source_doc_type,
            "libelle": libelle,
            "type": m.type,
            "depot_label": depot_label,
            "quantite": m.quantite,
            "cout_unitaire": m.cout_unitaire,
            "stock_apres": stock_courant,
            "valeur_apres": stock_courant * (m.cout_unitaire or stock_initial_cu or Decimal("1")),
        })

    stock_final = stock_courant
    valeur_finale = sum(s.valeur for s in stocks)

    # Répartition par dépôt
    stocks_par_depot = (
        StockCourant.objects.filter(matiere=matiere, exercice=exercice)
        .values("depot__nom")
        .extra(select={"quantite": "quantite", "cump": "cump", "valeur": "quantite * cump"})
        .order_by("depot__nom")
    )

    context = {
        "matiere": matiere,
        "exercice": exercice,
        "stock_initial_qte": stock_initial_qte,
        "stock_initial_cu": stock_initial_cu,
        "valeur_initiale": valeur_initiale,
        "mouvements": mouvements,
        "total_entrees": total_entrees,
        "total_sorties": total_sorties,
        "stock_final": stock_final,
        "valeur_finale": valeur_finale,
        "stocks_par_depot": stocks,
        "date_doc": timezone.now().date(),
        "exercice_label": exercice.code,
    }
    return render_pdf(
        request,
        "documents/fiche_stock.html",
        context,
        filename=f"fiche_stock_{matiere.code_court}_{exercice.code}.pdf",
    )
