# documents/views/registres_views.py
"""
Vues pour les registres comptables officiels :
- Livre journal (chronologique)
- Grand livre (par compte)
- Balance générale
"""
from decimal import Decimal
from django.http import JsonResponse
from django.db import models
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, render as render_to_response
from django.utils import timezone

from django.contrib import admin as django_admin

from documents.utils import render_pdf
from core.models import Exercice
from inventory.models import MouvementStock
from catalog.models import Matiere
from catalog.models.compte import ComptePrincipal, CompteDivisionnaire, SousCompte


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _libelle_mouvement(m) -> str:
    """Génère un libellé lisible pour un MouvementStock."""
    labels = {
        "ENTREE": "Entrée en stock",
        "SORTIE": "Sortie de stock",
        "TRANSFERT": "Transfert inter-dépôts",
        "AJUSTEMENT": "Ajustement de stock",
    }
    base = labels.get(m.type, m.type)
    if m.reference:
        base += f" — {m.reference}"
    if m.matiere:
        base += f" ({m.matiere.code_court})"
    return base


def _compte_code_for_mouvement(m) -> str:
    """Retourne le code du sous-compte de la matière."""
    try:
        return m.matiere.sous_compte.code
    except AttributeError:
        return "—"


# ─────────────────────────────────────────────────────────────
# Livre Journal
# ─────────────────────────────────────────────────────────────

@staff_member_required
def livre_journal(request, exercice_pk=None):
    if exercice_pk:
        exercice = get_object_or_404(Exercice, pk=exercice_pk)
    else:
        exercice = Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()

    mouvements_qs = (
        MouvementStock.objects.filter(exercice=exercice)
        .select_related("matiere__sous_compte", "matiere__unite", "depot")
        .order_by("date", "pk")
    )

    lignes = []
    total_debits  = Decimal("0")
    total_credits = Decimal("0")

    for m in mouvements_qs:
        valeur = m.cout_total or Decimal("0")
        qte    = m.quantite or Decimal("0")
        pu     = m.cout_unitaire or Decimal("0")
        try:
            unite_str = str(m.matiere.unite) if m.matiere.unite else "—"
        except AttributeError:
            unite_str = "—"

        # Convention CDM : ENTREE = colonne Entrées, SORTIE/TRANSFERT = colonne Sorties
        if m.type in ("ENTREE", "AJUSTEMENT"):
            debit, credit = valeur, None
            qte_entree, qte_sortie = qte, None
            total_debits += valeur
        else:
            debit, credit = None, valeur
            qte_entree, qte_sortie = None, qte
            total_credits += valeur

        lignes.append({
            "date":          m.date,
            "reference":     m.reference or f"{m.type}-{m.pk}",
            "libelle":       _libelle_mouvement(m),
            "compte_code":   _compte_code_for_mouvement(m),
            "unite":         unite_str,
            "cout_unitaire": pu,
            "qte_entree":    qte_entree,
            "qte_sortie":    qte_sortie,
            "debit":         debit,
            "credit":        credit,
        })

    context = {
        "exercice": exercice,
        "lignes": lignes,
        "total_lignes": len(lignes),
        "total_debits": total_debits,
        "total_credits": total_credits,
        "date_doc": timezone.now().date(),
        "exercice_label": exercice.code if exercice else "",
    }
    return render_pdf(
        request,
        "documents/livre_journal.html",
        context,
        filename=f"livre_journal_{exercice.code if exercice else 'all'}.pdf",
    )


# ─────────────────────────────────────────────────────────────
# HELPERS Grand Livre
# ─────────────────────────────────────────────────────────────

def _origine_libelle(m):
    """Libellé d'origine/destination pour le Grand Livre (colonne 3)."""
    src = m.source_doc_type or ""
    ref = m.reference or ""
    com = m.commentaire or ""

    if "LigneAchat" in src or "Achat" in src:
        base = "Achat"
        if ref: base += f" — {ref}"
    elif "ExternalStockEntry" in src:
        base = "Entrée externe"
        if ref: base += f" — {ref}"
    elif "Don" in src or "don" in src:
        base = "Don reçu"
        if ref: base += f" — {ref}"
    elif m.type == "SORTIE":
        base = "Sortie définitive"
        if ref: base += f" — {ref}"
        elif com: base += f" — {com}"
    elif m.type == "TRANSFERT":
        src_d = m.source_depot.nom if m.source_depot else "?"
        dst_d = m.destination_depot.nom if m.destination_depot else "?"
        base = f"Transfert {src_d} → {dst_d}"
    elif m.type == "AJUSTEMENT":
        base = "Ajustement d'inventaire"
        if ref: base += f" — {ref}"
    else:
        base = m.type
        if ref: base += f" — {ref}"

    if m.type in ("ENTREE", "AJUSTEMENT") and m.depot:
        base += f" ({m.depot.nom})"
    elif m.type == "SORTIE" and m.depot:
        base += f" ({m.depot.nom})"

    return base


def _build_gl_lignes(matiere, exercice):
    """
    Construit les lignes du Grand Livre pour une matière + exercice donnés.
    Retourne un dict avec si_*, lignes, totaux, solde_final.
    """
    from inventory.models import StockCourant
    from purchasing.models import LignePret

    # ── 1. Stock initial ───────────────────────────────────────
    si_qte = Decimal("0")
    si_val = Decimal("0")
    for sc in StockCourant.objects.filter(exercice=exercice, matiere=matiere):
        si_qte += sc.stock_initial_qte or Decimal("0")
        si_val += (sc.stock_initial_qte or Decimal("0")) * (sc.stock_initial_cu or Decimal("0"))
    si_cu = (si_val / si_qte) if si_qte else Decimal("0")

    # ── 2. Mouvements chronologiques ──────────────────────────
    mvts = (
        MouvementStock.objects
        .filter(exercice=exercice, matiere=matiere)
        .select_related("depot", "source_depot", "destination_depot")
        .order_by("date", "pk")
    )

    # ── 3. Prêts actifs (pour mémoire) ────────────────────────
    # Map: (pret_id, date_pret) -> {qte, code_pret}
    prets_actifs = {}
    for lp in LignePret.objects.filter(matiere=matiere, pret__est_clos=False).select_related("pret"):
        key = lp.pret.pk
        if key not in prets_actifs:
            prets_actifs[key] = {
                "date": lp.pret.date_pret,
                "code": lp.pret.code,
                "qte": Decimal("0"),
            }
        prets_actifs[key]["qte"] += lp.quantite or Decimal("0")

    # ── 4. Construire les lignes ──────────────────────────────
    lignes = []
    num = 0
    ex_qte  = si_qte
    ex_cump = si_cu
    ex_val  = si_val

    total_ent_qte      = Decimal("0")
    total_sor_def_qte  = Decimal("0")
    total_sor_prov_qte = Decimal("0")

    for m in mvts:
        if m.is_stock_initial:
            continue  # La ligne SI est affichée séparément

        num += 1
        qte = Decimal(m.quantite or 0)
        pu  = Decimal(m.cout_unitaire or 0)

        ent_qte = sor_def_qte = sor_prov_qte = None
        date_retour = None

        if m.type in ("ENTREE", "AJUSTEMENT"):
            ent_qte = qte
            total_ent_qte += qte
            new_qte = ex_qte + qte
            if new_qte > 0:
                ex_cump = ((ex_qte * ex_cump) + (qte * pu)) / new_qte
            ex_qte = new_qte
            ex_val = ex_qte * ex_cump

        elif m.type == "SORTIE":
            sor_def_qte = qte
            total_sor_def_qte += qte
            ex_qte = max(Decimal("0"), ex_qte - qte)
            ex_val = ex_qte * ex_cump

        elif m.type == "TRANSFERT":
            # Le stock total de la matière ne change pas ; afficher comme info
            ent_qte     = qte   # entre dans le dépôt dest
            sor_def_qte = qte   # sort du dépôt src

        lignes.append({
            "num":           num,
            "date":          m.date,
            "piece":         m.reference or f"N°{m.pk:04d}",
            "libelle":       _origine_libelle(m),
            "is_initial":    False,
            "ent_qte":       ent_qte,
            "sor_def_qte":   sor_def_qte,
            "sor_prov_qte":  sor_prov_qte,
            "date_retour":   date_retour,
            "ex_qte":        ex_qte,
            "ex_cump":       ex_cump,
            "ex_val":        ex_val,
        })

    # ── 5. Insérer les lignes prêts (pour mémoire) ────────────
    for p in sorted(prets_actifs.values(), key=lambda x: x["date"]):
        num += 1
        total_sor_prov_qte += p["qte"]
        lignes.append({
            "num":           num,
            "date":          p["date"],
            "piece":         p["code"],
            "libelle":       f"Prêt provisoire — {p['code']}",
            "is_initial":    False,
            "ent_qte":       None,
            "sor_def_qte":   None,
            "sor_prov_qte":  p["qte"],
            "date_retour":   None,
            "ex_qte":        ex_qte,   # existant inchangé (mémoire seulement)
            "ex_cump":       ex_cump,
            "ex_val":        ex_val,
        })
    # Re-trier par date (normaliser datetime → date pour comparaison)
    def _sort_key(x):
        d = x["date"]
        if hasattr(d, "date"):
            d = d.date()
        return (d, x["num"])
    lignes.sort(key=_sort_key)

    return {
        "si_date":           exercice.date_debut if exercice else timezone.now().date(),
        "si_qte":            si_qte,
        "si_pu":             si_cu,
        "si_val":            si_val,
        "lignes":            lignes,
        "total_ent_qte":     total_ent_qte,
        "total_sor_def_qte": total_sor_def_qte,
        "total_sor_prov_qte":total_sor_prov_qte,
        "solde_final_qte":   ex_qte,
        "solde_final_cump":  ex_cump,
        "solde_final_val":   ex_val,
    }


