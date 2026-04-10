# documents/views/don_views.py
from decimal import Decimal
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404

from documents.utils import render_pdf, fmt_montant, fmt_qte, SEUIL_PV_RECEPTION
from purchasing.models import Don


@staff_member_required
def bon_entree_don(request, pk):
    don = get_object_or_404(Don, pk=pk)
    context = {
        "don": don,
        "date_doc": don.date_don,
        "exercice_label": f"Exercice {don.date_don.year}",
    }
    return render_pdf(
        request,
        "documents/bon_entree_don.html",
        context,
        filename=f"bon_entree_don_{don.code}.pdf",
    )


@staff_member_required
def pv_reception_don(request, pk):
    don = get_object_or_404(Don, pk=pk)
    lignes_qs = don.lignes.select_related('matiere__unite').all()
    lignes = []
    total_qte = Decimal(0)
    for ligne in lignes_qs:
        qte = ligne.quantite or Decimal(0)
        mnt = ligne.total_ligne or Decimal(0)
        total_qte += qte
        lignes.append({
            "code":          ligne.matiere.code_court,
            "designation":   ligne.matiere.designation,
            "quantite":      qte,
            "unite":         ligne.matiere.unite.abreviation if ligne.matiere.unite else "—",
            "specification": "",
            "prix_unitaire": ligne.prix_unitaire or 0,
            "montant":       mnt,
            "observation":   ligne.observation or "",
        })
    ref_pieces = []
    if don.numero_piece:
        ref_pieces.append(f"Pièce n° {don.numero_piece}")
    context = {
        "numero_doc":         don.code,
        "date_reception":     don.date_don,
        "source_label":       "Donateur",
        "source_nom":         don.donateur.raison_sociale if don.donateur else "—",
        "source_detail":      "",
        "depot_nom":          don.depot.nom if don.depot else "—",
        "reference_pieces":   ref_pieces,
        "lignes":             lignes,
        "total_quantite":     total_qte,
        "total_montant":      don.total_valeur,
        "commission_membres": [],
    }
    return render_pdf(
        request,
        "documents/pv_reception_officiel.html",
        context,
        filename=f"pv_reception_don_{don.code}.pdf",
    )


@staff_member_required
def document_don(request, pk):
    """
    Un don génère toujours un PV de réception, quel que soit le montant.
    """
    return pv_reception_don(request, pk)


@staff_member_required
def bon_entree_modele1_don(request, pk):
    don = get_object_or_404(Don, pk=pk)
    lignes_qs = don.lignes.select_related('matiere__sous_compte', 'matiere__unite').all()
    
    lignes = []
    total_qte = Decimal(0)
    total_montant = Decimal(0)
    
    for ligne in lignes_qs:
        mat = ligne.matiere
        qte = ligne.quantite or Decimal(0)
        mnt = ligne.total_ligne or Decimal(0)
        total_qte += qte
        total_montant += mnt
        lignes.append({
            "compte": mat.sous_compte.code if mat.sous_compte else "",
            "nature": mat.code_court,
            "specification": mat.designation,
            "nombre_unites": fmt_qte(qte),
            "nature_unites": mat.unite.libelle if mat.unite else "unité",
            "prix_unitaire": fmt_montant(ligne.prix_unitaire or 0),
            "montant": fmt_montant(mnt),
            "num_bon_commande": don.numero_piece or "",
            "observations": ligne.observation or "",
        })
    
    nb_lignes = len(lignes)
    empty_count = max(0, 8 - nb_lignes)
    donateur_label = str(don.donateur) if don.donateur else "—"
    
    context = {
        "numero_bon": don.code,
        "annee": don.date_don.year if don.date_don else "—",
        "date_doc": don.date_don.strftime("%d/%m/%Y") if don.date_don else "—",
        "type_entree": "Don / Donation",
        "source_label": donateur_label,
        "reference": don.numero_piece or "",
        "etablissement": "École normale supérieure des mines et de la géologie",
        "depot": don.depot.nom if don.depot else "—",
        "lignes": lignes,
        "empty_rows": range(empty_count),
        "total_qte_str": fmt_qte(total_qte),
        "total_montant_str": fmt_montant(total_montant),
    }
    return render_pdf(request, "documents/bon_entree_modele1.html", context,
                      filename=f"bon_entree_{don.code}.pdf")
