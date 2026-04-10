# documents/views/dotation_views.py
"""
Vues de génération des documents pour les Dotations et Fiches d'affectation.

Bon de dotation              → un seul document présenté au bénéficiaire
                               couvre les deux groupes (consommables + immobilisations)
Fiche d'affectation          → document individuel par bien (1er groupe)
                               retrace la chaîne de garde du bien
Fiches affectation (groupées)→ toutes les fiches d'une dotation en un seul PDF
                               généré automatiquement à la validation
"""
from decimal import Decimal
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404
from documents.utils import render_pdf, fmt_montant, fmt_qte


def _build_fa_context(fa):
    """
    Construit le contexte de rendu pour une FicheAffectation.
    Partagé par la vue individuelle et la vue groupée.
    """
    mat   = fa.matiere
    qte   = fa.quantite or Decimal("0")
    prix  = Decimal("0")
    total = Decimal("0")

    if fa.ligne_dotation_id:
        try:
            prix  = fa.ligne_dotation.unit_price  or Decimal("0")
            total = fa.ligne_dotation.total_ligne or Decimal("0")
        except Exception:
            pass

    if total == Decimal("0") and fa.mouvement_stock_id:
        try:
            mvt   = fa.mouvement_stock
            prix  = mvt.cout_unitaire or Decimal("0")
            total = mvt.cout_total    or Decimal("0")
        except Exception:
            pass

    return {
        "numero_fa":     fa.code,
        "date_doc":      fa.date_affectation,
        "statut":        fa.get_statut_display(),
        "code_matiere":  mat.code_court if hasattr(mat, "code_court") else "",
        "designation":   mat.designation,
        "sous_compte":   str(mat.sous_compte) if mat.sous_compte else "—",
        "unite":         mat.unite.libelle if mat.unite else "unité",
        "quantite":      fmt_qte(qte),
        "prix_unitaire": fmt_montant(prix),
        "valeur_totale": fmt_montant(total),
        "beneficiaire":  fa.beneficiaire,
        "service":       str(fa.service) if fa.service else "—",
        "depot_source":  str(fa.depot) if fa.depot else "—",
        "dotation_code": str(fa.dotation) if fa.dotation else "—",
        "dotation_date": fa.dotation.date.strftime("%d/%m/%Y") if fa.dotation and fa.dotation.date else "—",
        "observations":  fa.observations or "",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Bon de dotation (Dotation)
# ─────────────────────────────────────────────────────────────────────────────

@staff_member_required
def bon_dotation(request, pk):
    """
    Bon de dotation — document unique remis au bénéficiaire.

    Toutes les lignes sont présentées dans un tableau unique.
    Chaque ligne indique son groupe (1er / 2e) pour distinguer
    les affectations des sorties définitives.
    """
    from purchasing.models.dotation import Dotation

    dotation = get_object_or_404(
        Dotation.objects.select_related("depot", "service").prefetch_related(
            "lignes__matiere__unite",
            "lignes__matiere__sous_compte",
        ),
        pk=pk,
    )

    lignes_data = []
    total_valeur = Decimal("0")

    for ligne in dotation.lignes.all():
        mat    = ligne.matiere
        qte    = ligne.quantity  or Decimal("0")
        prix   = ligne.unit_price or Decimal("0")
        total  = ligne.total_ligne or Decimal("0")
        is_immo = (mat.type_matiere == "reutilisable")

        total_valeur += total

        lignes_data.append({
            "code":        mat.code_court if hasattr(mat, "code_court") else (mat.code if hasattr(mat, "code") else ""),
            "designation": mat.designation,
            "groupe":      "1er groupe (durables)" if is_immo else "2e groupe (consomm.)",
            "is_immo":     is_immo,
            "unite":       mat.unite.abreviation if mat.unite else "u",
            "quantite":    fmt_qte(qte),
            "prix_unit":   fmt_montant(prix),
            "total":       fmt_montant(total),
            "note":        ligne.note or "",
        })

    context = {
        # En-tête document
        "numero_bon":   dotation.code,
        "date_doc":     dotation.date,
        # Bénéficiaire
        "beneficiaire": dotation.beneficiaire,
        "service":      str(dotation.service) if dotation.service else "—",
        "depot":        str(dotation.depot) if dotation.depot else "—",
        # Référence
        "document_ref": dotation.document_number or "—",
        "type_dotation": dotation.get_type_dotation_display() if dotation.type_dotation else "—",
        "observations": dotation.comment or "",
        # Lignes
        "lignes":       lignes_data,
        "nb_lignes":    len(lignes_data),
        # Totaux
        "total_valeur_str": fmt_montant(total_valeur),
        # Lignes vides pour compléter le tableau (minimum 6 lignes)
        "empty_rows":   range(max(0, 6 - len(lignes_data))),
    }

    return render_pdf(
        request,
        "documents/bon_dotation.html",
        context,
        filename=f"bon_dotation_{dotation.code}.pdf",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Fiche d'affectation (FicheAffectation)
# ─────────────────────────────────────────────────────────────────────────────

@staff_member_required
def fiche_affectation_document(request, pk):
    """
    Fiche d'affectation — document individuel pour chaque bien immobilisé
    distribué via une dotation (1er groupe).

    Retrace la chaîne de garde : qui détient quel bien, depuis quand,
    issu de quelle dotation.
    """
    from inventory.models import FicheAffectation

    fa = get_object_or_404(
        FicheAffectation.objects.select_related(
            "matiere__unite", "matiere__sous_compte",
            "depot", "service", "dotation",
        ),
        pk=pk,
    )

    context = _build_fa_context(fa)

    return render_pdf(
        request,
        "documents/fiche_affectation.html",
        context,
        filename=f"fiche_affectation_{fa.code}.pdf",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Toutes les fiches d'affectation d'une dotation (PDF multi-pages)
# ─────────────────────────────────────────────────────────────────────────────

@staff_member_required
def fiches_affectation_dotation(request, pk):
    """
    Génère un PDF contenant TOUTES les fiches d'affectation d'une dotation.

    Une fiche par page (saut de page entre chaque).
    Destiné à être imprimé immédiatement après la validation d'une dotation
    1er groupe ou mixte.

    Si la dotation ne contient aucune fiche d'affectation (2e groupe pur),
    retourne une page d'information.
    """
    from purchasing.models.dotation import Dotation
    from inventory.models import FicheAffectation

    dotation = get_object_or_404(
        Dotation.objects.select_related("depot", "service"),
        pk=pk,
    )

    fas = (
        FicheAffectation.objects
        .filter(dotation=dotation)
        .select_related(
            "matiere__unite", "matiere__sous_compte",
            "depot", "service", "dotation",
            "ligne_dotation", "mouvement_stock",
        )
        .order_by("code")
    )

    fiches = [_build_fa_context(fa) for fa in fas]

    context = {
        "dotation_code":  dotation.code,
        "dotation_date":  dotation.date.strftime("%d/%m/%Y") if dotation.date else "—",
        "beneficiaire":   dotation.beneficiaire,
        "service":        str(dotation.service) if dotation.service else "—",
        "depot":          str(dotation.depot) if dotation.depot else "—",
        "nb_fiches":      len(fiches),
        "fiches":         fiches,
    }

    return render_pdf(
        request,
        "documents/fiches_affectation_dotation.html",
        context,
        filename=f"fiches_affectation_{dotation.code}.pdf",
    )