# ─────────────────────────────────────────────────────────────
# Grand Livre des Matières — Index (page HTML admin)
# ─────────────────────────────────────────────────────────────

@staff_member_required
def grand_livre(request, exercice_pk=None):
    """
    Page HTML : liste de toutes les matières, cliquable → GL de la matière.
    Bouton 'Grand Livre des Matières Complet'.
    """
    from django.db.models import Count, Sum as DSum
    from inventory.models import StockCourant

    exercice_id = request.GET.get("exercice") or exercice_pk
    exercice = (
        get_object_or_404(Exercice, pk=exercice_id) if exercice_id
        else Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
    )
    exercices = Exercice.objects.order_by("-annee")

    stock_map = {
        s["matiere_id"]: s["total_qte"]
        for s in StockCourant.objects.filter(exercice=exercice)
        .values("matiere_id").annotate(total_qte=DSum("quantite"))
    }
    mvt_map = {
        m["matiere_id"]: m["cnt"]
        for m in MouvementStock.objects.filter(exercice=exercice)
        .values("matiere_id").annotate(cnt=Count("id"))
    }

    rows = []
    for mat in Matiere.objects.select_related("sous_compte", "unite").order_by("code_court"):
        qte = stock_map.get(mat.pk, Decimal("0")) or Decimal("0")
        nb  = mvt_map.get(mat.pk, 0)
        url = (
            f"/documents/grand-journal/matiere/{mat.pk}/"
            f"?exercice={exercice.pk}"
        )
        type_code = (mat.type_matiere or "")[:1].upper()  # C or R
        type_label = (
            '<span class="type-badge type-C">Consomptible</span>' if type_code == "C"
            else '<span class="type-badge type-R">Durable</span>' if type_code == "R"
            else mat.type_matiere or "—"
        )
        stock_str = f"{int(qte):,}" if qte == int(qte) else f"{float(qte):.2f}"
        mvt_pill = (
            f'<span class="mvt-pill has">{nb}</span>' if nb > 0
            else '<span class="mvt-pill none">0</span>'
        )
        rows.append({
            "url":          url,
            "search_text":  f"{mat.code_court} {mat.designation}",
            "type_filter":  type_code,
            "cells": [
                {"html": f'<span class="code-badge">{mat.code_court}</span>'},
                {"html": mat.designation},
                {"html": type_label, "center": True},
                {"html": str(mat.unite) if mat.unite else "—", "center": True},
                {"html": stock_str, "right": True},
                {"html": mvt_pill, "center": True},
            ],
        })

    return render_to_response(request, "documents/grand_livre_index.html", {
        **django_admin.site.each_context(request),
        "titre_page":   "Grand Journal des Matières",
        "title":        "Grand Journal des Matières",
        "description":  "Liste de toutes les matières de l'exercice.",
        "exercice":     exercice,
        "exercices":    exercices,
        "rows":         rows,
        "nb_avec":      sum(1 for nb in mvt_map.values() if nb > 0),
        "colonnes": [
            {"label": "Code",          "width": "90px"},
            {"label": "Désignation"},
            {"label": "Type",          "width": "110px"},
            {"label": "Unité",         "width": "70px"},
            {"label": "Stock actuel",  "width": "90px",  "right": True},
            {"label": "Mouvements",    "width": "90px"},
        ],
        "url_complet":   "/documents/grand-journal/complet/",
        "label_complet": "Grand Journal des Matières Complet",
        "type_filter":   True,
    })


# ─────────────────────────────────────────────────────────────
# Grand Livre par Matière — PDF Modèle N°7
# ─────────────────────────────────────────────────────────────

@staff_member_required
def grand_livre_par_matiere(request, matiere_pk, exercice_pk=None):
    matiere  = get_object_or_404(Matiere, pk=matiere_pk)
    exercice_id = request.GET.get("exercice") or exercice_pk
    exercice = (
        get_object_or_404(Exercice, pk=exercice_id) if exercice_id
        else Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
    )

    data = _build_gl_lignes(matiere, exercice)

    # Entête droite selon format CDM
    unite_str = str(matiere.unite) if getattr(matiere, "unite", None) else "—"
    try:
        compte_code = matiere.sous_compte.code
    except AttributeError:
        compte_code = matiere.code_court

    context = {
        "titre_doc":    "GRAND JOURNAL DES MATIÈRES",
        "modele_ref":   "Modèle N°7 — Art. 18a",
        "entete_droite": [
            ("Nature de l'unité", unite_str),
            ("Compte N°",         compte_code),
            ("Intitulé",          matiere.designation),
            ("Exercice",          str(exercice.annee) if exercice else "—"),
        ],
        "exercice":          exercice,
        "exercice_label":    exercice.code if exercice else "",
        "date_doc":          timezone.now().date(),
        **data,
    }
    return render_pdf(
        request, "documents/grand_livre.html", context,
        filename=f"GJ_mat_{matiere.code_court}_{exercice.code if exercice else 'all'}.pdf",
    )


# ─────────────────────────────────────────────────────────────
# Grand Livre des Matières Complet — toutes matières, PDF
# ─────────────────────────────────────────────────────────────

@staff_member_required
def grand_livre_matieres_complet(request, exercice_pk=None):
    exercice_id = request.GET.get("exercice") or exercice_pk
    exercice = (
        get_object_or_404(Exercice, pk=exercice_id) if exercice_id
        else Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
    )

    # Construire un document multi-matières : une section par matière
    sections = []
    for mat in Matiere.objects.select_related("sous_compte", "unite").order_by("code_court"):
        data = _build_gl_lignes(mat, exercice)
        unite_str = str(mat.unite) if getattr(mat, "unite", None) else "—"
        try:
            compte_code = mat.sous_compte.code
        except AttributeError:
            compte_code = mat.code_court
        sections.append({
            "matiere": mat,
            "unite_str": unite_str,
            "compte_code": compte_code,
            **data,
        })

    context = {
        "titre_doc":      "GRAND JOURNAL DES MATIÈRES",
        "modele_ref":     "Modèle N°7 — Art. 18a (complet)",
        "exercice":       exercice,
        "exercice_label": exercice.code if exercice else "",
        "date_doc":       timezone.now().date(),
        "sections":       sections,
        "is_complet":     True,
    }
    return render_pdf(
        request, "documents/grand_livre_complet.html", context,
        filename=f"GJ_complet_{exercice.code if exercice else 'all'}.pdf",
    )


# ─────────────────────────────────────────────────────────────
# Grand Livre des Comptes — Index (page HTML admin)
# ─────────────────────────────────────────────────────────────

