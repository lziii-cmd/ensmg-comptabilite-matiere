# documents/views/external_entry_views.py
from decimal import Decimal
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404
from documents.utils import render_pdf, fmt_montant, fmt_qte, SEUIL_PV_RECEPTION


@staff_member_required
def bon_entree_modele1_dotation(request, pk):
    from purchasing.models import ExternalStockEntry
    entry = get_object_or_404(ExternalStockEntry, pk=pk)
    lines_qs = entry.lines.select_related('matiere__sous_compte', 'matiere__unite').all()
    
    lignes = []
    total_qte = Decimal(0)
    total_montant = Decimal(0)
    
    for line in lines_qs:
        mat = line.matiere
        qte = line.quantity or Decimal(0)
        mnt = line.total_line or Decimal(0)
        total_qte += qte
        total_montant += mnt
        lignes.append({
            "compte": mat.sous_compte.code if mat.sous_compte else "",
            "nature": mat.code_court,
            "specification": mat.designation,
            "nombre_unites": fmt_qte(qte),
            "nature_unites": mat.unite.libelle if mat.unite else "unité",
            "prix_unitaire": fmt_montant(line.unit_price or 0),
            "montant": fmt_montant(mnt),
            "num_bon_commande": entry.document_number or "",
            "observations": line.note or "",
        })
    
    nb_lignes = len(lignes)
    empty_count = max(0, 8 - nb_lignes)
    source_label = str(entry.source) if entry.source else "—"
    
    context = {
        "numero_bon": entry.code,
        "annee": entry.received_date.year if entry.received_date else "—",
        "date_doc": entry.received_date.strftime("%d/%m/%Y") if entry.received_date else "—",
        "type_entree": "Dotation / Entrée externe",
        "source_label": source_label,
        "reference": entry.document_number or "",
        "etablissement": "École normale supérieure des mines et de la géologie",
        "depot": entry.depot.nom if entry.depot else "—",
        "lignes": lignes,
        "empty_rows": range(empty_count),
        "total_qte_str": fmt_qte(total_qte),
        "total_montant_str": fmt_montant(total_montant),
    }
    return render_pdf(request, "documents/bon_entree_modele1.html", context,
                      filename=f"bon_entree_{entry.code}.pdf")


@staff_member_required
def pv_reception_dotation(request, pk):
    from purchasing.models import ExternalStockEntry
    entry = get_object_or_404(ExternalStockEntry, pk=pk)
    # Règle métier : PVR obligatoire uniquement si valeur ≥ seuil
    if entry.total_value < SEUIL_PV_RECEPTION:
        return bon_entree_modele1_dotation(request, pk)
    lines_qs = entry.lines.select_related('matiere__unite').all()
    lignes = []
    total_qte = Decimal(0)
    for line in lines_qs:
        qte = line.quantity or Decimal(0)
        mnt = line.total_line or Decimal(0)
        total_qte += qte
        lignes.append({
            "code":          line.matiere.code_court,
            "designation":   line.matiere.designation,
            "quantite":      qte,
            "unite":         line.matiere.unite.abreviation if line.matiere.unite else "—",
            "specification": "",
            "prix_unitaire": line.unit_price or 0,
            "montant":       mnt,
            "observation":   line.note or "",
        })
    ref_pieces = []
    if entry.document_number:
        ref_pieces.append(f"Document n° {entry.document_number}")
    context = {
        "numero_doc":         entry.code,
        "date_reception":     entry.received_date,
        "source_label":       "Source / Organisme",
        "source_nom":         str(entry.source) if entry.source else "—",
        "source_detail":      "",
        "depot_nom":          entry.depot.nom if entry.depot else "—",
        "reference_pieces":   ref_pieces,
        "lignes":             lignes,
        "total_quantite":     total_qte,
        "total_montant":      entry.total_value,
        "commission_membres": [],
    }
    return render_pdf(
        request,
        "documents/pv_reception_officiel.html",
        context,
        filename=f"pv_reception_dotation_{entry.code}.pdf",
    )


@staff_member_required
def document_dotation(request, pk):
    """
    Routeur intelligent :
    - Valeur < 300 000 F CFA  → Bon d'entrée (modèle 1)
    - Valeur ≥ 300 000 F CFA  → PV de réception (commission obligatoire)
    """
    from purchasing.models import ExternalStockEntry
    entry = get_object_or_404(ExternalStockEntry, pk=pk)
    if entry.total_value >= SEUIL_PV_RECEPTION:
        return pv_reception_dotation(request, pk)
    return bon_entree_modele1_dotation(request, pk)
