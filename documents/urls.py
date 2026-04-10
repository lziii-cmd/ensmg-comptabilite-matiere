# documents/urls.py
from django.urls import path
from documents.views import (
    bon_entree_achat, pv_reception_achat, document_achat, bon_entree_modele1_achat,
    bon_entree_don, bon_entree_modele1_don, pv_reception_don, document_don,
    bon_sortie,
    bon_pret, bon_retour_pret,
    bon_mutation, bon_entree_modele1_transfert,
    bon_entree_modele1_dotation, pv_reception_dotation, document_dotation,
    bon_dotation, fiche_affectation_document, fiches_affectation_dotation,
    fiche_stock,
    livre_journal, grand_livre, balance_generale, grand_livre_par_matiere,
    grand_livre_journaux, grand_livre_par_journal, grand_livre_journaux_complet,
)
from documents.views.registres_views import (
    releve_recapitulatif, pv_reforme, fiche_inventaire,
    grand_livre_par_matiere,
    grand_livre_matieres_complet,
    grand_livre_comptes,
    grand_livre_par_compte,
    grand_livre_comptes_complet,
    pv_recensement,
    certificat_administratif,
    pv_vente_destruction,
    compte_gestion,
    compte_principal,
    compte_central,
    # Pages d'index / navigation
    documents_hub,
    reformes_list,
    reforme_detail,
    certificats_admin_list,
    fiches_stock_index,
    fiches_inventaire_index,
    comptes_gestion_index,
    pv_recensement_index,
)

app_name = "documents"