@staff_member_required
def grand_livre_comptes(request, exercice_pk=None):
    """
    Page HTML : liste des sous-comptes avec leurs matières,
    cliquable → GL du sous-compte.
    Bouton 'Grand Livre des Comptes Complet'.
    """
    from django.db.models import Count

    exercice_id = request.GET.get("exercice") or exercice_pk
    exercice = (
        get_object_or_404(Exercice, pk=exercice_id) if exercice_id
        else Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
    )
    exercices = Exercice.objects.order_by("-annee")

    # Nb mouvements par sous-compte (via matiere__sous_compte)
    mvt_qs = (
        MouvementStock.objects.filter(exercice=exercice)
        .values("matiere__sous_compte_id")
        .annotate(cnt=Count("id"))
    )
    sc_mvt_map = {m["matiere__sous_compte_id"]: m["cnt"] for m in mvt_qs}

    rows = []
    nb_avec = 0

    # Hierarchie : CP > CD > SC
    for cp in ComptePrincipal.objects.order_by("code"):
        for cd in CompteDivisionnaire.objects.filter(compte_principal=cp).order_by("code"):
            for sc in SousCompte.objects.filter(compte_divisionnaire=cd).order_by("code"):
                nb_mats = Matiere.objects.filter(sous_compte=sc).count()
                nb_mvt  = sc_mvt_map.get(sc.pk, 0)
                url = f"/documents/grand-livre-comptes/sous-compte/{sc.pk}/?exercice={exercice.pk}"

                mvt_pill = (
                    f'<span class="mvt-pill has">{nb_mvt}</span>' if nb_mvt > 0
                    else '<span class="mvt-pill none">0</span>'
                )
                hier = (
                    f'<span style="color:#9ca3af;font-size:11px;">'
                    f'{cp.code} › {cd.code}</span>'
                )

                rows.append({
                    "url":         url,
                    "search_text": f"{sc.code} {sc.libelle} {cp.libelle} {cd.libelle}",
                    "type_filter": None,
                    "cells": [
                        {"html": f'<span class="code-badge compte">{sc.code}</span>'},
                        {"html": sc.libelle},
                        {"html": hier},
                        {"html": str(nb_mats) if nb_mats else '<span style="color:#9ca3af">0</span>', "center": True},
                        {"html": mvt_pill, "center": True},
                    ],
                })
                if nb_mvt > 0:
                    nb_avec += 1

    return render_to_response(request, "documents/grand_livre_index.html", {
        **django_admin.site.each_context(request),
        "titre_page":   "Grand Livre des Comptes",
        "title":        "Grand Livre des Comptes",
        "description":  "Liste des sous-comptes de la nomenclature.",
        "exercice":     exercice,
        "exercices":    exercices,
        "rows":         rows,
        "nb_avec":      nb_avec,
        "colonnes": [
            {"label": "Compte N°",    "width": "100px"},
            {"label": "Intitulé"},
            {"label": "Hiérarchie",   "width": "160px"},
            {"label": "Matières",     "width": "70px"},
            {"label": "Mouvements",   "width": "90px"},
        ],
        "url_complet":   "/documents/grand-livre-comptes/complet/",
        "label_complet": "Grand Livre des Comptes Complet",
        "type_filter":   False,
    })


# ─────────────────────────────────────────────────────────────
# Grand Livre par Compte (SousCompte) — PDF Modèle N°7
# ─────────────────────────────────────────────────────────────

@staff_member_required
def grand_livre_par_compte(request, sc_pk, exercice_pk=None):
    sc = get_object_or_404(SousCompte, pk=sc_pk)
    exercice_id = request.GET.get("exercice") or exercice_pk
    exercice = (
        get_object_or_404(Exercice, pk=exercice_id) if exercice_id
        else Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
    )

    # Toutes les matières de ce sous-compte
    matieres = Matiere.objects.filter(sous_compte=sc).order_by("code_court")

    # Construire les lignes pour TOUTES les matières, triées chronologiquement
    all_lignes = []
    si_qte = si_val = si_cu = Decimal("0")
    total_ent = total_sor_def = total_sor_prov = Decimal("0")
    ex_qte = ex_cump = ex_val = Decimal("0")

    for mat in matieres:
        data = _build_gl_lignes(mat, exercice)
        si_qte += data["si_qte"]
        si_val += data["si_val"]
        for l in data["lignes"]:
            # Préfixer le libellé avec le code matière
            l["libelle"] = f"[{mat.code_court}] {l['libelle']}"
            all_lignes.append(l)
        total_ent     += data["total_ent_qte"]
        total_sor_def += data["total_sor_def_qte"]
        total_sor_prov+= data["total_sor_prov_qte"]
        ex_qte  = data["solde_final_qte"]
        ex_cump = data["solde_final_cump"]
        ex_val  = data["solde_final_val"]

    si_cu = (si_val / si_qte) if si_qte else Decimal("0")
    def _sk_compte(x):
        d = x["date"]
        if hasattr(d, "date"): d = d.date()
        return (d, x["num"])
    all_lignes.sort(key=_sk_compte)
    # Renuméroter
    for i, l in enumerate(all_lignes, 1):
        l["num"] = i

    try:
        cp_code = sc.compte_divisionnaire.compte_principal.code
    except AttributeError:
        cp_code = "—"

    context = {
        # Variables pour le template grand_livre_compte.html (Modèle N°7 exact)
        "nature_unite":   f"{matieres.count()} matière(s)",
        "compte_code":    sc.code,
        "intitule":       sc.libelle,
        "exercice":       exercice,
        "exercice_label": exercice.code if exercice else "",
        "date_doc":       timezone.now().date(),
        "si_date":        exercice.date_debut if exercice else timezone.now().date(),
        "si_qte":         si_qte,
        "si_pu":          si_cu,
        "si_val":         si_val,
        "lignes":         all_lignes,
        "total_ent_qte":     total_ent,
        "total_sor_def_qte": total_sor_def,
        "total_sor_prov_qte":total_sor_prov,
        "solde_final_qte":   ex_qte,
        "solde_final_cump":  ex_cump,
        "solde_final_val":   ex_val,
    }
    return render_pdf(
        request, "documents/grand_livre_compte.html", context,
        filename=f"GL_compte_{sc.code}_{exercice.code if exercice else 'all'}.pdf",
    )


# ─────────────────────────────────────────────────────────────
# Grand Livre des Comptes Complet — tous sous-comptes, PDF
# ─────────────────────────────────────────────────────────────

@staff_member_required
def grand_livre_comptes_complet(request, exercice_pk=None):
    exercice_id = request.GET.get("exercice") or exercice_pk
    exercice = (
        get_object_or_404(Exercice, pk=exercice_id) if exercice_id
        else Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
    )

    sections = []
    for cp in ComptePrincipal.objects.order_by("code"):
        for cd in CompteDivisionnaire.objects.filter(compte_principal=cp).order_by("code"):
            for sc in SousCompte.objects.filter(compte_divisionnaire=cd).order_by("code"):
                matieres = Matiere.objects.filter(sous_compte=sc).order_by("code_court")
                if not matieres.exists():
                    continue
                all_lignes = []
                si_qte = si_val = Decimal("0")
                total_ent = total_sor_def = total_sor_prov = Decimal("0")
                ex_qte = ex_cump = ex_val = Decimal("0")
                for mat in matieres:
                    data = _build_gl_lignes(mat, exercice)
                    si_qte += data["si_qte"]
                    si_val += data["si_val"]
                    for l in data["lignes"]:
                        l["libelle"] = f"[{mat.code_court}] {l['libelle']}"
                        all_lignes.append(l)
                    total_ent     += data["total_ent_qte"]
                    total_sor_def += data["total_sor_def_qte"]
                    total_sor_prov+= data["total_sor_prov_qte"]
                    ex_qte  = data["solde_final_qte"]
                    ex_cump = data["solde_final_cump"]
                    ex_val  = data["solde_final_val"]
                def _sk(x):
                    d = x["date"]
                    if hasattr(d, "date"): d = d.date()
                    return (d, x["num"])
                all_lignes.sort(key=_sk)
                for i, l in enumerate(all_lignes, 1):
                    l["num"] = i
                si_cu = (si_val / si_qte) if si_qte else Decimal("0")
                sections.append({
                    "sc": sc, "cp": cp, "cd": cd,
                    "si_date":  exercice.date_debut if exercice else timezone.now().date(),
                    "si_qte": si_qte, "si_pu": si_cu, "si_val": si_val,
                    "lignes": all_lignes,
                    "total_ent_qte": total_ent,
                    "total_sor_def_qte": total_sor_def,
                    "total_sor_prov_qte": total_sor_prov,
                    "solde_final_qte": ex_qte,
                    "solde_final_cump": ex_cump,
                    "solde_final_val": ex_val,
                })

    context = {
        "titre_doc":      "GRAND LIVRE DES COMPTES",
        "modele_ref":     "Modèle N°7 — Art. 18a (complet)",
        "exercice":       exercice,
        "exercice_label": exercice.code if exercice else "",
        "date_doc":       timezone.now().date(),
        "sections":       sections,
        "is_complet":     True,
    }
    return render_pdf(
        request, "documents/grand_livre_comptes_complet.html", context,
        filename=f"GL_comptes_complet_{exercice.code if exercice else 'all'}.pdf",
    )



