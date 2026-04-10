# documents/views/transfert_views.py
from decimal import Decimal
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404

from documents.utils import render_pdf, fmt_montant, fmt_qte
from inventory.models import OperationTransfert


@staff_member_required
def bon_mutation(request, pk):
    transfert = get_object_or_404(OperationTransfert, pk=pk)
    nb_lignes = transfert.lignes.count()
    context = {
        "transfert": transfert,
        "date_doc": transfert.date_operation,
        "exercice_label": f"Exercice {transfert.date_operation.year}",
        "empty_rows": range(max(0, 12 - nb_lignes)),
    }
    return render_pdf(
        request,
        "documents/bon_mutation.html",
        context,
        filename=f"bon_mutation_{transfert.code}.pdf",
    )


@staff_member_required
def bon_entree_modele1_transfert(request, pk):
    transfert = get_object_or_404(OperationTransfert, pk=pk)
    lignes_qs = transfert.lignes.select_related('matiere__sous_compte', 'matiere__unite').all()
    
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
            "prix_unitaire": fmt_montant(ligne.cout_unitaire or 0),
            "montant": fmt_montant(mnt),
            "num_bon_commande": transfert.code or "",
            "observations": ligne.commentaire or "",
        })
    
    nb_lignes = len(lignes)
    empty_count = max(0, 8 - nb_lignes)
    source = str(transfert.depot_source) if transfert.depot_source else "—"
    motif_label = transfert.get_motif_display() if hasattr(transfert, 'get_motif_display') else transfert.motif
    
    context = {
        "numero_bon": transfert.code,
        "annee": transfert.date_operation.year if transfert.date_operation else "—",
        "date_doc": transfert.date_operation.strftime("%d/%m/%Y") if transfert.date_operation else "—",
        "type_entree": f"Transfert reçu ({motif_label})",
        "source_label": f"Dépôt source : {source}",
        "reference": transfert.code or "",
        "etablissement": "École normale supérieure des mines et de la géologie",
        "depot": str(transfert.depot_destination) if transfert.depot_destination else "—",
        "lignes": lignes,
        "empty_rows": range(empty_count),
        "total_qte_str": fmt_qte(total_qte),
        "total_montant_str": fmt_montant(total_montant),
    }
    return render_pdf(request, "documents/bon_entree_modele1.html", context,
                      filename=f"bon_entree_transfert_{transfert.code}.pdf")