urlpatterns = [
    # ── Achats ──────────────────────────────────────────────
    path("achat/<int:pk>/imprimer/",      document_achat,    name="achat_document"),
    path("achat/<int:pk>/bon-entree/",    bon_entree_achat,  name="achat_bon_entree"),
    path("achat/<int:pk>/pv-reception/",  pv_reception_achat, name="achat_pv_reception"),
    path("achat/<int:pk>/bon-entree-modele1/", bon_entree_modele1_achat, name="achat_bon_entree_modele1"),

    # ── Dons ────────────────────────────────────────────────
    path("don/<int:pk>/imprimer/",           document_don,         name="don_document"),
    path("don/<int:pk>/bon-entree/",         bon_entree_don,       name="don_bon_entree"),
    path("don/<int:pk>/pv-reception/",       pv_reception_don,     name="don_pv_reception"),
    path("don/<int:pk>/bon-entree-modele1/", bon_entree_modele1_don, name="don_bon_entree_modele1"),

    # ── Sorties de stock ────────────────────────────────────
    path("sortie/<int:pk>/imprimer/",     bon_sortie,        name="sortie_document"),

    # ── Prêts ───────────────────────────────────────────────
    path("pret/<int:pk>/imprimer/",               bon_pret,          name="pret_document"),
    path("retour-pret/<int:pk>/imprimer/",        bon_retour_pret,   name="retour_pret_document"),

    # ── Transferts ──────────────────────────────────────────
    path("transfert/<int:pk>/imprimer/",  bon_mutation,      name="transfert_document"),
    path("transfert/<int:pk>/bon-entree-reception/", bon_entree_modele1_transfert, name="transfert_bon_entree"),

    # ── Dotations / Entrées externes ────────────────────────
    path("dotation/<int:pk>/imprimer/",    document_dotation,          name="dotation_document"),
    path("dotation/<int:pk>/pv-reception/", pv_reception_dotation,     name="dotation_pv_reception"),
    path("dotation/<int:pk>/bon-entree/",  bon_entree_modele1_dotation, name="dotation_bon_entree"),

    # ── Nouveau : Bon de dotation (modèle Dotation) ──────────────────────
    path("dotation-v2/<int:pk>/bon-dotation/", bon_dotation,              name="dotation_bon_dotation"),

    # ── Fiche d'affectation individuelle ────────────────────────────────
    path("fiche-affectation/<int:pk>/imprimer/", fiche_affectation_document, name="fiche_affectation_document"),

    # ── Toutes les fiches d'affectation d'une dotation ───────────────────
    path("dotation-v2/<int:pk>/fiches-affectation/", fiches_affectation_dotation, name="dotation_fiches_affectation"),

    # ── Fiche de stock ──────────────────────────────────────
    path("fiche-stock/<int:matiere_pk>/",                          fiche_stock, name="fiche_stock"),
    path("fiche-stock/<int:matiere_pk>/exercice/<int:exercice_pk>/", fiche_stock, name="fiche_stock_exercice"),

    # ── Livre Journal ────────────────────────────────────────
    path("livre-journal/",                           livre_journal, name="livre_journal"),
    path("livre-journal/exercice/<int:exercice_pk>/", livre_journal, name="livre_journal_exercice"),

    # ── Grand Journal des Matières (renommé depuis Grand Livre des Matières) ─
    path("grand-journal/",                             grand_livre,                   name="grand_livre"),
    path("grand-journal/exercice/<int:exercice_pk>/",  grand_livre,                   name="grand_livre_exercice"),
    path("grand-journal/matiere/<int:matiere_pk>/",    grand_livre_par_matiere,       name="grand_livre_matiere"),
    path("grand-journal/matiere/<int:matiere_pk>/exercice/<int:exercice_pk>/",
                                                       grand_livre_par_matiere,       name="grand_livre_matiere_exercice"),
    path("grand-journal/complet/",                     grand_livre_matieres_complet,  name="grand_livre_matieres_complet"),
    path("grand-journal/complet/exercice/<int:exercice_pk>/",
                                                       grand_livre_matieres_complet,  name="grand_livre_matieres_complet_exercice"),
    # Rétrocompatibilité (anciens liens)
    path("grand-livre/",                             grand_livre,                   name="grand_livre_compat"),
    path("grand-livre/matiere/<int:matiere_pk>/",    grand_livre_par_matiere,       name="grand_livre_matiere_compat"),
    path("grand-livre/complet/",                     grand_livre_matieres_complet,  name="grand_livre_matieres_complet_compat"),

    # ── Grand Livre des Comptes ──────────────────────────────
    path("grand-livre-comptes/",                         grand_livre_comptes,          name="grand_livre_comptes"),
    path("grand-livre-comptes/exercice/<int:exercice_pk>/", grand_livre_comptes,       name="grand_livre_comptes_exercice"),
    path("grand-livre-comptes/sous-compte/<int:sc_pk>/", grand_livre_par_compte,       name="grand_livre_par_compte"),
    path("grand-livre-comptes/sous-compte/<int:sc_pk>/exercice/<int:exercice_pk>/",
                                                         grand_livre_par_compte,       name="grand_livre_par_compte_exercice"),
    path("grand-livre-comptes/complet/",                 grand_livre_comptes_complet,  name="grand_livre_comptes_complet"),
    path("grand-livre-comptes/complet/exercice/<int:exercice_pk>/",
                                                         grand_livre_comptes_complet,  name="grand_livre_comptes_complet_exercice"),

    # ── Grand Livre des Journaux ─────────────────────────────
    # IMPORTANT: complet/ DOIT être avant <str:journal_code>/ pour éviter le conflit
    path("grand-livre-journaux/",                              grand_livre_journaux,          name="grand_livre_journaux"),
    path("grand-livre-journaux/exercice/<int:exercice_pk>/",   grand_livre_journaux,          name="grand_livre_journaux_exercice"),
    path("grand-livre-journaux/complet/",                      grand_livre_journaux_complet,  name="grand_livre_journaux_complet"),
    path("grand-livre-journaux/complet/exercice/<int:exercice_pk>/",
                                                               grand_livre_journaux_complet,  name="grand_livre_journaux_complet_exercice"),
    path("grand-livre-journaux/<str:journal_code>/",           grand_livre_par_journal,       name="grand_livre_par_journal"),
    path("grand-livre-journaux/<str:journal_code>/exercice/<int:exercice_pk>/",
                                                               grand_livre_par_journal,       name="grand_livre_par_journal_exercice"),

    # ── Balance générale ─────────────────────────────────────
    path("balance-generale/",                           balance_generale, name="balance_generale"),
    path("balance-generale/exercice/<int:exercice_pk>/", balance_generale, name="balance_generale_exercice"),

    # ── Documents additionnels ──────────────────────────────
    path("releve-recapitulatif/",                               releve_recapitulatif, name="releve_recapitulatif"),
    path("releve-recapitulatif/exercice/<int:exercice_pk>/",    releve_recapitulatif, name="releve_recapitulatif_exercice"),
    path("pv-reforme/<int:sortie_pk>/",                         pv_reforme,           name="pv_reforme"),
    path("fiche-inventaire/<int:matiere_pk>/",                                 fiche_inventaire, name="fiche_inventaire"),
    path("fiche-inventaire/<int:matiere_pk>/exercice/<int:exercice_pk>/",      fiche_inventaire, name="fiche_inventaire_exercice"),

    # ── Nouveaux documents CDM ───────────────────────────────
    path("pv-recensement/",                               pv_recensement,           name="pv_recensement"),
    path("pv-recensement/exercice/<int:exercice_pk>/",    pv_recensement,           name="pv_recensement_exercice"),
    path("certificat-administratif/<int:sortie_pk>/",     certificat_administratif, name="certificat_administratif"),
    path("pv-vente-destruction/<int:sortie_pk>/",         pv_vente_destruction,     name="pv_vente_destruction"),

    # ── Comptes de fin d'exercice ────────────────────────────
    # Compte de gestion — par dépôt (Art. 24-25)
    path("compte-gestion/depot/<int:depot_pk>/",                          compte_gestion, name="compte_gestion"),
    path("compte-gestion/depot/<int:depot_pk>/exercice/<int:exercice_pk>/", compte_gestion, name="compte_gestion_exercice"),

    # Compte principal — tous dépôts (Art. 26)
    path("compte-principal/",                             compte_principal, name="compte_principal"),
    path("compte-principal/exercice/<int:exercice_pk>/",  compte_principal, name="compte_principal_exercice"),

    # Compte central — synthèse ministère (Art. 27)
    path("compte-central/",                               compte_central,  name="compte_central"),
    path("compte-central/exercice/<int:exercice_pk>/",    compte_central,  name="compte_central_exercice"),

    # ── Pages d'index / navigation ───────────────────────────
    path("",                              documents_hub,            name="hub"),
    path("reformes/",                     reformes_list,            name="reformes_list"),
    path("reformes/<int:sortie_pk>/",     reforme_detail,           name="reforme_detail"),
    path("certificats-admin/",            certificats_admin_list,   name="certificats_admin_list"),
    path("fiches-stock/",                 fiches_stock_index,       name="fiches_stock_index"),
    path("fiches-inventaire/",            fiches_inventaire_index,  name="fiches_inventaire_index"),
    path("comptes-gestion/",              comptes_gestion_index,    name="comptes_gestion_index"),
    path("pv-recensement-index/",         pv_recensement_index,     name="pv_recensement_index"),
]