# ─────────────────────────────────────────────────────────────
# Balance Générale
# ─────────────────────────────────────────────────────────────

@staff_member_required
def balance_generale(request, exercice_pk=None):
    if exercice_pk:
        exercice = get_object_or_404(Exercice, pk=exercice_pk)
    else:
        exercice = Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()

    from django.db.models import Sum
    from inventory.models import StockCourant

    # Agréger les mouvements par sous-compte
    mouvements_qs = (
        MouvementStock.objects.filter(exercice=exercice)
        .select_related(
            "matiere__sous_compte__compte_divisionnaire__compte_principal"
        )
    )

    # Structure : {sc_pk: {solde_initial, entrees, sorties}}
    sc_totaux = {}

    for m in mouvements_qs:
        try:
            sc = m.matiere.sous_compte
            cd = sc.compte_divisionnaire
            cp = cd.compte_principal
        except AttributeError:
            continue

        valeur = m.cout_total or Decimal("0")

        key = (cp.code, cp.libelle, cd.code, cd.libelle, sc.code, sc.libelle)
        if key not in sc_totaux:
            sc_totaux[key] = {
                "cp_code": cp.code, "cp_lib": cp.libelle,
                "cd_code": cd.code, "cd_lib": cd.libelle,
                "sc_code": sc.code, "sc_lib": sc.libelle,
                "solde_initial": Decimal("0"),
                "total_entrees": Decimal("0"),
                "total_sorties": Decimal("0"),
            }

        if m.is_stock_initial:
            sc_totaux[key]["solde_initial"] += valeur
        elif m.type in ("ENTREE", "AJUSTEMENT"):
            sc_totaux[key]["total_entrees"] += valeur
        else:
            sc_totaux[key]["total_sorties"] += valeur

    # Construire les lignes pour le template (avec en-têtes hiérarchiques)
    lignes = []
    total_si = total_ent = total_sor = Decimal("0")
    prev_cp = prev_cd = None

    for key in sorted(sc_totaux.keys()):
        d = sc_totaux[key]
        cp_code, cd_code = d["cp_code"], d["cd_code"]

        if cp_code != prev_cp:
            lignes.append({
                "is_principal": True,
                "code": d["cp_code"],
                "libelle": d["cp_lib"],
            })
            prev_cp = cp_code
            prev_cd = None

        if cd_code != prev_cd:
            lignes.append({
                "is_divisionnaire": True,
                "code": d["cd_code"],
                "libelle": d["cd_lib"],
            })
            prev_cd = cd_code

        solde_final = d["solde_initial"] + d["total_entrees"] - d["total_sorties"]
        lignes.append({
            "is_principal": False,
            "is_divisionnaire": False,
            "code": d["sc_code"],
            "libelle": d["sc_lib"],
            "solde_initial": d["solde_initial"],
            "total_entrees": d["total_entrees"],
            "total_sorties": d["total_sorties"],
            "solde_final": solde_final,
        })
        total_si += d["solde_initial"]
        total_ent += d["total_entrees"]
        total_sor += d["total_sorties"]

    context = {
        "exercice": exercice,
        "lignes": lignes,
        "total_solde_initial": total_si,
        "total_entrees": total_ent,
        "total_sorties": total_sor,
        "total_solde_final": total_si + total_ent - total_sor,
        "date_doc": timezone.now().date(),
        "exercice_label": exercice.code if exercice else "",
    }
    return render_pdf(
        request,
        "documents/balance_generale.html",
        context,
        filename=f"balance_generale_{exercice.code if exercice else 'all'}.pdf",
    )


# ─────────────────────────────────────────────────────────────
# Relevé Récapitulatif (Modèle n°8)
# ─────────────────────────────────────────────────────────────

@staff_member_required
def releve_recapitulatif(request, exercice_pk=None):
    """
    Relevé récapitulatif des matières — CDM Modèle n°9.
    Par matière : en attente d'affectation / en service / en sortie provisoire / total.
    """
    from django.db.models import Sum
    from inventory.models import StockCourant

    if exercice_pk:
        exercice = get_object_or_404(Exercice, pk=exercice_pk)
    else:
        exercice = Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()

    # Stock courant par matière et dépôt
    stocks_qs = (
        StockCourant.objects
        .filter(exercice=exercice)
        .select_related("matiere__sous_compte", "matiere__unite", "depot")
        .order_by("matiere__sous_compte__code", "matiere__code_court")
    )

    # Agréger par matière (quantité disponible en service, prêts = sortie provisoire)
    # Sorties provisoires (prêts en cours) par matière
    prets_map = {}
    try:
        from purchasing.models import LignePret as LP, Pret
        for lp in LP.objects.filter(pret__exercice=exercice).select_related("matiere"):
            prets_map[lp.matiere_id] = prets_map.get(lp.matiere_id, Decimal("0")) + (lp.quantite or Decimal("0"))
    except Exception:
        pass

    # Regrouper stocks par matière
    mat_map = {}
    for sc in stocks_qs:
        mid = sc.matiere_id
        if mid not in mat_map:
            mat_map[mid] = {
                "matiere": sc.matiere,
                "quantite": Decimal("0"),
            }
        mat_map[mid]["quantite"] += sc.quantite or Decimal("0")

    lignes = []
    tot_en_attente = Decimal("0")
    tot_en_service = Decimal("0")
    tot_prov       = Decimal("0")
    tot_total      = Decimal("0")

    for mid, data in mat_map.items():
        mat = data["matiere"]
        try:
            compte_code = mat.sous_compte.code
        except AttributeError:
            compte_code = "—"

        en_sortie_prov = prets_map.get(mid, Decimal("0"))
        qte_total      = data["quantite"]
        en_service     = max(qte_total - en_sortie_prov, Decimal("0"))
        en_attente     = Decimal("0")  # stocks non encore affectés (simplifié)

        tot_en_attente += en_attente
        tot_en_service += en_service
        tot_prov       += en_sortie_prov
        tot_total      += qte_total

        lignes.append({
            "compte_code":        compte_code,
            "designation":        mat.designation,
            "en_attente":         en_attente,
            "en_service":         en_service,
            "en_sortie_provisoire": en_sortie_prov,
            "total":              qte_total,
            "observations":       "",
        })

    context = {
        "exercice":       exercice,
        "exercice_label": exercice.code if exercice else "",
        "lignes":         lignes,
        "tot_en_attente": tot_en_attente,
        "tot_en_service": tot_en_service,
        "tot_prov":       tot_prov,
        "tot_total":      tot_total,
        "date_doc":       timezone.now().date(),
    }

    return render_pdf(
        request,
        "documents/releve_recapitulatif.html",
        context,
        filename=f"releve_recapitulatif_{exercice.code if exercice else 'all'}.pdf",
    )


# ─────────────────────────────────────────────────────────────
# Procès-Verbal de Réforme
# ─────────────────────────────────────────────────────────────

@staff_member_required
def pv_reforme(request, sortie_pk):
    """
    Procès-verbal de réforme pour une OperationSortie de type REFORME_DESTRUCTION.
    """
    from inventory.models import OperationSortie

    operation = get_object_or_404(OperationSortie, pk=sortie_pk)

    if operation.type_sortie != OperationSortie.TypeSortie.REFORME_DESTRUCTION:
        return JsonResponse({"error": "Cette opération n'est pas une réforme/destruction"}, status=400)

    lignes_qs = operation.lignes.select_related("matiere__unite", "matiere__sous_compte")

    lignes = []
    for ligne in lignes_qs:
        unite_str = "—"
        try:
            if ligne.matiere.unite:
                unite_str = ligne.matiere.unite.symbole or str(ligne.matiere.unite)
        except AttributeError:
            pass
        try:
            compte_code = ligne.matiere.sous_compte.code
        except AttributeError:
            compte_code = "—"
        lignes.append({
            "code_court":    ligne.matiere.code_court,
            "designation":   ligne.matiere.designation,
            "quantite":      ligne.quantite or Decimal("0"),
            "unite":         unite_str,
            "prix_unitaire": ligne.prix_unitaire or Decimal("0"),
            "total_ligne":   ligne.total_ligne or Decimal("0"),
            "commentaire":   ligne.commentaire or "Usure / vétusté",
            "compte_code":   compte_code,
        })

    context = {
        "operation":          operation,
        "operation_code":     operation.code,
        "exercice_label":     str(operation.date_sortie.year) if operation.date_sortie else "—",
        "date_operation":     operation.date_sortie,
        "depot_label":        operation.depot.nom if operation.depot else "—",
        "commission_membres": ["À spécifier"],
        "lignes":             lignes,
        "observations":       operation.commentaire or "Néant",
        "decision":           "À autoriser par la Direction",
        "date_doc":           timezone.now().date(),
    }

    return render_pdf(
        request,
        "documents/pv_reforme.html",
        context,
        filename=f"pv_reforme_{operation.code}.pdf",
    )


