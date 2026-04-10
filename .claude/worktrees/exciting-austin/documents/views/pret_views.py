# documents/views/pret_views.py
from decimal import Decimal
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404

from documents.utils import render_pdf
from purchasing.models import Pret, LignePret, RetourPret, LigneRetourPret


@staff_member_required
def bon_pret(request, pk):
    pret = get_object_or_404(Pret, pk=pk)

    # Calculer pour chaque ligne : qté retournée et solde restant
    lignes_enrichies = []
    for ligne in pret.lignes.select_related("matiere__unite").all():
        # Sommer tous les retours pour cette matière sur ce prêt
        from django.db.models import Sum
        qte_retournee = (
            pret.retours
            .filter(lignes_retour_pret__matiere=ligne.matiere)
            .aggregate(total=Sum("lignes_retour_pret__quantite"))["total"]
            or Decimal("0")
        )
        solde = ligne.quantite - qte_retournee

        # On ajoute des attributs dynamiques
        ligne.qte_retournee = qte_retournee
        ligne.solde = solde
        lignes_enrichies.append(ligne)

    nb_lignes = len(lignes_enrichies)
    context = {
        "pret": pret,
        "lignes": lignes_enrichies,
        "date_doc": pret.date_pret,
        "exercice_label": f"Exercice {pret.date_pret.year}",
        "empty_rows": range(max(0, 8 - nb_lignes)),
    }
    return render_pdf(
        request,
        "documents/bon_pret.html",
        context,
        filename=f"bon_pret_{pret.code}.pdf",
    )


@staff_member_required
def bon_retour_pret(request, pk):
    """
    Bon de retour de prêt.
    Affiche les matières restituées, les quantités prêtées,
    retournées ce jour et le solde restant à rendre.
    """
    retour = get_object_or_404(RetourPret.objects.select_related("pret__service", "pret__depot"), pk=pk)
    pret = retour.pret

    # ── Pour chaque ligne retournée : enrichir avec qté prêtée et solde restant ──
    lignes_enrichies = []
    for ligne in retour.lignes_retour_pret.select_related("matiere__unite", "matiere__sous_compte").all():
        # Qté prêtée pour cette matière sur le prêt d'origine
        qte_pretee = (
            pret.lignes.filter(matiere=ligne.matiere)
            .aggregate(s=Sum("quantite"))["s"] or Decimal("0")
        )
        # Qté totale déjà retournée (tous retours, y compris ce retour)
        qte_deja_retournee = (
            pret.retours
            .filter(lignes_retour_pret__matiere=ligne.matiere)
            .aggregate(s=Sum("lignes_retour_pret__quantite"))["s"] or Decimal("0")
        )
        # Solde restant après ce retour
        solde_restant = max(Decimal("0"), qte_pretee - qte_deja_retournee)

        ligne.qte_pretee = qte_pretee
        ligne.solde_restant = solde_restant
        lignes_enrichies.append(ligne)

    nb_lignes = len(lignes_enrichies)

    context = {
        "retour":     retour,
        "pret":       pret,
        "lignes":     lignes_enrichies,
        "pret_clos":  pret.est_clos,
        "date_doc":   retour.date_retour,
        "empty_rows": range(max(0, 8 - nb_lignes)),
    }
    return render_pdf(
        request,
        "documents/bon_retour_pret.html",
        context,
        filename=f"bon_retour_pret_{retour.code}.pdf",
    )
