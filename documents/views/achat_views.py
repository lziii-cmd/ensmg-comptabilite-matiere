# documents/views/achat_views.py
from decimal import Decimal
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404
from django.utils import timezone

from documents.utils import render_pdf, SEUIL_PV_RECEPTION, fmt_montant, fmt_qte
from purchasing.models import Achat


@staff_member_required
def bon_entree_achat(request, pk):
    achat = get_object_or_404(Achat, pk=pk)
    context = {
        "achat": achat,
        "date_doc": achat.date_achat,
        "exercice_label": f"Exercice {achat.date_achat.year}",
    }
    return render_pdf(
        request,
        "documents/bon_entree_achat.html",
        context,
        filename=f"bon_entree_{achat.code}.pdf",
    )


@staff_member_required
def pv_reception_achat(request, pk):
    achat = get_object_or_404(Achat, pk=pk)
    # Règle métier : PVR obligatoire uniquement si montant ≥ seuil
    if achat.total_ttc < SEUIL_PV_RECEPTION:
        return bon_entree_achat(request, pk)
    lignes_qs = achat.lignes.select_related('matiere__unite').all()
    lignes = []
    total_qte = Decimal(0)
    for ligne in lignes_qs:
        qte = ligne.quantite or Decimal(0)
        mnt = ligne.total_ligne_ht or Decimal(0)
        total_qte += qte
        lignes.append({
            "code":          ligne.matiere.code_court,
            "designation":   ligne.matiere.designation,
            "quantite":      qte,
            "unite":         ligne.matiere.unite.abreviation if ligne.matiere.unite else "—",
            "specification": ligne.appreciation or "",
            "prix_unitaire": ligne.prix_unitaire or 0,
            "montant":       mnt,
            "observation":   "",
        })
    ref_pieces = []
    if achat.numero_facture:
        ref_pieces.append(f"Facture n° {achat.numero_facture}")
    context = {
        "numero_doc":         achat.code,
        "date_reception":     achat.date_achat,
        "source_label":       "Fournisseur",
        "source_nom":         achat.fournisseur.raison_sociale if achat.fournisseur else "—",
        "source_detail":      f"NINEA : {achat.fournisseur.ninea}" if achat.fournisseur and achat.fournisseur.ninea else "",
        "depot_nom":          achat.depot.nom if achat.depot else "—",
        "reference_pieces":   ref_pieces,
        "lignes":             lignes,
        "total_quantite":     total_qte,
        "total_montant":      achat.total_ht,
        "commission_membres": [],
    }
    return render_pdf(
        request,
        "documents/pv_reception_officiel.html",
        context,
        filename=f"pv_reception_{achat.code}.pdf",
    )


@staff_member_required
def document_achat(request, pk):
    """
    Routeur intelligent :
    - Montant < 600 000 F CFA  → Bon d'entrée
    - Montant ≥ 600 000 F CFA  → PV de réception
    """
    achat = get_object_or_404(Achat, pk=pk)
    if achat.total_ttc >= SEUIL_PV_RECEPTION:
        return pv_reception_achat(request, pk)
    return bon_entree_achat(request, pk)


@staff_member_required
def bon_entree_modele1_achat(request, pk):
    from decimal import Decimal
    achat = get_object_or_404(Achat, pk=pk)
    lignes_qs = achat.lignes.select_related(
        'matiere__sous_compte', 'matiere__unite'
    ).all()
    
    lignes = []
    total_qte = Decimal(0)
    total_montant = Decimal(0)
    
    for ligne in lignes_qs:
        mat = ligne.matiere
        qte = ligne.quantite or Decimal(0)
        mnt = ligne.total_ligne_ht or Decimal(0)
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
            "num_bon_commande": achat.numero_facture or "",
            "observations": ligne.appreciation or "",
        })
    
    # Lignes vides pour remplissage du formulaire (minimum 8 lignes)
    nb_lignes = len(lignes)
    empty_count = max(0, 8 - nb_lignes)
    
    context = {
        "numero_bon": achat.code,
        "annee": achat.date_achat.year if achat.date_achat else "—",
        "date_doc": achat.date_achat.strftime("%d/%m/%Y") if achat.date_achat else "—",
        "type_entree": "Achat",
        "source_label": str(achat.fournisseur) if achat.fournisseur else "—",
        "reference": achat.numero_facture or "",
        "etablissement": "École normale supérieure des mines et de la géologie",
        "depot": achat.depot.nom if achat.depot else "—",
        "lignes": lignes,
        "empty_rows": range(empty_count),
        "total_qte_str": fmt_qte(total_qte),
        "total_montant_str": fmt_montant(total_montant),
    }
    return render_pdf(request, "documents/bon_entree_modele1.html", context,
                      filename=f"bon_entree_{achat.code}.pdf")