# ─────────────────────────────────────────────────────────────
# Fiche Inventaire Individuel (Modèle n°4, Groupe 1)
# ─────────────────────────────────────────────────────────────

@staff_member_required
def fiche_inventaire(request, matiere_pk, exercice_pk=None):
    """
    Fiche inventaire individuelle avec historique des mouvements
    Modèle n°4, Groupe 1
    """
    matiere = get_object_or_404(Matiere, pk=matiere_pk)
    
    if exercice_pk:
        exercice = get_object_or_404(Exercice, pk=exercice_pk)
    else:
        exercice = Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
    
    # Récupérer les mouvements pour cette matière
    mouvements = MouvementStock.objects.filter(
        matiere=matiere,
        exercice=exercice
    ).order_by('date', 'pk').select_related('depot')
    
    historique = []
    solde = 0
    
    for mvt in mouvements:
        if mvt.type == 'ENTREE':
            solde += mvt.quantite
        elif mvt.type == 'SORTIE':
            solde -= mvt.quantite
        
        historique.append({
            'date': mvt.date,
            'type': mvt.type,
            'quantite': mvt.quantite,
            'solde': solde,
            'reference': mvt.reference or f"{mvt.type}-{mvt.pk}",
        })
    
    # Stock actuel
    try:
        from inventory.models import StockCourant
        stock = StockCourant.objects.filter(
            matiere=matiere,
        ).aggregate(total=models.Sum('quantite'))
        stock_actuel = stock['total'] or 0
    except Exception:
        stock_actuel = solde
    
    context = {
        'matiere': matiere,
        'exercice': exercice,
        'exercice_label': exercice.code if exercice else '—',
        'depot_label': 'Tous dépôts',
        'historique': historique,
        'stock_actuel': stock_actuel,
        'observations': f"Matière {matiere.type_matiere}",
        'date_doc': timezone.now().date(),
    }
    
    return render_pdf(
        request,
        "documents/fiche_inventaire.html",
        context,
        filename=f"fiche_inventaire_{matiere.code_court}.pdf",
    )


# ─────────────────────────────────────────────────────────────
# Grand Livre des Journaux — Index + Par journal + Complet
# ─────────────────────────────────────────────────────────────

# Types de journaux reconnus
JOURNAL_TYPES = [
    {"code": "ACHAT",       "label": "Journal des Achats",          "mvt_types": ["ENTREE"], "sources": ["LigneAchat", "Achat"]},
    {"code": "ENTREE_EXT",  "label": "Journal des Entrées Externes", "mvt_types": ["ENTREE"], "sources": ["ExternalStockEntry", "Don"]},
    {"code": "SORTIE",      "label": "Journal des Sorties Définitives", "mvt_types": ["SORTIE"], "sources": []},
    {"code": "MUTATION",    "label": "Journal des Mutations",        "mvt_types": ["TRANSFERT"], "sources": []},
    {"code": "AJUSTEMENT",  "label": "Journal des Ajustements",      "mvt_types": ["AJUSTEMENT"], "sources": []},
]


def _journal_filter_qs(base_qs, journal_code):
    """Filtre un queryset de MouvementStock selon le code journal."""
    jt = next((j for j in JOURNAL_TYPES if j["code"] == journal_code), None)
    if not jt:
        return base_qs.none()
    qs = base_qs.filter(type__in=jt["mvt_types"])
    if jt["sources"]:
        import django.db.models as dm
        q = dm.Q()
        for src in jt["sources"]:
            q |= dm.Q(source_doc_type__icontains=src)
        qs = qs.filter(q)
    elif jt["code"] == "ENTREE_EXT":
        pass  # already filtered above
    elif jt["code"] in ("SORTIE", "MUTATION", "AJUSTEMENT"):
        # Exclude achats (already in ACHAT journal)
        if jt["mvt_types"] == ["ENTREE"]:
            qs = qs.exclude(source_doc_type__icontains="Achat").exclude(source_doc_type__icontains="LigneAchat")
    return qs


def _build_journal_lignes(qs):
    """Construit les lignes pour le document Grand Livre des Journaux."""
    lignes = []
    total_entrees_qte = Decimal("0")
    total_entrees_val = Decimal("0")
    total_sorties_qte = Decimal("0")
    total_sorties_val = Decimal("0")

    for m in qs.select_related("matiere__sous_compte", "depot").order_by("date", "pk"):
        qte = m.quantite or Decimal("0")
        pu  = m.cout_unitaire or Decimal("0")
        val = m.cout_total or (qte * pu)

        if m.type in ("ENTREE", "AJUSTEMENT"):
            ent_qte, ent_val = qte, val
            sor_qte, sor_val = None, None
            total_entrees_qte += qte
            total_entrees_val += val
        else:
            ent_qte, ent_val = None, None
            sor_qte, sor_val = qte, val
            total_sorties_qte += qte
            total_sorties_val += val

        ref = m.reference or f"{m.type}-{m.pk}"
        try:
            compte_code = m.matiere.sous_compte.code
        except AttributeError:
            compte_code = "—"

        lignes.append({
            "date":         m.date,
            "num":          ref,
            "compte":       compte_code,
            "designation":  m.matiere.designation if m.matiere else "—",
            "libelle":      _origine_libelle(m),
            "ent_qte":      ent_qte,
            "ent_val":      ent_val,
            "sor_qte":      sor_qte,
            "sor_val":      sor_val,
            "pu":           pu,
        })

    return {
        "lignes":              lignes,
        "total_entrees_qte":   total_entrees_qte,
        "total_entrees_val":   total_entrees_val,
        "total_sorties_qte":   total_sorties_qte,
        "total_sorties_val":   total_sorties_val,
    }


@staff_member_required
def grand_livre_journaux(request, exercice_pk=None):
    """
    Index HTML : liste des types de journaux avec leur nombre de mouvements.
    """
    from django.db.models import Count, Q as DQ

    exercice_id = request.GET.get("exercice") or exercice_pk
    exercice = (
        get_object_or_404(Exercice, pk=exercice_id) if exercice_id
        else Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
    )
    exercices = Exercice.objects.order_by("-annee")

    base_qs = MouvementStock.objects.filter(exercice=exercice)
    rows = []
    nb_avec = 0

    for jt in JOURNAL_TYPES:
        qs = _journal_filter_qs(base_qs, jt["code"])
        nb = qs.count()
        url = f"/documents/grand-livre-journaux/{jt['code']}/?exercice={exercice.pk}"
        pill = (
            f'<span class="mvt-pill has">{nb}</span>' if nb > 0
            else '<span class="mvt-pill none">0</span>'
        )
        rows.append({
            "url":         url,
            "search_text": jt["label"],
            "type_filter": None,
            "cells": [
                {"html": f'<span class="code-badge compte">{jt["code"]}</span>'},
                {"html": jt["label"]},
                {"html": pill, "center": True},
            ],
        })
        if nb > 0:
            nb_avec += 1

    return render_to_response(request, "documents/grand_livre_index.html", {
        **django_admin.site.each_context(request),
        "titre_page":    "Grand Livre des Journaux",
        "title":         "Grand Livre des Journaux",
        "description":   "Liste des journaux comptables de l'exercice.",
        "exercice":      exercice,
        "exercices":     exercices,
        "rows":          rows,
        "nb_avec":       nb_avec,
        "colonnes": [
            {"label": "Code",          "width": "110px"},
            {"label": "Intitulé du journal"},
            {"label": "Mouvements",    "width": "100px"},
        ],
        "url_complet":   "/documents/grand-livre-journaux/complet/",
        "label_complet": "Grand Livre des Journaux Complet",
        "type_filter":   False,
    })


@staff_member_required
def grand_livre_par_journal(request, journal_code, exercice_pk=None):
    """
    PDF : Grand Livre pour un type de journal donné.
    """
    jt = next((j for j in JOURNAL_TYPES if j["code"] == journal_code), None)
    if not jt:
        from django.http import Http404
        raise Http404("Journal inconnu")

    exercice_id = request.GET.get("exercice") or exercice_pk
    exercice = (
        get_object_or_404(Exercice, pk=exercice_id) if exercice_id
        else Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
    )

    base_qs = MouvementStock.objects.filter(exercice=exercice)
    qs = _journal_filter_qs(base_qs, journal_code)
    data = _build_journal_lignes(qs)

    context = {
        "titre_doc":  f"GRAND LIVRE DES JOURNAUX",
        "sous_titre": jt["label"],
        "modele_ref": "Livre Journal — Art. 18",
        "entete_droite": [
            ("Journal",   jt["label"]),
            ("Exercice",  str(exercice.annee) if exercice else "—"),
        ],
        "exercice":       exercice,
        "exercice_label": exercice.code if exercice else "",
        "date_doc":       timezone.now().date(),
        **data,
    }
    return render_pdf(
        request, "documents/grand_livre_journal.html", context,
        filename=f"GLJ_{journal_code}_{exercice.code if exercice else 'all'}.pdf",
    )


@staff_member_required
def grand_livre_journaux_complet(request, exercice_pk=None):
    """
    PDF : Grand Livre de tous les journaux combinés (une section par journal).
    """
    exercice_id = request.GET.get("exercice") or exercice_pk
    exercice = (
        get_object_or_404(Exercice, pk=exercice_id) if exercice_id
        else Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
    )

    base_qs = MouvementStock.objects.filter(exercice=exercice)
    sections = []
    for jt in JOURNAL_TYPES:
        qs = _journal_filter_qs(base_qs, jt["code"])
        if qs.exists():
            data = _build_journal_lignes(qs)
            sections.append({
                "journal_label": jt["label"],
                "journal_code":  jt["code"],
                **data,
            })

    context = {
        "titre_doc":      "GRAND LIVRE DES JOURNAUX",
        "modele_ref":     "Livre Journal complet — Art. 18",
        "exercice":       exercice,
        "exercice_label": exercice.code if exercice else "",
        "date_doc":       timezone.now().date(),
        "sections":       sections,
    }
    return render_pdf(
        request, "documents/grand_livre_journaux_complet.html", context,
        filename=f"GLJ_complet_{exercice.code if exercice else 'all'}.pdf",
    )


# ─────────────────────────────────────────────────────────────
# Procès-Verbal de Recensement
# ─────────────────────────────────────────────────────────────

@staff_member_required
def pv_recensement(request, exercice_pk=None):
    """
    PV de recensement : état comparatif qté théorique vs qté comptée
    pour toutes les matières d'un exercice.
    """
    from django.db.models import Sum
    from inventory.models import StockCourant

    if exercice_pk:
        exercice = get_object_or_404(Exercice, pk=exercice_pk)
    else:
        exercice = Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()

    # Agréger stock par matière
    stock_map = {}
    for sc in StockCourant.objects.filter(exercice=exercice).select_related("matiere"):
        mid = sc.matiere_id
        if mid not in stock_map:
            stock_map[mid] = Decimal("0")
        stock_map[mid] += sc.quantite or Decimal("0")

    lignes = []
    total_theorique = Decimal("0")

    for mat in Matiere.objects.select_related("sous_compte", "unite").order_by(
        "sous_compte__code", "code_court"
    ):
        try:
            compte_code = mat.sous_compte.code
        except AttributeError:
            compte_code = "—"

        qte_th = stock_map.get(mat.pk, Decimal("0"))
        total_theorique += qte_th

        lignes.append({
            "compte_code":   compte_code,
            "code_court":    mat.code_court,
            "designation":   mat.designation,
            "unite":         str(mat.unite) if mat.unite else "—",
            "qte_theorique": qte_th,
            "ecart":         Decimal("0"),  # à calculer physiquement
        })

    context = {
        "exercice":          exercice,
        "exercice_label":    exercice.code if exercice else "",
        "pv_numero":         f"PVR-{exercice.annee}-001",
        "date_recensement":  timezone.now().date(),
        "depot_label":       "Tous dépôts",
        "commission_membres": [],
        "lignes":            lignes,
        "total_theorique":   total_theorique,
        "observations":      "",
        "date_doc":          timezone.now().date(),
    }
    return render_pdf(
        request,
        "documents/pv_recensement.html",
        context,
        filename=f"pv_recensement_{exercice.code if exercice else 'all'}.pdf",
    )


# ─────────────────────────────────────────────────────────────
# Certificat Administratif
# ─────────────────────────────────────────────────────────────

@staff_member_required
def certificat_administratif(request, sortie_pk):
    """
    Certificat administratif portant autorisation de sortie définitive
    pour une OperationSortie de type CERTIFICAT_ADMIN.
    """
    from inventory.models import OperationSortie

    operation = get_object_or_404(OperationSortie, pk=sortie_pk)
    lignes_qs = operation.lignes.select_related("matiere__unite", "matiere__sous_compte")

    lignes = []
    total_valeur = Decimal("0")

    for ligne in lignes_qs:
        unite_str = "—"
        try:
            if ligne.matiere.unite:
                unite_str = ligne.matiere.unite.symbole or str(ligne.matiere.unite)
        except AttributeError:
            pass
        try:
            compte_code = ligne.matiere.sous_compte.code
        except AttributeError:
            compte_code = "—"
        total_valeur += ligne.total_ligne or Decimal("0")
        lignes.append({
            "code_court":    ligne.matiere.code_court,
            "designation":   ligne.matiere.designation,
            "unite":         unite_str,
            "quantite":      ligne.quantite or Decimal("0"),
            "cout_unitaire": ligne.prix_unitaire or Decimal("0"),
            "cout_total":    ligne.total_ligne or Decimal("0"),
            "compte_code":   compte_code,
        })

    context = {
        "operation":      operation,
        "operation_code": operation.code,
        "exercice_label": str(operation.date_sortie.year) if operation.date_sortie else "—",
        "depot_label":    operation.depot.nom if operation.depot else "—",
        "motif":          operation.motif_principal or operation.get_type_sortie_display(),
        "lignes":         lignes,
        "total_valeur":   total_valeur,
        "observations":   operation.commentaire or "",
        "date_doc":       timezone.now().date(),
    }
    return render_pdf(
        request,
        "documents/certificat_administratif.html",
        context,
        filename=f"certificat_admin_{operation.code}.pdf",
    )


# ─────────────────────────────────────────────────────────────
# Procès-Verbal de Vente ou Destruction
# ─────────────────────────────────────────────────────────────

@staff_member_required
def pv_vente_destruction(request, sortie_pk):
    """
    PV de vente ou destruction pour une OperationSortie de type REFORME_DESTRUCTION
    ou PERTE_VOL_DEFICIT.
    """
    from inventory.models import OperationSortie

    operation = get_object_or_404(OperationSortie, pk=sortie_pk)
    lignes_qs = operation.lignes.select_related("matiere__unite", "matiere__sous_compte")

    lignes = []
    total_valeur = Decimal("0")

    for ligne in lignes_qs:
        unite_str = "—"
        try:
            if ligne.matiere.unite:
                unite_str = ligne.matiere.unite.symbole or str(ligne.matiere.unite)
        except AttributeError:
            pass
        try:
            compte_code = ligne.matiere.sous_compte.code
        except AttributeError:
            compte_code = "—"
        total_valeur += ligne.total_ligne or Decimal("0")
        lignes.append({
            "code_court":    ligne.matiere.code_court,
            "designation":   ligne.matiere.designation,
            "unite":         unite_str,
            "quantite":      ligne.quantite or Decimal("0"),
            "prix_reforme":  ligne.prix_unitaire or Decimal("0"),
            "valeur_totale": ligne.total_ligne or Decimal("0"),
            "compte_code":   compte_code,
            "commentaire":   ligne.commentaire or "Usure / vétusté",
        })

    context = {
        "operation":          operation,
        "operation_code":     operation.code,
        "exercice_label":     str(operation.date_sortie.year) if operation.date_sortie else "—",
        "depot_label":        operation.depot.nom if operation.depot else "—",
        "commission_membres": ["À spécifier"],
        "lignes":             lignes,
        "total_valeur":       total_valeur,
        "mode_sortie":        "DESTRUCTION",   # VENTE | DESTRUCTION | CESSION
        "observations":       operation.commentaire or "",
        "date_doc":           timezone.now().date(),
    }
    return render_pdf(
        request,
        "documents/pv_vente_destruction.html",
        context,
        filename=f"pv_vente_destruction_{operation.code}.pdf",
    )


# ═════════════════════════════════════════════════════════════
# COMPTES DE FIN D'EXERCICE
# ─────────────────────────────────────────────────────────────
# Compte de gestion  (Art. 24-25 Décret 81-844)
# Compte principal   (Art. 26)
# Compte central     (Art. 27)
# ═════════════════════════════════════════════════════════════

def _zero_totaux():
    """Retourne un dict de totaux initialisés à zéro."""
    return {
        "si_qte":  Decimal("0"), "si_val":  Decimal("0"),
        "ent_qte": Decimal("0"), "ent_val": Decimal("0"),
        "sor_qte": Decimal("0"), "sor_val": Decimal("0"),
        "prov_qte": Decimal("0"),
        "sf_qte":  Decimal("0"), "sf_val":  Decimal("0"),
    }


def _add_totaux(dest, ligne):
    """Ajoute les valeurs d'une ligne dans un dict de totaux."""
    for k in dest:
        dest[k] += ligne.get(k, Decimal("0")) or Decimal("0")


def _build_compte_sections(exercice, depot=None):
    """
    Construit les sections hiérarchiques CP > CD > SC > lignes_matière
    pour le Compte de gestion (depot donné) ou Principal/Central (depot=None).

    Retourne : (sections, grand_total)
    """
    from inventory.models import StockCourant
    from purchasing.models import LignePret
    from catalog.models.compte import ComptePrincipal, CompteDivisionnaire, SousCompte
    from django.db.models import Sum

    # ── 1. Stocks initiaux + finaux par (matière, [depot]) ───────────────
    sc_qs = StockCourant.objects.filter(exercice=exercice).select_related(
        "matiere__sous_compte__compte_divisionnaire__compte_principal",
        "matiere__unite",
        "depot",
    )
    if depot:
        sc_qs = sc_qs.filter(depot=depot)

    # Agréger par matière (plusieurs dépôts possibles si depot=None)
    # {matiere_id: {si_qte, si_val, sf_qte, sf_val, cump}}
    stock_by_mat = {}
    for sc in sc_qs:
        mid = sc.matiere_id
        si_qte = sc.stock_initial_qte or Decimal("0")
        si_cu  = sc.stock_initial_cu  or Decimal("0")
        sf_qte = sc.quantite  or Decimal("0")
        sf_cu  = sc.cump      or Decimal("0")
        if mid not in stock_by_mat:
            stock_by_mat[mid] = {
                "matiere": sc.matiere,
                "si_qte":  Decimal("0"),
                "si_val":  Decimal("0"),
                "sf_qte":  Decimal("0"),
                "sf_val":  Decimal("0"),
            }
        stock_by_mat[mid]["si_qte"] += si_qte
        stock_by_mat[mid]["si_val"] += si_qte * si_cu
        stock_by_mat[mid]["sf_qte"] += sf_qte
        stock_by_mat[mid]["sf_val"] += sf_qte * sf_cu

    if not stock_by_mat:
        return [], _zero_totaux()

    # ── 2. Mouvements (entrées + sorties définitives) par matière ────────
    mvt_qs = MouvementStock.objects.filter(exercice=exercice)
    if depot:
        mvt_qs = mvt_qs.filter(depot=depot)

    ent_map = {}  # {matiere_id: (qte, val)}
    for row in mvt_qs.filter(type__in=["ENTREE", "AJUSTEMENT"]).values("matiere_id").annotate(
        tq=Sum("quantite"), tv=Sum("cout_total")
    ):
        ent_map[row["matiere_id"]] = (
            row["tq"] or Decimal("0"),
            row["tv"] or Decimal("0"),
        )

    sor_map = {}  # {matiere_id: (qte, val)}
    for row in mvt_qs.filter(type="SORTIE").values("matiere_id").annotate(
        tq=Sum("quantite"), tv=Sum("cout_total")
    ):
        sor_map[row["matiere_id"]] = (
            row["tq"] or Decimal("0"),
            row["tv"] or Decimal("0"),
        )

    # ── 3. Sorties provisoires (prêts actifs) par matière ────────────────
    pret_qs = LignePret.objects.filter(
        matiere_id__in=list(stock_by_mat.keys()),
        pret__est_clos=False,
    ).values("matiere_id").annotate(tq=Sum("quantite"))
    prov_map = {row["matiere_id"]: row["tq"] or Decimal("0") for row in pret_qs}

    # ── 4. Construire la hiérarchie ───────────────────────────────────────
    sections = []
    grand_total = _zero_totaux()

    for cp in ComptePrincipal.objects.order_by("code"):
        cp_tot = _zero_totaux()
        cds = []

        for cd in CompteDivisionnaire.objects.filter(compte_principal=cp).order_by("code"):
            cd_tot = _zero_totaux()
            scs = []

            for sc in SousCompte.objects.filter(compte_divisionnaire=cd).order_by("code"):
                sc_mats = [
                    v for mid, v in stock_by_mat.items()
                    if v["matiere"].sous_compte_id == sc.pk
                ]
                if not sc_mats:
                    continue

                sc_tot = _zero_totaux()
                lignes = []

                for sd in sorted(sc_mats, key=lambda x: x["matiere"].code_court):
                    mat = sd["matiere"]
                    ent_qte, ent_val = ent_map.get(mat.pk, (Decimal("0"), Decimal("0")))
                    sor_qte, sor_val = sor_map.get(mat.pk, (Decimal("0"), Decimal("0")))
                    prov_qte = prov_map.get(mat.pk, Decimal("0"))
                    unite_str = str(mat.unite) if getattr(mat, "unite", None) else "—"

                    ligne = {
                        "compte_code": sc.code,
                        "code_court":  mat.code_court,
                        "designation": mat.designation,
                        "unite":       unite_str,
                        "si_qte":      sd["si_qte"],
                        "si_val":      sd["si_val"],
                        "ent_qte":     ent_qte,
                        "ent_val":     ent_val,
                        "sor_qte":     sor_qte,
                        "sor_val":     sor_val,
                        "prov_qte":    prov_qte,
                        "sf_qte":      sd["sf_qte"],
                        "sf_val":      sd["sf_val"],
                    }
                    lignes.append(ligne)
                    _add_totaux(sc_tot, ligne)

                scs.append({"sc": sc, "lignes": lignes, "totaux": sc_tot})
                _add_totaux(cd_tot, sc_tot)

            if scs:
                cds.append({"cd": cd, "scs": scs, "totaux": cd_tot})
                _add_totaux(cp_tot, cd_tot)

        if cds:
            sections.append({"cp": cp, "cds": cds, "totaux": cp_tot})
            _add_totaux(grand_total, cp_tot)

    return sections, grand_total


# ─────────────────────────────────────────────────────────────
# Compte de gestion — par dépôt
# ─────────────────────────────────────────────────────────────

@staff_member_required
def compte_gestion(request, depot_pk, exercice_pk=None):
    """
    Compte de gestion (Art. 24-25) : état annuel d'un dépôt.
    Hiérarchie CP > CD > SC > matières.
    Colonnes : SI (qté/val) | Entrées (qté/val) | Sorties déf. (qté/val)
               | Sorties prov. (qté) | SF (qté/val)
    """
    from core.models import Depot
    depot = get_object_or_404(Depot, pk=depot_pk)

    exercice_id = request.GET.get("exercice") or exercice_pk
    exercice = (
        get_object_or_404(Exercice, pk=exercice_id) if exercice_id
        else Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
    )

    sections, grand_total = _build_compte_sections(exercice, depot=depot)

    context = {
        "titre_doc":      "COMPTE DE GESTION",
        "sous_titre":     f"Dépôt : {depot.nom}",
        "modele_ref":     "Art. 24-25 — Décret N° 81-844",
        "exercice":       exercice,
        "exercice_label": exercice.code if exercice else "",
        "depot":          depot,
        "depot_label":    depot.nom,
        "sections":       sections,
        "grand_total":    grand_total,
        "date_doc":       timezone.now().date(),
        "mode":           "gestion",   # pour les templates conditionnels
    }
    return render_pdf(
        request,
        "documents/compte_gestion.html",
        context,
        filename=f"compte_gestion_{depot.identifiant}_{exercice.code if exercice else 'all'}.pdf",
    )


# ─────────────────────────────────────────────────────────────
# Compte principal — tous dépôts consolidés
# ─────────────────────────────────────────────────────────────

@staff_member_required
def compte_principal(request, exercice_pk=None):
    """
    Compte principal (Art. 26) : consolidation de tous les dépôts
    de l'établissement pour un exercice donné.
    """
    from core.models import Depot

    exercice_id = request.GET.get("exercice") or exercice_pk
    exercice = (
        get_object_or_404(Exercice, pk=exercice_id) if exercice_id
        else Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
    )

    sections, grand_total = _build_compte_sections(exercice, depot=None)
    exercices = Exercice.objects.order_by("-annee")
    depots = Depot.objects.filter(actif=True).order_by("nom")

    context = {
        "titre_doc":      "COMPTE PRINCIPAL",
        "sous_titre":     "Consolidation de tous les dépôts",
        "modele_ref":     "Art. 26 — Décret N° 81-844",
        "exercice":       exercice,
        "exercice_label": exercice.code if exercice else "",
        "exercices":      exercices,
        "depots":         depots,
        "nb_depots":      depots.count(),
        "sections":       sections,
        "grand_total":    grand_total,
        "date_doc":       timezone.now().date(),
        "mode":           "principal",
    }
    return render_pdf(
        request,
        "documents/compte_principal.html",
        context,
        filename=f"compte_principal_{exercice.code if exercice else 'all'}.pdf",
    )


# ─────────────────────────────────────────────────────────────
# Compte central — synthèse ministère / multi-établissements
# ─────────────────────────────────────────────────────────────

@staff_member_required
def compte_central(request, exercice_pk=None):
    """
    Compte central (Art. 27) : synthèse au niveau du ministère.
    Dans notre contexte mono-établissement : résumé par compte principal
    avec comparaison inter-exercices.
    """
    from django.db.models import Sum
    from inventory.models import StockCourant

    exercice_id = request.GET.get("exercice") or exercice_pk
    exercice = (
        get_object_or_404(Exercice, pk=exercice_id) if exercice_id
        else Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
    )

    exercices = Exercice.objects.order_by("-annee")
    sections, grand_total = _build_compte_sections(exercice, depot=None)

    # Synthèse par ComptePrincipal uniquement (vue agrégée supérieure)
    synthese = []
    for s in sections:
        synthese.append({
            "cp_code": s["cp"].code,
            "cp_lib":  s["cp"].libelle,
            "totaux":  s["totaux"],
        })

    # Tableau comparatif inter-exercices (SI, Entrées, Sorties, SF)
    comparatif = []
    for ex in Exercice.objects.order_by("annee"):
        _, gt = _build_compte_sections(ex, depot=None)
        comparatif.append({
            "exercice": ex,
            "si_val":   gt["si_val"],
            "ent_val":  gt["ent_val"],
            "sor_val":  gt["sor_val"],
            "sf_val":   gt["sf_val"],
        })

    context = {
        "titre_doc":      "COMPTE CENTRAL",
        "sous_titre":     "Synthèse Ministère — École normale supérieure des mines et de la géologie",
        "modele_ref":     "Art. 27 — Décret N° 81-844",
        "exercice":       exercice,
        "exercice_label": exercice.code if exercice else "",
        "exercices":      exercices,
        "sections":       sections,
        "grand_total":    grand_total,
        "synthese":       synthese,
        "comparatif":     comparatif,
        "date_doc":       timezone.now().date(),
        "mode":           "central",
    }
    return render_pdf(
        request,
        "documents/compte_central.html",
        context,
        filename=f"compte_central_{exercice.code if exercice else 'all'}.pdf",
    )


# ─────────────────────────────────────────────────────────────
# Pages d'index / navigation pour les 17 documents CDM
# ─────────────────────────────────────────────────────────────

@staff_member_required
def documents_hub(request):
    """Page centrale listant tous les documents CDM avec navigation."""
    from core.models import Depot
    from inventory.models import OperationSortie

    exercice = Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
    exercices = Exercice.objects.order_by("-annee")
    depots = Depot.objects.filter(actif=True).order_by("identifiant")
    matieres = Matiere.objects.select_related("sous_compte").order_by("code_court")
    nb_reformes = OperationSortie.objects.filter(
        type_sortie=OperationSortie.TypeSortie.REFORME_DESTRUCTION
    ).count()
    nb_certificats = OperationSortie.objects.filter(
        type_sortie=OperationSortie.TypeSortie.CERTIFICAT_ADMIN
    ).count()
    return render_to_response(request, "documents/documents_hub.html", {
        **django_admin.site.each_context(request),
        "exercice": exercice,
        "exercices": exercices,
        "depots": depots,
        "matieres": matieres,
        "nb_reformes": nb_reformes,
        "nb_certificats": nb_certificats,
        "titre_page": "Documents & Registres",
    })


@staff_member_required
def reformes_list(request):
    """Liste des opérations REFORME_DESTRUCTION → PV réforme et PV vente/destruction."""
    from inventory.models import OperationSortie
    sorties = (
        OperationSortie.objects
        .filter(type_sortie=OperationSortie.TypeSortie.REFORME_DESTRUCTION)
        .select_related("depot")
        .prefetch_related("lignes__matiere")
        .order_by("-date_sortie")
    )
    return render_to_response(request, "documents/reformes_list.html", {
        **django_admin.site.each_context(request),
        "sorties": sorties,
        "titre_page": "Réformes & Destructions",
    })


@staff_member_required
def reforme_detail(request, sortie_pk):
    """Page de détail d'une opération REFORME_DESTRUCTION avec boutons PV."""
    from inventory.models import OperationSortie
    operation = get_object_or_404(
        OperationSortie.objects.select_related("depot").prefetch_related(
            "lignes__matiere__unite"
        ),
        pk=sortie_pk,
    )
    lignes = list(operation.lignes.select_related("matiere__unite").all())
    total_valeur = sum((lg.total_ligne or Decimal("0")) for lg in lignes)
    return render_to_response(request, "documents/reformes_detail.html", {
        **django_admin.site.each_context(request),
        "operation":    operation,
        "lignes":       lignes,
        "nb_lignes":    len(lignes),
        "total_valeur": total_valeur if total_valeur else None,
        "titre_page":   f"Réforme — {operation.code}",
    })


@staff_member_required
def certificats_admin_list(request):
    """Liste des opérations CERTIFICAT_ADMIN."""
    from inventory.models import OperationSortie
    sorties = (
        OperationSortie.objects
        .filter(type_sortie=OperationSortie.TypeSortie.CERTIFICAT_ADMIN)
        .select_related("depot")
        .prefetch_related("lignes__matiere")
        .order_by("-date_sortie")
    )
    return render_to_response(request, "documents/certificats_admin_list.html", {
        **django_admin.site.each_context(request),
        "sorties": sorties,
        "titre_page": "Certificats Administratifs",
    })


@staff_member_required
def fiches_stock_index(request):
    """Liste des matières pour sélectionner une fiche de stock."""
    exercice = Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
    exercices = Exercice.objects.order_by("-annee")
    matieres = Matiere.objects.select_related(
        "sous_compte__compte_divisionnaire__compte_principal", "unite"
    ).order_by("code_court")
    return render_to_response(request, "documents/fiches_index.html", {
        **django_admin.site.each_context(request),
        "matieres": matieres,
        "exercice": exercice,
        "exercices": exercices,
        "titre_page": "Fiches de Stock",
        "titre_doc": "Fiche de stock",
        "url_base": "/documents/fiche-stock/",
    })


@staff_member_required
def fiches_inventaire_index(request):
    """Liste des matières pour sélectionner une fiche d'inventaire."""
    exercice = Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
    exercices = Exercice.objects.order_by("-annee")
    matieres = Matiere.objects.select_related(
        "sous_compte__compte_divisionnaire__compte_principal", "unite"
    ).order_by("code_court")
    return render_to_response(request, "documents/fiches_index.html", {
        **django_admin.site.each_context(request),
        "matieres": matieres,
        "exercice": exercice,
        "exercices": exercices,
        "titre_page": "Fiches d'Inventaire",
        "titre_doc": "Fiche d'inventaire",
        "url_base": "/documents/fiche-inventaire/",
    })


@staff_member_required
def comptes_gestion_index(request):
    """Liste des dépôts pour sélectionner un compte de gestion."""
    from core.models import Depot
    exercice = Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
    exercices = Exercice.objects.order_by("-annee")
    depots = Depot.objects.filter(actif=True).order_by("identifiant")
    return render_to_response(request, "documents/comptes_gestion_index.html", {
        **django_admin.site.each_context(request),
        "depots": depots,
        "exercice": exercice,
        "exercices": exercices,
        "titre_page": "Comptes de Gestion",
    })


@staff_member_required
def pv_recensement_index(request):
    """Sélecteur d'exercice pour le PV de recensement."""
    exercice = Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
    exercices = Exercice.objects.order_by("-annee")
    return render_to_response(request, "documents/pv_recensement_index.html", {
        **django_admin.site.each_context(request),
        "exercice": exercice,
        "exercices": exercices,
        "titre_page": "PV de Recensement",
    })
