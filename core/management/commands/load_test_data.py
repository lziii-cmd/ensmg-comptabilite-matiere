# core/management/commands/load_test_data.py
"""
Vide la BDD (hors auth/groupes) et charge des données de test COMPLÈTES et RICHES.
Couvre les exercices 2023 (CLOS), 2024 (CLOS), 2025 (CLOS), 2026 (OUVERT).
Chaque exercice contient des achats, dons, sorties, transferts, prêts, etc.
Usage : python manage.py load_test_data
"""
from decimal import Decimal
from datetime import date, datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


class Command(BaseCommand):
    help = 'Vide et recharge des données de test ENSMG (2023–2026)'

    def handle(self, *args, **options):
        self.stdout.write('Suppression des données existantes...')
        self._clear_data()
        self.stdout.write('Création des données de test...')
        with transaction.atomic():
            self._create_all()
        self.stdout.write(self.style.SUCCESS('Données de test chargées avec succès !'))

    def _clear_data(self):
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA foreign_keys = OFF')
            tables = [
                'purchasing_externalstockentryline',
                'purchasing_externalstockentry',
                'core_externalsource',
                'inventory_stockcourant',
                'inventory_mouvementstock',
                'inventory_ligneoperationsortie',
                'inventory_operationsortie',
                'inventory_ligneoperationtransfert',
                'inventory_operationtransfert',
                'purchasing_ligneretourpret',
                'purchasing_retourpret',
                'purchasing_ligneretour',
                'purchasing_retourfournisseur',
                'purchasing_lignepret',
                'purchasing_pret',
                'purchasing_lignedon',
                'purchasing_don',
                'purchasing_ligneachat',
                'purchasing_achat',
                'catalog_matiere',
                'catalog_souscategorie',
                'catalog_categorie',
                'catalog_souscompte',
                'catalog_comptedivisionnaire',
                'catalog_compteprincipal',
                'core_depot',
                'core_service',
                'core_donateur',
                'core_fournisseur',
                'core_exercice',
                'core_unite',
                'core_pendingrecord',
            ]
            for table in tables:
                try:
                    cursor.execute(f'DELETE FROM {table}')
                    self.stdout.write(f'  - {table}: vidée')
                except Exception as e:
                    self.stdout.write(f'  ! {table}: {e}')
            cursor.execute('PRAGMA foreign_keys = ON')

    def _create_all(self):
        from django.apps import apps

        Unite = apps.get_model('core', 'Unite')
        Service = apps.get_model('core', 'Service')
        Depot = apps.get_model('core', 'Depot')
        Fournisseur = apps.get_model('core', 'Fournisseur')
        Donateur = apps.get_model('core', 'Donateur')
        Exercice = apps.get_model('core', 'Exercice')
        Categorie = apps.get_model('catalog', 'Categorie')
        SousCategorie = apps.get_model('catalog', 'SousCategorie')
        Matiere = apps.get_model('catalog', 'Matiere')
        Achat = apps.get_model('purchasing', 'Achat')
        LigneAchat = apps.get_model('purchasing', 'LigneAchat')
        Don = apps.get_model('purchasing', 'Don')
        LigneDon = apps.get_model('purchasing', 'LigneDon')

        # ── Unités ─────────────────────────────────────────
        u_unite  = Unite.objects.create(abreviation='U',   libelle='Unité')
        u_rame   = Unite.objects.create(abreviation='RM',  libelle='Rame')
        u_boite  = Unite.objects.create(abreviation='BT',  libelle='Boîte')
        u_litre  = Unite.objects.create(abreviation='L',   libelle='Litre')
        u_paire  = Unite.objects.create(abreviation='PR',  libelle='Paire')
        u_carton = Unite.objects.create(abreviation='CT',  libelle='Carton')
        u_kg     = Unite.objects.create(abreviation='KG',  libelle='Kilogramme')
        u_m      = Unite.objects.create(abreviation='M',   libelle='Mètre')
        self.stdout.write('  Unités: 8 créées')

        # ── Services ────────────────────────────────────────
        s_admin  = Service.objects.create(code='ADM', libelle='Administration',      responsable='Mr. Diallo Mamadou',     actif=True)
        s_info   = Service.objects.create(code='INF', libelle='Informatique',        responsable='Mme Ndiaye Aissatou',    actif=True)
        s_compta = Service.objects.create(code='CPT', libelle='Comptabilité',        responsable='Mr. Ba Ibrahima',        actif=True)
        s_tech   = Service.objects.create(code='TEC', libelle='Technique',           responsable='Mr. Sall Ousmane',       actif=True)
        s_rh     = Service.objects.create(code='RH',  libelle='Ressources Humaines', responsable='Mme Sarr Coumba',        actif=True)
        s_ped    = Service.objects.create(code='PED', libelle='Pédagogie',           responsable='Mr. Faye Lamine',        actif=True)
        s_labo   = Service.objects.create(code='LAB', libelle='Laboratoire',         responsable='Mme Diouf Fatou',        actif=True)
        self.stdout.write('  Services: 7 créés')

        # ── Dépôts ──────────────────────────────────────────
        d_central = Depot.objects.create(identifiant='MAG-CENT', nom='Magasin Central',         type_lieu='DEPOT')
        d_bureau  = Depot.objects.create(identifiant='B-ADM-01', nom='Bureau Administration',   type_lieu='BUREAU')
        d_info    = Depot.objects.create(identifiant='MAG-INF',  nom='Magasin Informatique',    type_lieu='DEPOT')
        d_labo    = Depot.objects.create(identifiant='MAG-LAB',  nom='Magasin Laboratoire',     type_lieu='DEPOT')
        d_tech    = Depot.objects.create(identifiant='MAG-TEC',  nom='Magasin Technique',       type_lieu='DEPOT')
        self.stdout.write('  Dépôts: 5 créés')

        # ── Fournisseurs (8) ────────────────────────────────
        f1 = Fournisseur.objects.create(
            raison_sociale='Bureau Plus SARL',
            adresse='12 Rue des Artisans, Dakar', numero='33 820 10 10',
            courriel='contact@bureauplus.sn'
        )
        f2 = Fournisseur.objects.create(
            raison_sociale='InfoTech Solutions',
            adresse='Zone Industrielle, Thiès', numero='77 654 32 10',
            courriel='ventes@infotech.sn'
        )
        f3 = Fournisseur.objects.create(
            raison_sociale='Produits Ménagers du Sénégal',
            adresse='Autoroute VDN km3, Dakar', numero='33 860 55 00',
            courriel='info@pms.sn'
        )
        f4 = Fournisseur.objects.create(
            raison_sociale='Électro-Matériel Afrique',
            adresse='Port de Dakar, Dakar', numero='33 849 22 33',
            courriel='sales@electromat.sn'
        )
        f5 = Fournisseur.objects.create(
            raison_sociale='Papier Sénégal SA',
            adresse='Parcelles Assainies, Dakar', numero='33 835 47 20',
            courriel='commercial@papiersenegal.sn'
        )
        f6 = Fournisseur.objects.create(
            raison_sociale='Mobilier Moderne Dakar',
            adresse='Almadies, Dakar', numero='77 312 56 78',
            courriel='ventes@mobiliermoderne.sn'
        )
        f7 = Fournisseur.objects.create(
            raison_sociale='TechAfrique Distribution',
            adresse='Grand-Yoff, Dakar', numero='33 867 19 45',
            courriel='info@techafrique.sn'
        )
        f8 = Fournisseur.objects.create(
            raison_sociale='MatériauX Pro SARL',
            adresse='Zone Franche, Mbao', numero='77 445 88 12',
            courriel='contact@materiauxpro.sn'
        )
        self.stdout.write('  Fournisseurs: 8 créés')

        # ── Donateurs (5) ───────────────────────────────────
        don1 = Donateur.objects.create(
            code_prefix='UNICEF',
            raison_sociale='UNICEF Sénégal',
            adresse='Almadies, Dakar',
            telephone='33 869 90 00',
            courriel='senegal@unicef.org'
        )
        don2 = Donateur.objects.create(
            code_prefix='BM',
            raison_sociale='Banque Mondiale',
            adresse='Plateau, Dakar',
            telephone='33 859 40 00',
            courriel='dakar@worldbank.org'
        )
        don3 = Donateur.objects.create(
            code_prefix='PNUD',
            raison_sociale='Programme des Nations Unies pour le Développement',
            adresse='Sacré-Cœur, Dakar',
            telephone='33 869 44 00',
            courriel='dakar@undp.org'
        )
        don4 = Donateur.objects.create(
            code_prefix='AFD',
            raison_sociale='Agence Française de Développement',
            adresse='Mermoz, Dakar',
            telephone='33 849 70 00',
            courriel='dakar@afd.fr'
        )
        don5 = Donateur.objects.create(
            code_prefix='UNESCO',
            raison_sociale='UNESCO Bureau Dakar',
            adresse='Point E, Dakar',
            telephone='33 849 23 20',
            courriel='dakar@unesco.org'
        )
        self.stdout.write('  Donateurs: 5 créés')

        # ── Exercices ─────────────────────────────────────────
        # 2023, 2024, 2025 : CLOS — 2026 : OUVERT (exercice en cours)
        ex2023 = Exercice.objects.create(annee=2023, statut='CLOS')
        ex2024 = Exercice.objects.create(annee=2024, statut='CLOS')
        ex2025 = Exercice.objects.create(annee=2025, statut='CLOS')
        ex2026 = Exercice.objects.create(annee=2026, statut='OUVERT')
        self.stdout.write('  Exercices: 2023 (CLOS), 2024 (CLOS), 2025 (CLOS), 2026 (OUVERT)')

        # ── Catégories et Sous-catégories ───────────────────
        cat_con = Categorie.objects.create(code='CON', libelle='Consommables',    description='Fournitures de bureau')
        cat_mob = Categorie.objects.create(code='MOB', libelle='Mobilier',         description='Mobilier de bureau')
        cat_inf = Categorie.objects.create(code='INF', libelle='Informatique',     description='Matériel informatique')
        cat_net = Categorie.objects.create(code='NET', libelle='Nettoyage',        description='Produits de nettoyage')
        cat_epi = Categorie.objects.create(code='EPI', libelle='EPI',              description='Équipements de protection')
        cat_ens = Categorie.objects.create(code='ENS', libelle='Enseignement',     description='Matériel pédagogique')

        sc_pap  = SousCategorie.objects.create(code='PAP',  libelle='Papeterie',      categorie=cat_con)
        sc_imp  = SousCategorie.objects.create(code='IMP',  libelle='Impression',     categorie=cat_con)
        sc_bur  = SousCategorie.objects.create(code='BUR',  libelle='Bureau',         categorie=cat_mob)
        sc_pc   = SousCategorie.objects.create(code='PC',   libelle='Ordinateurs',    categorie=cat_inf)
        sc_per  = SousCategorie.objects.create(code='PER',  libelle='Périphériques',  categorie=cat_inf)
        sc_det  = SousCategorie.objects.create(code='DET',  libelle='Détergents',     categorie=cat_net)
        sc_prot = SousCategorie.objects.create(code='PROT', libelle='Protection',     categorie=cat_epi)
        sc_ped  = SousCategorie.objects.create(code='PED',  libelle='Pédagogique',    categorie=cat_ens)
        self.stdout.write('  Catégories & Sous-catégories: 14 créés')

        # ── Comptes ─────────────────────────────────────────
        ComptePrincipal     = apps.get_model('catalog', 'ComptePrincipal')
        CompteDivisionnaire = apps.get_model('catalog', 'CompteDivisionnaire')
        SousCompte          = apps.get_model('catalog', 'SousCompte')

        cp_con  = ComptePrincipal.objects.create(pin=60, code='60', libelle='Achats et charges', groupe='6')
        cp_immo = ComptePrincipal.objects.create(pin=21, code='21', libelle='Immobilisations',   groupe='2')

        cd_con  = CompteDivisionnaire.objects.create(pin=601, code='601', libelle='Fournitures', compte_principal=cp_con)
        cd_immo = CompteDivisionnaire.objects.create(pin=211, code='211', libelle='Mobilier',    compte_principal=cp_immo)

        ssc_pap  = SousCompte.objects.create(pin=6011, code='6011', libelle='Papeterie',        compte_divisionnaire=cd_con)
        ssc_imp  = SousCompte.objects.create(pin=6012, code='6012', libelle='Impression',       compte_divisionnaire=cd_con)
        ssc_mob  = SousCompte.objects.create(pin=6013, code='6013', libelle='Mobilier usage',   compte_divisionnaire=cd_con)
        ssc_inf  = SousCompte.objects.create(pin=6014, code='6014', libelle='Informatique',     compte_divisionnaire=cd_con)
        ssc_net  = SousCompte.objects.create(pin=6015, code='6015', libelle='Nettoyage',        compte_divisionnaire=cd_con)
        ssc_epi  = SousCompte.objects.create(pin=6016, code='6016', libelle='EPI',              compte_divisionnaire=cd_con)
        ssc_ped  = SousCompte.objects.create(pin=6017, code='6017', libelle='Pédagogique',      compte_divisionnaire=cd_con)
        ssc_immo = SousCompte.objects.create(pin=2111, code='2111', libelle='Immobilisations',  compte_divisionnaire=cd_immo)
        self.stdout.write('  Comptes: 8 sous-comptes créés')

        # ── Matières (30+) ──────────────────────────────────
        def mat(code, designation, sous_cat, unite, sous_cpt, seuil=5, type_mat='CONSOMMABLE'):
            return Matiere.objects.create(
                code_court=code, designation=designation,
                type_matiere=type_mat, seuil_min=seuil,
                sous_categorie=sous_cat, sous_compte=sous_cpt, unite=unite,
                actif=True, est_stocke=True
            )

        # Papeterie
        m_papier    = mat('PAP-A4-80',  'Papier A4 80g (rame)',           sc_pap,  u_rame,   ssc_pap, seuil=20)
        m_stylo_b   = mat('STY-BB',     'Stylo bille bleu',               sc_pap,  u_unite,  ssc_pap, seuil=30)
        m_stylo_r   = mat('STY-BR',     'Stylo bille rouge',              sc_pap,  u_unite,  ssc_pap, seuil=20)
        m_stylo_n   = mat('STY-BN',     'Stylo bille noir',               sc_pap,  u_unite,  ssc_pap, seuil=25)
        m_classeur  = mat('CLA-A4',     'Classeur A4',                    sc_pap,  u_unite,  ssc_pap, seuil=10)
        m_cahier    = mat('CAH-100',    'Cahier 100 pages',               sc_pap,  u_unite,  ssc_pap, seuil=15)
        m_bloc_note = mat('BLC-A4',     'Bloc-notes A4',                  sc_pap,  u_unite,  ssc_pap, seuil=10)
        m_enveloppe = mat('ENV-C4',     'Enveloppes C4',                  sc_pap,  u_carton, ssc_pap, seuil=5)
        m_marqueur  = mat('MAR-NOI',    'Marqueur permanent noir',        sc_pap,  u_unite,  ssc_pap, seuil=10)
        m_chemise   = mat('CHM-A4',     'Chemise cartonnée A4',           sc_pap,  u_unite,  ssc_pap, seuil=20)
        # Impression
        m_cart      = mat('CART-NR',    'Cartouche encre noire',          sc_imp,  u_unite,  ssc_imp, seuil=5)
        m_toner     = mat('TON-NR',     'Toner noir',                     sc_imp,  u_unite,  ssc_imp, seuil=3)
        m_toner_c   = mat('TON-CL',     'Toner couleur',                  sc_imp,  u_unite,  ssc_imp, seuil=2)
        m_papier_i  = mat('PAP-IMP',    'Papier impression 75g',          sc_imp,  u_rame,   ssc_imp, seuil=10)
        m_ruban     = mat('RUB-IMP',    'Ruban encreur imprimante',       sc_imp,  u_unite,  ssc_imp, seuil=4)
        # Informatique
        m_pc        = mat('PC-I7',      'Ordinateur portable Core i7',    sc_pc,   u_unite,  ssc_inf, seuil=2, type_mat='IMMOBILISATION')
        m_pc_fixe   = mat('PC-FIX',     'Ordinateur fixe i5',             sc_pc,   u_unite,  ssc_inf, seuil=1, type_mat='IMMOBILISATION')
        m_tablette  = mat('TAB-10',     'Tablette 10 pouces',             sc_pc,   u_unite,  ssc_inf, seuil=1, type_mat='IMMOBILISATION')
        m_souris    = mat('SOU-USB',    'Souris USB',                     sc_per,  u_unite,  ssc_inf, seuil=5)
        m_souris_w  = mat('SOU-WRL',    'Souris sans fil',                sc_per,  u_unite,  ssc_inf, seuil=5)
        m_clavier   = mat('CLA-USB',    'Clavier USB',                    sc_per,  u_unite,  ssc_inf, seuil=5)
        m_clavier_w = mat('CLA-WRL',    'Clavier sans fil',               sc_per,  u_unite,  ssc_inf, seuil=3)
        m_ecran     = mat('ECR-27',     'Écran 27 pouces LED',            sc_per,  u_unite,  ssc_inf, seuil=2)
        m_hub_usb   = mat('HUB-USB',    'Hub USB 7 ports',                sc_per,  u_unite,  ssc_inf, seuil=2)
        m_cle_usb   = mat('USB-32G',    'Clé USB 32 Go',                  sc_per,  u_unite,  ssc_inf, seuil=5)
        # Nettoyage
        m_ampoule   = mat('AMP-LED',    'Ampoule LED 9W',                 sc_det,  u_unite,  ssc_net, seuil=10)
        m_deterg    = mat('DET-1L',     'Détergent 1L',                   sc_det,  u_litre,  ssc_net, seuil=10)
        m_balai     = mat('BAL-STD',    'Balai brosse standard',          sc_det,  u_unite,  ssc_net, seuil=5)
        m_sac_pou   = mat('SAC-POU',    'Sac poubelle 100L (rouleau)',    sc_det,  u_carton, ssc_net, seuil=5)
        # EPI
        m_gant      = mat('GANT-M',     'Gants protection taille M',      sc_prot, u_paire,  ssc_epi, seuil=10)
        m_masque    = mat('MASQ-CH',    'Masque chirurgical',             sc_prot, u_unite,  ssc_epi, seuil=20)
        m_casque    = mat('CASC-STD',   'Casque de sécurité',             sc_prot, u_unite,  ssc_epi, seuil=5)
        # Mobilier
        m_chaise    = mat('CH-STD',     'Chaise standard',                sc_bur,  u_unite,  ssc_immo, seuil=2, type_mat='IMMOBILISATION')
        m_bureau    = mat('BUR-DIR',    'Bureau directeur',               sc_bur,  u_unite,  ssc_immo, seuil=1, type_mat='IMMOBILISATION')
        m_etagere   = mat('ETA-METAL',  'Étagère métallique',             sc_bur,  u_unite,  ssc_immo, seuil=2, type_mat='IMMOBILISATION')
        m_armoire   = mat('ARM-A4',     'Armoire de rangement',           sc_bur,  u_unite,  ssc_immo, seuil=1, type_mat='IMMOBILISATION')
        # Pédagogique
        m_tableau   = mat('TAB-BLC',    'Tableau blanc 120x90',           sc_ped,  u_unite,  ssc_ped,  seuil=2, type_mat='IMMOBILISATION')
        m_feutre    = mat('FEU-TB',     'Feutres tableau (jeu 4 coul.)',  sc_ped,  u_boite,  ssc_ped,  seuil=10)
        m_efface    = mat('EFF-TB',     'Effaceur tableau blanc',         sc_ped,  u_unite,  ssc_ped,  seuil=5)
        self.stdout.write('  Matières: 38 créées')

        # ════════════════════════════════════════════════════════════
        #  HELPERS
        # ════════════════════════════════════════════════════════════
        def make_achat(fournisseur, depot, date_a, num_facture, exercice, lignes):
            total_ht = sum(Decimal(str(l[1])) * Decimal(str(l[2])) for l in lignes)
            achat = Achat.objects.create(
                fournisseur=fournisseur, depot=depot,
                date_achat=date_a, numero_facture=num_facture,
                tva_active=False, total_ht=total_ht,
                total_tva=Decimal('0'), total_ttc=total_ht
            )
            for matiere, qte, prix in lignes:
                LigneAchat.objects.create(
                    achat=achat, matiere=matiere,
                    quantite=Decimal(str(qte)), prix_unitaire=Decimal(str(prix))
                )
            achat.recompute_totaux()
            achat.save(update_fields=['total_ht', 'total_tva', 'total_ttc'])
            return achat

        def make_don(donateur, depot, date_d, num_piece, lignes):
            total_val = sum(Decimal(str(l[1])) * Decimal(str(l[2])) for l in lignes)
            don = Don.objects.create(
                donateur=donateur, depot=depot,
                date_don=date_d, numero_piece=num_piece,
                total_valeur=Decimal(str(total_val))
            )
            for matiere, qte, val_unit in lignes:
                LigneDon.objects.create(
                    don=don, matiere=matiere,
                    quantite=Decimal(str(qte)), prix_unitaire=Decimal(str(val_unit))
                )
            don.recompute_totaux()
            don.save(update_fields=['total_valeur'])
            return don

        OperationSortie = apps.get_model('inventory', 'OperationSortie')
        LigneOperationSortie = apps.get_model('inventory', 'LigneOperationSortie')

        def make_sortie(type_s, depot, date_s, motif, num_doc, lignes_data):
            op = OperationSortie.objects.create(
                type_sortie=type_s, depot=depot,
                date_sortie=date_s, motif_principal=motif,
                numero_document=num_doc,
            )
            for matiere, qte, prix in lignes_data:
                LigneOperationSortie.objects.create(
                    operation=op, matiere=matiere,
                    quantite=Decimal(str(qte)), prix_unitaire=Decimal(str(prix)),
                )
            op.recompute_totaux()
            op.save(update_fields=['total_valeur'])
            return op

        OperationTransfert = apps.get_model('inventory', 'OperationTransfert')
        LigneOperationTransfert = apps.get_model('inventory', 'LigneOperationTransfert')

        def make_transfert(motif, depot_src, depot_dst, date_op, description, lignes_data):
            op = OperationTransfert.objects.create(
                motif=motif, depot_source=depot_src, depot_destination=depot_dst,
                date_operation=date_op, description=description,
            )
            for matiere, qte, cout in lignes_data:
                LigneOperationTransfert.objects.create(
                    operation=op, matiere=matiere,
                    quantite=Decimal(str(qte)), cout_unitaire=Decimal(str(cout)),
                )
            op.recompute_totaux()
            op.save(update_fields=['total_valeur'])
            return op

        Pret = apps.get_model('purchasing', 'Pret')
        LignePret = apps.get_model('purchasing', 'LignePret')

        def make_pret(service, depot, date_p, commentaire, lignes_data, est_clos=False):
            pret = Pret.objects.create(
                service=service, depot=depot,
                date_pret=date_p, commentaire=commentaire, est_clos=est_clos,
            )
            for matiere, qte in lignes_data:
                LignePret.objects.create(
                    pret=pret, matiere=matiere, quantite=Decimal(str(qte)),
                )
            return pret

        RetourPret = apps.get_model('purchasing', 'RetourPret')
        LigneRetourPret = apps.get_model('purchasing', 'LigneRetourPret')

        def make_retour_pret(pret, date_ret, commentaire, num_piece, lignes, close_pret=False):
            rp = RetourPret.objects.create(
                pret=pret, date_retour=date_ret,
                commentaire=commentaire, numero_piece=num_piece,
            )
            for matiere, qte in lignes:
                LigneRetourPret.objects.create(retour=rp, matiere=matiere, quantite=Decimal(str(qte)))
            rp.recompute_total()
            rp.save(update_fields=['total_qte'])
            if close_pret:
                pret.recompute_closure()
                pret.save(update_fields=['est_clos'])
            return rp

        RetourFournisseur = apps.get_model('purchasing', 'RetourFournisseur')
        LigneRetour = apps.get_model('purchasing', 'LigneRetour')

        def make_retour_fournisseur(fournisseur, depot, date_ret, commentaire, lignes):
            ret = RetourFournisseur.objects.create(
                fournisseur=fournisseur, depot=depot,
                date_retour=date_ret, commentaire=commentaire,
            )
            for matiere, qte in lignes:
                LigneRetour.objects.create(retour=ret, matiere=matiere, quantite=Decimal(str(qte)))
            return ret

        ExternalSource = apps.get_model('core', 'ExternalSource')
        ExternalStockEntry = apps.get_model('purchasing', 'ExternalStockEntry')
        ExternalStockEntryLine = apps.get_model('purchasing', 'ExternalStockEntryLine')

        def make_dotation(source, depot, date_rec, num_doc, comment, lignes):
            entry = ExternalStockEntry.objects.create(
                source=source, depot=depot,
                received_date=date_rec, document_number=num_doc, comment=comment,
            )
            for matiere, qte, pu in lignes:
                ExternalStockEntryLine.objects.create(
                    entry=entry, matiere=matiere,
                    quantity=Decimal(str(qte)), unit_price=Decimal(str(pu))
                )
            entry.recompute_totals()
            entry.save(update_fields=['total_value'])
            return entry

        # ════════════════════════════════════════════════════════════
        #  SOURCES EXTERNES
        # ════════════════════════════════════════════════════════════
        src_mfpai  = ExternalSource.objects.create(source_type='MINISTRY', name='Ministère de la Formation Professionnelle',   acronym='MFPAI')
        src_men    = ExternalSource.objects.create(source_type='MINISTRY', name='Ministère de l\'Éducation Nationale',          acronym='MEN')
        src_bm     = ExternalSource.objects.create(source_type='PARTNER',  name='Banque Mondiale Sénégal',                     acronym='BMS')
        src_unicef = ExternalSource.objects.create(source_type='PARTNER',  name='UNICEF Sénégal',                              acronym='UNICEF')
        src_afd    = ExternalSource.objects.create(source_type='PARTNER',  name='Agence Française de Développement',           acronym='AFD')
        src_usaid  = ExternalSource.objects.create(source_type='PARTNER',  name='USAID Sénégal',                               acronym='USAID')
        self.stdout.write('  Sources externes: 6 créées')

        # ════════════════════════════════════════════════════════════
        #  EXERCICE 2023 — CLOS
        # ════════════════════════════════════════════════════════════
        self.stdout.write('  --- EXERCICE 2023 ---')

        # Achats 2023 (5)
        make_achat(f1, d_central, date(2023, 1, 20), 'FACT-2023-001', ex2023, [
            (m_papier,   60, '3000'),
            (m_stylo_b, 100, '200'),
            (m_classeur, 30, '750'),
        ])
        make_achat(f2, d_central, date(2023, 3, 15), 'FACT-2023-002', ex2023, [
            (m_cart,      8, '11000'),
            (m_souris,   10, '4500'),
            (m_clavier,   8, '7000'),
        ])
        make_achat(f3, d_central, date(2023, 5, 10), 'FACT-2023-003', ex2023, [
            (m_deterg,   25, '1500'),
            (m_gant,     30, '1300'),
            (m_masque,   80, '450'),
        ])
        make_achat(f6, d_central, date(2023, 7, 3), 'FACT-2023-004', ex2023, [
            (m_chaise,    6, '40000'),
            (m_etagere,   3, '30000'),
        ])
        make_achat(f5, d_central, date(2023, 10, 18), 'FACT-2023-005', ex2023, [
            (m_papier_i, 20, '2800'),
            (m_enveloppe, 10, '2500'),
            (m_cahier,   40, '550'),
        ])
        self.stdout.write('  Achats 2023: 5 créés')

        # Dons 2023 (3)
        make_don(don4, d_central, date(2023, 2, 14), 'DON-2023-001', [
            (m_pc,       2, '750000'),
            (m_ecran,    2, '85000'),
        ])
        make_don(don1, d_central, date(2023, 6, 20), 'DON-2023-002', [
            (m_masque, 300, '400'),
            (m_gant,   150, '1100'),
        ])
        make_don(don5, d_central, date(2023, 9, 5), 'DON-2023-003', [
            (m_tableau,  2, '45000'),
            (m_feutre,  10, '2500'),
        ])
        self.stdout.write('  Dons 2023: 3 créés')

        # Sorties 2023 (5)
        make_sortie('CONSOMMATION_2E_GROUPE', d_central, date(2023, 2, 28),
                    'Dotation mensuelle – Administration', 'BS-2023-0001',
                    [(m_papier, 8, 3000), (m_stylo_b, 25, 200)])
        make_sortie('CONSOMMATION_2E_GROUPE', d_central, date(2023, 5, 31),
                    'Dotation mai – Service Informatique', 'BS-2023-0002',
                    [(m_cart, 3, 11000), (m_souris, 2, 4500)])
        make_sortie('REFORME_DESTRUCTION', d_central, date(2023, 7, 20),
                    'Réforme matériel vétuste', 'PV-REF-2023-001',
                    [(m_chaise, 2, 40000)])
        make_sortie('CONSOMMATION_2E_GROUPE', d_central, date(2023, 9, 15),
                    'Dotation Service Pédagogie', 'BS-2023-0003',
                    [(m_feutre, 4, 2500), (m_efface, 3, 1500)])
        make_sortie('PERTE_VOL_DEFICIT', d_central, date(2023, 11, 10),
                    'Déficit constaté lors recensement annuel', 'PV-REC-2023-001',
                    [(m_stylo_b, 10, 200), (m_enveloppe, 2, 2500)])
        self.stdout.write('  Sorties 2023: 5 créées')

        # Transferts 2023 (3)
        make_transfert('AFFECTATION', d_central, d_bureau,
                       date(2023, 1, 25), 'Dotation initiale Bureau Admin – Jan 2023',
                       [(m_papier, 15, 3000), (m_stylo_b, 20, 200), (m_classeur, 8, 750)])
        make_transfert('AFFECTATION', d_central, d_labo,
                       date(2023, 4, 10), 'Dotation Labo – matériel de protection',
                       [(m_gant, 15, 1300), (m_masque, 30, 450), (m_casque, 4, 8000)])
        make_transfert('AFFECTATION', d_central, d_info,
                       date(2023, 6, 1), 'Affectation informatique – magasin INF',
                       [(m_souris, 4, 4500), (m_clavier, 4, 7000)])
        self.stdout.write('  Transferts 2023: 3 créés')

        # Entrées externes 2023 (2)
        make_dotation(src_mfpai, d_central, date(2023, 1, 5), 'DOT-MFPAI-2023-001',
                      'Dotation annuelle fournitures – Ministère Éducation 2023',
                      [(m_papier, 40, 3000), (m_stylo_b, 80, 200), (m_cahier, 30, 550)])
        make_dotation(src_bm, d_central, date(2023, 8, 20), 'BM-EQUIP-2023-004',
                      'Équipement pédagogique – Projet PAQUET-EF phase 1',
                      [(m_tableau, 3, 45000), (m_feutre, 15, 2500), (m_efface, 8, 1500)])
        self.stdout.write('  Dotations 2023: 2 créées')

        # Prêts 2023 (3)
        pret_2023_1 = make_pret(s_rh, d_central, date(2023, 3, 10),
                                'Prêt chaises pour réunion annuelle RH',
                                [(m_chaise, 4)])
        pret_2023_2 = make_pret(s_info, d_central, date(2023, 7, 15),
                                'Prêt clés USB pour formation informatique',
                                [(m_cle_usb, 10)])
        pret_2023_3 = make_pret(s_ped, d_central, date(2023, 10, 5),
                                'Prêt matériel pédagogique – séminaire',
                                [(m_feutre, 5), (m_efface, 3)])
        self.stdout.write('  Prêts 2023: 3 créés')

        # Retours prêts 2023
        make_retour_pret(pret_2023_1, date(2023, 3, 20), 'Retour total chaises', 'RET-2023-001',
                         [(m_chaise, 4)], close_pret=True)
        make_retour_pret(pret_2023_3, date(2023, 10, 25), 'Retour matériel pédagogique', 'RET-2023-002',
                         [(m_feutre, 5), (m_efface, 3)], close_pret=True)
        self.stdout.write('  Retours prêts 2023: 2 créés')

        # Retours fournisseurs 2023
        make_retour_fournisseur(f3, d_central, date(2023, 5, 22),
                                'Détergents non conformes aux spécifications',
                                [(m_deterg, 5)])
        make_retour_fournisseur(f2, d_central, date(2023, 9, 8),
                                'Clavier défectueux à la livraison',
                                [(m_clavier, 2)])
        self.stdout.write('  Retours fournisseurs 2023: 2 créés')

        # ════════════════════════════════════════════════════════════
        #  EXERCICE 2024 — CLOS
        # ════════════════════════════════════════════════════════════
        self.stdout.write('  --- EXERCICE 2024 ---')

        # Achats 2024 (7)
        make_achat(f1, d_central, date(2024, 1, 12), 'FACT-2024-001', ex2024, [
            (m_papier,   80, '3100'),
            (m_stylo_b, 120, '210'),
            (m_chemise,  50, '450'),
        ])
        make_achat(f2, d_central, date(2024, 2, 20), 'FACT-2024-002', ex2024, [
            (m_toner,     4, '34000'),
            (m_cart,      6, '11500'),
            (m_papier_i, 15, '2900'),
        ])
        make_achat(f3, d_central, date(2024, 4, 8), 'FACT-2024-003', ex2024, [
            (m_deterg,   20, '1600'),
            (m_gant,     25, '1350'),
            (m_balai,    10, '3500'),
        ])
        make_achat(f7, d_central, date(2024, 6, 15), 'FACT-2024-004', ex2024, [
            (m_pc,        2, '800000'),
            (m_souris_w,  5, '5800'),
            (m_clavier_w, 3, '7200'),
        ])
        make_achat(f6, d_central, date(2024, 7, 22), 'FACT-2024-005', ex2024, [
            (m_armoire,   2, '95000'),
            (m_etagere,   4, '32000'),
        ])
        make_achat(f5, d_central, date(2024, 9, 5), 'FACT-2024-006', ex2024, [
            (m_cahier,   60, '580'),
            (m_bloc_note,25, '430'),
            (m_marqueur, 30, '900'),
        ])
        make_achat(f1, d_central, date(2024, 11, 10), 'FACT-2024-007', ex2024, [
            (m_papier,   80, '3200'),
            (m_stylo_b, 150, '230'),
        ])
        self.stdout.write('  Achats 2024: 7 créés')

        # Dons 2024 (3)
        make_don(don2, d_central, date(2024, 3, 18), 'DON-2024-001', [
            (m_pc,       3, '850000'),
            (m_tablette, 5, '280000'),
        ])
        make_don(don3, d_central, date(2024, 6, 10), 'DON-2024-002', [
            (m_papier, 50, '3100'),
            (m_stylo_b, 80, '210'),
            (m_classeur, 20, '780'),
        ])
        make_don(don4, d_central, date(2024, 10, 25), 'DON-2024-003', [
            (m_feutre,  15, '2400'),
            (m_efface,   8, '1400'),
            (m_tableau,  1, '42000'),
        ])
        self.stdout.write('  Dons 2024: 3 créés')

        # Sorties 2024 (7)
        make_sortie('CONSOMMATION_2E_GROUPE', d_central, date(2024, 2, 29),
                    'Dotation février – Administration', 'BS-2024-0001',
                    [(m_papier, 12, 3100), (m_stylo_b, 30, 210)])
        make_sortie('CONSOMMATION_2E_GROUPE', d_central, date(2024, 4, 30),
                    'Dotation avril – Service Informatique', 'BS-2024-0002',
                    [(m_toner, 2, 34000), (m_cart, 3, 11500)])
        make_sortie('AFFECTATION', d_central, date(2024, 5, 15),
                    'Affectation PCs neufs – salle multimédia', 'AFF-2024-001',
                    [(m_pc, 2, 800000), (m_souris_w, 2, 5800)])
        make_sortie('CONSOMMATION_2E_GROUPE', d_central, date(2024, 7, 15),
                    'Dotation juillet – Service RH', 'BS-2024-0003',
                    [(m_cahier, 15, 580), (m_bloc_note, 8, 430)])
        make_sortie('REFORME_DESTRUCTION', d_central, date(2024, 8, 20),
                    'Réforme étagères vétustes', 'PV-REF-2024-001',
                    [(m_etagere, 2, 32000)])
        make_sortie('CONSOMMATION_2E_GROUPE', d_central, date(2024, 10, 1),
                    'Dotation octobre – Service Pédagogie', 'BS-2024-0004',
                    [(m_feutre, 6, 2400), (m_efface, 3, 1400)])
        make_sortie('PERTE_VOL_DEFICIT', d_central, date(2024, 12, 5),
                    'Perte détergents – fuite stockage', 'PV-REC-2024-001',
                    [(m_deterg, 4, 1600)])
        self.stdout.write('  Sorties 2024: 7 créées')

        # Transferts 2024 (4)
        make_transfert('AFFECTATION', d_central, d_bureau,
                       date(2024, 1, 20), 'Dotation annuelle Bureau Administration 2024',
                       [(m_papier, 20, 3100), (m_stylo_b, 30, 210), (m_chemise, 20, 450)])
        make_transfert('AFFECTATION', d_central, d_info,
                       date(2024, 3, 5), 'Matériel informatique – Magasin INF 2024',
                       [(m_souris, 5, 4500), (m_clavier, 4, 7000), (m_cart, 4, 11500)])
        make_transfert('AFFECTATION', d_central, d_labo,
                       date(2024, 4, 15), 'Dotation Labo – produits protection 2024',
                       [(m_gant, 12, 1350), (m_masque, 25, 450), (m_deterg, 6, 1600)])
        make_transfert('RETOUR', d_bureau, d_central,
                       date(2024, 11, 15), 'Retour excédent fin d\'année – Bureau Admin',
                       [(m_papier, 8, 3100), (m_chemise, 5, 450)])
        self.stdout.write('  Transferts 2024: 4 créés')

        # Entrées externes 2024 (2)
        make_dotation(src_men, d_central, date(2024, 1, 8), 'DOT-MEN-2024-001',
                      'Dotation annuelle MEN 2024 – fournitures bureau',
                      [(m_papier, 50, 3100), (m_stylo_b, 100, 210), (m_classeur, 25, 780)])
        make_dotation(src_afd, d_central, date(2024, 9, 12), 'AFD-PROJET-2024-008',
                      'Équipement pédagogique – Projet Mines & Géologie AFD',
                      [(m_tableau, 2, 42000), (m_tablette, 3, 280000)])
        self.stdout.write('  Dotations 2024: 2 créées')

        # Prêts 2024 (4)
        pret_2024_1 = make_pret(s_admin, d_central, date(2024, 2, 5),
                                'Prêt mobilier pour séminaire Administration',
                                [(m_chaise, 8), (m_bureau, 1)])
        pret_2024_2 = make_pret(s_compta, d_central, date(2024, 5, 12),
                                'Prêt fournitures bureautiques – Comptabilité',
                                [(m_papier, 8), (m_stylo_b, 20)])
        pret_2024_3 = make_pret(s_info, d_central, date(2024, 8, 20),
                                'Prêt périphériques pour formation',
                                [(m_souris_w, 4), (m_clavier_w, 3)])
        pret_2024_4 = make_pret(s_labo, d_central, date(2024, 11, 3),
                                'Prêt EPI Laboratoire – TP étudiants',
                                [(m_gant, 10), (m_masque, 20)])
        self.stdout.write('  Prêts 2024: 4 créés')

        # Retours prêts 2024
        make_retour_pret(pret_2024_1, date(2024, 2, 20), 'Retour total mobilier séminaire', 'RET-2024-001',
                         [(m_chaise, 8), (m_bureau, 1)], close_pret=True)
        make_retour_pret(pret_2024_3, date(2024, 9, 10), 'Retour partiel périphériques', 'RET-2024-002',
                         [(m_souris_w, 3), (m_clavier_w, 2)])
        make_retour_pret(pret_2024_4, date(2024, 12, 2), 'Retour EPI Labo après TP', 'RET-2024-003',
                         [(m_gant, 10), (m_masque, 18)], close_pret=False)
        self.stdout.write('  Retours prêts 2024: 3 créés')

        # Retours fournisseurs 2024
        make_retour_fournisseur(f1, d_central, date(2024, 2, 8),
                                'Papier humide – lot défectueux',
                                [(m_papier, 10)])
        make_retour_fournisseur(f7, d_central, date(2024, 7, 5),
                                'Souris sans fil défectueuses à la livraison',
                                [(m_souris_w, 2)])
        self.stdout.write('  Retours fournisseurs 2024: 2 créés')

        # ════════════════════════════════════════════════════════════
        #  EXERCICE 2025 — CLOS
        # ════════════════════════════════════════════════════════════
        self.stdout.write('  --- EXERCICE 2025 ---')

        # Achats 2025 (10)
        make_achat(f1, d_central, date(2025, 1, 15), 'FACT-2025-001', ex2025, [
            (m_papier,    100, '3500'),
            (m_stylo_b,   200, '250'),
            (m_stylo_r,   100, '250'),
            (m_classeur,   50, '800'),
        ])
        make_achat(f2, d_central, date(2025, 2, 10), 'FACT-2025-002', ex2025, [
            (m_cart,      10, '12000'),
            (m_toner,      5, '35000'),
            (m_souris,    15, '5000'),
            (m_clavier,   10, '7500'),
        ])
        make_achat(f3, d_central, date(2025, 3, 5), 'FACT-2025-003', ex2025, [
            (m_deterg,    20, '1800'),
            (m_gant,      30, '1500'),
            (m_masque,    50, '500'),
        ])
        make_achat(f1, d_central, date(2025, 4, 20), 'FACT-2025-004', ex2025, [
            (m_cahier,    60, '600'),
            (m_ampoule,   20, '2000'),
        ])
        make_achat(f2, d_central, date(2025, 5, 8), 'FACT-2025-005', ex2025, [
            (m_pc,         3, '850000'),
            (m_chaise,     8, '45000'),
        ])
        make_achat(f4, d_central, date(2025, 6, 12), 'FACT-2025-006', ex2025, [
            (m_ecran,      5, '95000'),
            (m_hub_usb,    3, '8000'),
        ])
        make_achat(f1, d_central, date(2025, 7, 3), 'FACT-2025-007', ex2025, [
            (m_stylo_n,   120, '260'),
            (m_bloc_note,  30, '450'),
        ])
        make_achat(f2, d_central, date(2025, 8, 15), 'FACT-2025-008', ex2025, [
            (m_pc_fixe,    2, '650000'),
            (m_souris_w,   5, '6000'),
        ])
        make_achat(f3, d_central, date(2025, 9, 22), 'FACT-2025-009', ex2025, [
            (m_toner_c,    3, '40000'),
            (m_papier_i,   25, '3000'),
        ])
        make_achat(f1, d_central, date(2025, 10, 10), 'FACT-2025-010', ex2025, [
            (m_bureau,     2, '120000'),
            (m_etagere,    4, '35000'),
        ])
        self.stdout.write('  Achats 2025: 10 créés')

        # Dons 2025 (5)
        make_don(don1, d_central, date(2025, 1, 28), 'DON-2025-001', [
            (m_masque, 200, '400'),
            (m_gant,   100, '1200'),
        ])
        make_don(don2, d_central, date(2025, 3, 15), 'DON-2025-002', [
            (m_pc,      2, '900000'),
            (m_souris,  5, '4500'),
        ])
        make_don(don1, d_central, date(2025, 5, 10), 'DON-2025-003', [
            (m_deterg, 15, '1500'),
        ])
        make_don(don3, d_central, date(2025, 7, 20), 'DON-2025-004', [
            (m_toner,  2, '38000'),
            (m_papier, 40, '3300'),
        ])
        make_don(don2, d_central, date(2025, 9, 5), 'DON-2025-005', [
            (m_clavier, 8, '7000'),
            (m_ecran,   1, '100000'),
        ])
        self.stdout.write('  Dons 2025: 5 créés')

        # Sorties 2025 (10)
        make_sortie('CONSOMMATION_2E_GROUPE', d_central, date(2025, 2, 28),
                    'Dotation mensuelle février – Service Administration', 'BS-2025-0001',
                    [(m_papier, 10, 3500), (m_stylo_b, 30, 250)])
        make_sortie('CONSOMMATION_2E_GROUPE', d_central, date(2025, 3, 31),
                    'Dotation mars – Service Informatique', 'BS-2025-0002',
                    [(m_cart, 3, 12000), (m_toner, 2, 35000)])
        make_sortie('REFORME_DESTRUCTION', d_central, date(2025, 4, 15),
                    'Réforme mobilier vétuste', 'PV-REF-2025-001',
                    [(m_chaise, 2, 45000)])
        make_sortie('PERTE_VOL_DEFICIT', d_central, date(2025, 5, 20),
                    'Déficit constaté lors recensement mai', 'PV-REC-2025-001',
                    [(m_ampoule, 3, 2000)])
        make_sortie('CERTIFICAT_ADMIN', d_central, date(2025, 6, 10),
                    'Régularisation changement dénomination', 'CERT-ADM-2025-001',
                    [(m_cahier, 5, 600)])
        make_sortie('CONSOMMATION_2E_GROUPE', d_central, date(2025, 7, 15),
                    'Dotation juillet – Service Comptabilité', 'BS-2025-0003',
                    [(m_papier, 15, 3500), (m_stylo_n, 20, 260)])
        make_sortie('AFFECTATION', d_central, date(2025, 8, 5),
                    'Affectation matériel informatique', 'AFF-2025-001',
                    [(m_souris, 3, 5000), (m_clavier, 2, 7500)])
        make_sortie('CONSOMMATION_2E_GROUPE', d_central, date(2025, 9, 10),
                    'Dotation septembre – Service Informatique', 'BS-2025-0004',
                    [(m_toner, 1, 35000), (m_cart, 2, 12000)])
        make_sortie('CONSOMMATION_2E_GROUPE', d_central, date(2025, 10, 1),
                    'Dotation octobre – Service RH', 'BS-2025-0005',
                    [(m_papier, 8, 3500), (m_bloc_note, 10, 450)])
        make_sortie('CONSOMMATION_2E_GROUPE', d_central, date(2025, 11, 15),
                    'Dotation novembre – Service Administration', 'BS-2025-0006',
                    [(m_stylo_b, 50, 250), (m_classeur, 10, 800)])
        self.stdout.write('  Sorties 2025: 10 créées')

        # Transferts 2025 (5)
        make_transfert('AFFECTATION', d_central, d_bureau,
                       date(2025, 2, 1), 'Dotation initiale Bureau Administration 2025',
                       [(m_papier, 20, 3500), (m_stylo_b, 30, 250), (m_classeur, 10, 800)])
        make_transfert('AFFECTATION', d_central, d_info,
                       date(2025, 2, 5), 'Affectation informatique – Magasin INF',
                       [(m_souris, 5, 5000), (m_clavier, 5, 7500), (m_cart, 5, 12000)])
        make_transfert('RETOUR', d_bureau, d_central,
                       date(2025, 6, 1), 'Retour excédent consommables non utilisés',
                       [(m_papier, 5, 3500)])
        make_transfert('AFFECTATION', d_central, d_labo,
                       date(2025, 3, 10), 'Dotation Magasin Laboratoire',
                       [(m_gant, 20, 1500), (m_masque, 30, 500)])
        make_transfert('AFFECTATION', d_central, d_tech,
                       date(2025, 4, 1), 'Dotation Magasin Technique',
                       [(m_ampoule, 10, 2000), (m_deterg, 8, 1800)])
        self.stdout.write('  Transferts 2025: 5 créés')

        # Entrées externes 2025 (3)
        make_dotation(src_men, d_central, date(2025, 1, 10), 'DOT-MEN-2025-001',
                      'Dotation annuelle fournitures de bureau – Ministère 2025',
                      [(m_papier, 50, 3500), (m_stylo_b, 100, 250), (m_classeur, 20, 800)])
        make_dotation(src_bm, d_central, date(2025, 3, 22), 'BMS-GRANT-2025-003',
                      'Matériel informatique – Projet PAQUET-EF',
                      [(m_pc, 2, 950000), (m_souris, 5, 5000)])
        make_dotation(src_unicef, d_central, date(2025, 7, 15), 'UNICEF-EQUIP-2025-005',
                      'Équipements de protection – campagne de santé',
                      [(m_masque, 500, 400), (m_gant, 200, 1200)])
        self.stdout.write('  Dotations 2025: 3 créées')

        # Prêts 2025 (5)
        pret_2025_1 = make_pret(s_info, d_central, date(2025, 3, 10),
                                'Prêt temporaire matériel informatique',
                                [(m_souris, 3), (m_clavier, 2)])
        pret_2025_2 = make_pret(s_compta, d_central, date(2025, 4, 5),
                                'Prêt fournitures en attente livraison',
                                [(m_papier, 5), (m_stylo_b, 10)])
        pret_2025_3 = make_pret(s_tech, d_central, date(2025, 2, 15),
                                'Prêt cartouches temporaire',
                                [(m_cart, 2)])
        pret_2025_4 = make_pret(s_admin, d_central, date(2025, 5, 20),
                                'Prêt consommables Service Admin',
                                [(m_bloc_note, 5), (m_stylo_r, 15)])
        pret_2025_5 = make_pret(s_rh, d_central, date(2025, 6, 1),
                                'Prêt chaises pour événement RH',
                                [(m_chaise, 6)])
        self.stdout.write('  Prêts 2025: 5 créés')

        # Retours prêts 2025
        make_retour_pret(pret_2025_3, date(2025, 3, 1), 'Retour complet cartouches', 'RET-2025-001',
                         [(m_cart, 2)], close_pret=True)
        make_retour_pret(pret_2025_1, date(2025, 4, 20), 'Retour partiel – 1 souris rendue', 'RET-2025-002',
                         [(m_souris, 1)])
        make_retour_pret(pret_2025_4, date(2025, 6, 10), 'Retour total – matériel intact', 'RET-2025-003',
                         [(m_bloc_note, 5), (m_stylo_r, 15)], close_pret=True)
        make_retour_pret(pret_2025_5, date(2025, 6, 15), 'Retour partiel – 4 chaises sur 6', 'RET-2025-004',
                         [(m_chaise, 4)])
        self.stdout.write('  Retours prêts 2025: 4 créés')

        # Retours fournisseurs 2025
        make_retour_fournisseur(f1, d_central, date(2025, 3, 20), 'Articles défectueux', [(m_stylo_b, 20)])
        make_retour_fournisseur(f2, d_central, date(2025, 4, 10), 'Non-conformité',       [(m_cart, 3)])
        make_retour_fournisseur(f3, d_central, date(2025, 5, 25), 'Excédent de stock',    [(m_deterg, 5)])
        make_retour_fournisseur(f4, d_central, date(2025, 8, 3),  'Erreur de livraison',  [(m_ecran, 1)])
        self.stdout.write('  Retours fournisseurs 2025: 4 créés')

        # ════════════════════════════════════════════════════════════
        #  EXERCICE 2026 — OUVERT (exercice en cours)
        # ════════════════════════════════════════════════════════════
        self.stdout.write('  --- EXERCICE 2026 (OUVERT) ---')

        # Achats 2026 (8)
        make_achat(f1, d_central, date(2026, 1, 8), 'FACT-2026-001', ex2026, [
            (m_papier,   120, '3600'),
            (m_stylo_b,  200, '260'),
            (m_stylo_n,  150, '260'),
            (m_classeur,  60, '850'),
        ])
        make_achat(f2, d_central, date(2026, 1, 20), 'FACT-2026-002', ex2026, [
            (m_toner,      6, '36000'),
            (m_cart,      12, '12500'),
            (m_ruban,      8, '4500'),
        ])
        make_achat(f7, d_central, date(2026, 2, 5), 'FACT-2026-003', ex2026, [
            (m_pc,         4, '900000'),
            (m_ecran,      6, '100000'),
            (m_hub_usb,    4, '8500'),
        ])
        make_achat(f3, d_central, date(2026, 2, 18), 'FACT-2026-004', ex2026, [
            (m_deterg,    30, '1900'),
            (m_gant,      40, '1600'),
            (m_masque,    80, '520'),
            (m_sac_pou,   10, '3200'),
        ])
        make_achat(f6, d_central, date(2026, 2, 25), 'FACT-2026-005', ex2026, [
            (m_chaise,    12, '48000'),
            (m_armoire,    2, '98000'),
        ])
        make_achat(f5, d_central, date(2026, 3, 1), 'FACT-2026-006', ex2026, [
            (m_cahier,    80, '620'),
            (m_bloc_note, 40, '470'),
            (m_chemise,   60, '480'),
            (m_enveloppe, 15, '2600'),
        ])
        make_achat(f4, d_central, date(2026, 3, 1), 'FACT-2026-007', ex2026, [
            (m_ampoule,   30, '2100'),
            (m_balai,     15, '3600'),
        ])
        make_achat(f8, d_central, date(2026, 3, 2), 'FACT-2026-008', ex2026, [
            (m_casque,    10, '9000'),
            (m_cle_usb,   20, '3800'),
        ])
        self.stdout.write('  Achats 2026: 8 créés')

        # Dons 2026 (4)
        make_don(don5, d_central, date(2026, 1, 15), 'DON-2026-001', [
            (m_tablette,  5, '290000'),
            (m_cle_usb,  20, '3500'),
        ])
        make_don(don2, d_central, date(2026, 2, 3), 'DON-2026-002', [
            (m_pc,        3, '950000'),
            (m_souris_w,  6, '6200'),
            (m_clavier_w, 4, '7500'),
        ])
        make_don(don3, d_central, date(2026, 2, 20), 'DON-2026-003', [
            (m_papier,   60, '3600'),
            (m_stylo_b, 100, '260'),
        ])
        make_don(don4, d_central, date(2026, 3, 1), 'DON-2026-004', [
            (m_tableau,  3, '48000'),
            (m_feutre,  20, '2600'),
            (m_efface,  10, '1600'),
        ])
        self.stdout.write('  Dons 2026: 4 créés')

        # Sorties 2026 (6)
        make_sortie('CONSOMMATION_2E_GROUPE', d_central, date(2026, 1, 31),
                    'Dotation janvier – Service Administration', 'BS-2026-0001',
                    [(m_papier, 15, 3600), (m_stylo_b, 40, 260)])
        make_sortie('CONSOMMATION_2E_GROUPE', d_central, date(2026, 2, 15),
                    'Dotation février – Service Informatique', 'BS-2026-0002',
                    [(m_toner, 2, 36000), (m_cart, 4, 12500)])
        make_sortie('AFFECTATION', d_central, date(2026, 2, 20),
                    'Affectation PCs neufs – salle de cours', 'AFF-2026-001',
                    [(m_pc, 3, 900000), (m_ecran, 3, 100000)])
        make_sortie('CONSOMMATION_2E_GROUPE', d_central, date(2026, 2, 28),
                    'Dotation février – Service RH', 'BS-2026-0003',
                    [(m_cahier, 20, 620), (m_bloc_note, 12, 470)])
        make_sortie('CONSOMMATION_2E_GROUPE', d_central, date(2026, 3, 1),
                    'Dotation mars – Service Pédagogie', 'BS-2026-0004',
                    [(m_feutre, 8, 2600), (m_efface, 5, 1600)])
        make_sortie('AFFECTATION', d_central, date(2026, 3, 3),
                    'Affectation EPI – Magasin Laboratoire', 'AFF-2026-002',
                    [(m_gant, 15, 1600), (m_masque, 30, 520), (m_casque, 5, 9000)])
        self.stdout.write('  Sorties 2026: 6 créées')

        # Transferts 2026 (4)
        make_transfert('AFFECTATION', d_central, d_bureau,
                       date(2026, 1, 10), 'Dotation annuelle Bureau Administration 2026',
                       [(m_papier, 25, 3600), (m_stylo_b, 40, 260), (m_classeur, 15, 850)])
        make_transfert('AFFECTATION', d_central, d_info,
                       date(2026, 1, 15), 'Dotation Magasin Informatique 2026',
                       [(m_souris, 6, 5000), (m_clavier, 5, 7500), (m_hub_usb, 2, 8500)])
        make_transfert('AFFECTATION', d_central, d_labo,
                       date(2026, 2, 8), 'Dotation Labo – protection et nettoyage',
                       [(m_gant, 20, 1600), (m_masque, 40, 520), (m_deterg, 10, 1900)])
        make_transfert('AFFECTATION', d_central, d_tech,
                       date(2026, 2, 12), 'Dotation Magasin Technique 2026',
                       [(m_ampoule, 15, 2100), (m_balai, 8, 3600), (m_sac_pou, 5, 3200)])
        self.stdout.write('  Transferts 2026: 4 créés')

        # Entrées externes 2026 (3)
        make_dotation(src_men, d_central, date(2026, 1, 5), 'DOT-MEN-2026-001',
                      'Dotation annuelle MEN 2026 – fournitures pédagogiques et bureau',
                      [(m_papier, 60, 3600), (m_stylo_b, 120, 260), (m_classeur, 30, 850)])
        make_dotation(src_usaid, d_central, date(2026, 2, 10), 'USAID-MINES-2026-002',
                      'Équipement pédagogique USAID – Projet Mines & Compétences',
                      [(m_tablette, 5, 290000), (m_cle_usb, 30, 3500), (m_ecran, 2, 100000)])
        make_dotation(src_afd, d_central, date(2026, 3, 1), 'AFD-GEOL-2026-005',
                      'Matériel laboratoire – Programme coopération AFD',
                      [(m_casque, 8, 9000), (m_gant, 25, 1600), (m_masque, 50, 520)])
        self.stdout.write('  Dotations 2026: 3 créées')

        # Prêts 2026 (4)
        pret_2026_1 = make_pret(s_info, d_central, date(2026, 1, 20),
                                'Prêt périphériques – formation nouveaux agents',
                                [(m_souris, 4), (m_clavier, 3)])
        pret_2026_2 = make_pret(s_ped, d_central, date(2026, 2, 5),
                                'Prêt matériel pédagogique – séminaire enseignants',
                                [(m_tablette, 3), (m_feutre, 6)])
        pret_2026_3 = make_pret(s_admin, d_central, date(2026, 2, 20),
                                'Prêt consommables urgence – Administration',
                                [(m_papier, 10), (m_stylo_b, 20)])
        pret_2026_4 = make_pret(s_labo, d_central, date(2026, 3, 2),
                                'Prêt EPI TP Laboratoire S1 2026',
                                [(m_gant, 12), (m_masque, 25)])
        self.stdout.write('  Prêts 2026: 4 créés')

        # Retours prêts 2026
        make_retour_pret(pret_2026_1, date(2026, 2, 1), 'Retour périphériques après formation', 'RET-2026-001',
                         [(m_souris, 4), (m_clavier, 3)], close_pret=True)
        make_retour_pret(pret_2026_3, date(2026, 3, 1), 'Retour partiel consommables Admin', 'RET-2026-002',
                         [(m_papier, 6), (m_stylo_b, 15)])
        self.stdout.write('  Retours prêts 2026: 2 créés')

        # Retours fournisseurs 2026
        make_retour_fournisseur(f1, d_central, date(2026, 1, 25),
                                'Stylos lots non conformes à la commande',
                                [(m_stylo_b, 30)])
        make_retour_fournisseur(f7, d_central, date(2026, 2, 28),
                                'Écrans rayés à la livraison',
                                [(m_ecran, 1)])
        self.stdout.write('  Retours fournisseurs 2026: 2 créés')

        # ════════════════════════════════════════════════════════════
        #  MOUVEMENTS DIRECTS — tous dépôts, tous exercices
        # ════════════════════════════════════════════════════════════
        MouvementStock = apps.get_model('inventory', 'MouvementStock')
        from django.utils import timezone as tz

        def _dt(d):
            return tz.make_aware(datetime.combine(d, datetime.min.time()))

        # ── 2023 : Mouvements secondaires ──
        for depot, lignes, d in [
            (d_bureau, [(m_papier, 15, Decimal('3000')), (m_stylo_b, 20, Decimal('200')), (m_classeur, 8, Decimal('750'))], date(2023, 1, 25)),
            (d_labo,   [(m_gant, 15, Decimal('1300')), (m_masque, 30, Decimal('450')), (m_casque, 4, Decimal('8000'))], date(2023, 4, 10)),
            (d_info,   [(m_souris, 4, Decimal('4500')), (m_clavier, 4, Decimal('7000'))], date(2023, 6, 1)),
        ]:
            for mat_obj, qte, cu in lignes:
                MouvementStock.objects.create(
                    type='ENTREE', date=_dt(d), exercice=ex2023,
                    matiere=mat_obj, depot=depot,
                    quantite=Decimal(str(qte)), cout_unitaire=cu, cout_total=Decimal(str(qte)) * cu,
                    reference=f'DOTATION-{depot.identifiant}-2023',
                    commentaire=f'Dotation initiale {depot.nom} 2023',
                )
        # Sorties 2023 dépôts secondaires
        for depot, mat_obj, qte, cu, d in [
            (d_bureau, m_papier,  4, Decimal('3000'), date(2023, 3, 15)),
            (d_info,   m_souris,  2, Decimal('4500'), date(2023, 7, 10)),
            (d_labo,   m_masque, 10, Decimal('450'),  date(2023, 9, 5)),
        ]:
            MouvementStock.objects.create(
                type='SORTIE', date=_dt(d), exercice=ex2023,
                matiere=mat_obj, depot=depot,
                quantite=Decimal(str(qte)), cout_unitaire=cu, cout_total=Decimal(str(qte)) * cu,
                reference=f'SORTIE-{depot.identifiant}-2023',
                commentaire=f'Consommation {depot.nom} 2023',
            )
        self.stdout.write('  Mouvements directs 2023: créés')

        # ── 2024 : Mouvements secondaires ──
        for depot, lignes, d in [
            (d_bureau, [(m_papier, 20, Decimal('3100')), (m_stylo_b, 30, Decimal('210')), (m_chemise, 20, Decimal('450'))], date(2024, 1, 20)),
            (d_info,   [(m_souris, 5, Decimal('4500')), (m_clavier, 4, Decimal('7000')), (m_cart, 4, Decimal('11500'))], date(2024, 3, 5)),
            (d_labo,   [(m_gant, 12, Decimal('1350')), (m_masque, 25, Decimal('450')), (m_deterg, 6, Decimal('1600'))], date(2024, 4, 15)),
            (d_tech,   [(m_ampoule, 8, Decimal('2000')), (m_deterg, 5, Decimal('1600')), (m_balai, 4, Decimal('3500'))], date(2024, 5, 1)),
        ]:
            for mat_obj, qte, cu in lignes:
                MouvementStock.objects.create(
                    type='ENTREE', date=_dt(d), exercice=ex2024,
                    matiere=mat_obj, depot=depot,
                    quantite=Decimal(str(qte)), cout_unitaire=cu, cout_total=Decimal(str(qte)) * cu,
                    reference=f'DOTATION-{depot.identifiant}-2024',
                    commentaire=f'Dotation initiale {depot.nom} 2024',
                )
        for depot, mat_obj, qte, cu, d in [
            (d_bureau, m_papier,  6, Decimal('3100'), date(2024, 4, 20)),
            (d_bureau, m_stylo_b,12, Decimal('210'),  date(2024, 6, 15)),
            (d_info,   m_souris,  3, Decimal('4500'), date(2024, 7, 1)),
            (d_labo,   m_masque, 12, Decimal('450'),  date(2024, 8, 5)),
            (d_tech,   m_ampoule, 4, Decimal('2000'), date(2024, 9, 10)),
        ]:
            MouvementStock.objects.create(
                type='SORTIE', date=_dt(d), exercice=ex2024,
                matiere=mat_obj, depot=depot,
                quantite=Decimal(str(qte)), cout_unitaire=cu, cout_total=Decimal(str(qte)) * cu,
                reference=f'SORTIE-{depot.identifiant}-2024',
                commentaire=f'Consommation {depot.nom} 2024',
            )
        # Ajustements 2024
        for depot, mat_obj, qte, cu, d, comment in [
            (d_central, m_papier,   8, Decimal('3100'), date(2024, 6, 30), 'Inventaire mi-exercice 2024'),
            (d_central, m_stylo_b, -3, Decimal('210'),  date(2024, 9, 30), 'Correction inventaire Q3 2024'),
            (d_labo,    m_gant,     4, Decimal('1350'), date(2024, 10, 15), 'Réception complémentaire 2024'),
        ]:
            MouvementStock.objects.create(
                type='AJUSTEMENT', date=_dt(d), exercice=ex2024,
                matiere=mat_obj, depot=depot,
                quantite=Decimal(str(abs(qte))), cout_unitaire=cu,
                cout_total=Decimal(str(abs(qte))) * cu,
                reference=f'AJU-{depot.identifiant}-2024',
                commentaire=comment,
            )
        self.stdout.write('  Mouvements directs 2024: créés')

        # ── 2025 : Mouvements secondaires ──
        for depot, lignes, d in [
            (d_bureau, [(m_papier, 20, Decimal('3500')), (m_stylo_b, 30, Decimal('250')), (m_classeur, 10, Decimal('800'))], date(2025, 2, 1)),
            (d_info,   [(m_souris, 5, Decimal('5000')), (m_clavier, 5, Decimal('7500')), (m_cart, 5, Decimal('12000'))], date(2025, 2, 5)),
            (d_labo,   [(m_gant, 20, Decimal('1500')), (m_masque, 30, Decimal('500'))], date(2025, 3, 10)),
            (d_tech,   [(m_ampoule, 10, Decimal('2000')), (m_deterg, 8, Decimal('1800'))], date(2025, 4, 1)),
        ]:
            for mat_obj, qte, cu in lignes:
                MouvementStock.objects.create(
                    type='ENTREE', date=_dt(d), exercice=ex2025,
                    matiere=mat_obj, depot=depot,
                    quantite=Decimal(str(qte)), cout_unitaire=cu, cout_total=Decimal(str(qte)) * cu,
                    reference=f'DOTATION-{depot.identifiant}-2025',
                    commentaire=f'Dotation initiale {depot.nom} 2025',
                )
        for depot, mat_obj, qte, cu, d in [
            (d_bureau, m_papier,   5, Decimal('3500'), date(2025, 4, 10)),
            (d_bureau, m_stylo_b, 10, Decimal('250'),  date(2025, 5, 15)),
            (d_info,   m_souris,   2, Decimal('5000'), date(2025, 6, 1)),
            (d_labo,   m_masque,  10, Decimal('500'),  date(2025, 7, 5)),
            (d_tech,   m_ampoule,  3, Decimal('2000'), date(2025, 8, 10)),
        ]:
            MouvementStock.objects.create(
                type='SORTIE', date=_dt(d), exercice=ex2025,
                matiere=mat_obj, depot=depot,
                quantite=Decimal(str(qte)), cout_unitaire=cu, cout_total=Decimal(str(qte)) * cu,
                reference=f'SORTIE-{depot.identifiant}-2025',
                commentaire=f'Consommation {depot.nom} 2025',
            )
        for depot, mat_obj, qte, cu, d, comment in [
            (d_central, m_papier,   5, Decimal('3500'), date(2025, 6, 30),  'Inventaire mi-exercice 2025'),
            (d_central, m_stylo_b, -2, Decimal('250'),  date(2025, 9, 30),  'Correction inventaire Q3 2025'),
            (d_labo,    m_gant,     3, Decimal('1500'), date(2025, 10, 15), 'Réception complémentaire 2025'),
            (d_tech,    m_deterg,  -1, Decimal('1800'), date(2025, 11, 1),  'Inventaire fin Q4 2025'),
        ]:
            MouvementStock.objects.create(
                type='AJUSTEMENT', date=_dt(d), exercice=ex2025,
                matiere=mat_obj, depot=depot,
                quantite=Decimal(str(abs(qte))), cout_unitaire=cu,
                cout_total=Decimal(str(abs(qte))) * cu,
                reference=f'AJU-{depot.identifiant}-2025',
                commentaire=comment,
            )
        self.stdout.write('  Mouvements directs 2025: créés')

        # ── 2026 : Mouvements secondaires ──
        for depot, lignes, d in [
            (d_bureau, [(m_papier, 25, Decimal('3600')), (m_stylo_b, 40, Decimal('260')), (m_classeur, 15, Decimal('850'))], date(2026, 1, 10)),
            (d_info,   [(m_souris, 6, Decimal('5000')), (m_clavier, 5, Decimal('7500')), (m_hub_usb, 2, Decimal('8500'))], date(2026, 1, 15)),
            (d_labo,   [(m_gant, 20, Decimal('1600')), (m_masque, 40, Decimal('520')), (m_deterg, 10, Decimal('1900'))], date(2026, 2, 8)),
            (d_tech,   [(m_ampoule, 15, Decimal('2100')), (m_balai, 8, Decimal('3600')), (m_sac_pou, 5, Decimal('3200'))], date(2026, 2, 12)),
        ]:
            for mat_obj, qte, cu in lignes:
                MouvementStock.objects.create(
                    type='ENTREE', date=_dt(d), exercice=ex2026,
                    matiere=mat_obj, depot=depot,
                    quantite=Decimal(str(qte)), cout_unitaire=cu, cout_total=Decimal(str(qte)) * cu,
                    reference=f'DOTATION-{depot.identifiant}-2026',
                    commentaire=f'Dotation initiale {depot.nom} 2026',
                )
        for depot, mat_obj, qte, cu, d in [
            (d_bureau, m_papier,   8, Decimal('3600'), date(2026, 2, 15)),
            (d_bureau, m_stylo_b, 15, Decimal('260'),  date(2026, 2, 28)),
            (d_info,   m_souris,   2, Decimal('5000'), date(2026, 2, 20)),
            (d_labo,   m_masque,  15, Decimal('520'),  date(2026, 2, 25)),
            (d_tech,   m_ampoule,  5, Decimal('2100'), date(2026, 3, 1)),
        ]:
            MouvementStock.objects.create(
                type='SORTIE', date=_dt(d), exercice=ex2026,
                matiere=mat_obj, depot=depot,
                quantite=Decimal(str(qte)), cout_unitaire=cu, cout_total=Decimal(str(qte)) * cu,
                reference=f'SORTIE-{depot.identifiant}-2026',
                commentaire=f'Consommation {depot.nom} – mars 2026',
            )
        self.stdout.write('  Mouvements directs 2026: créés')

        # ════════════════════════════════════════════════════════════
        #  UTILISATEURS ET GROUPES
        # ════════════════════════════════════════════════════════════
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group, Permission
        User = get_user_model()

        admin_group, _ = Group.objects.get_or_create(name='Administrateurs')
        agent_group, _ = Group.objects.get_or_create(name='Agents')
        chef_group, _ = Group.objects.get_or_create(name='Chefs de Service')

        agent_perms = (Permission.objects.filter(codename__startswith='view_') |
                       Permission.objects.filter(codename__startswith='add_')).exclude(
                           content_type__app_label='auth'
                       )
        agent_group.permissions.set(agent_perms)

        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={'is_superuser': True, 'is_staff': True, 'email': 'admin@ensmg.sn'}
        )
        if not admin_user.check_password('Admin@2025'):
            admin_user.set_password('Admin@2025')
            admin_user.save()

        testadmin_user, _ = User.objects.get_or_create(
            username='testadmin',
            defaults={'is_superuser': True, 'is_staff': True, 'email': 'testadmin@ensmg.sn'}
        )
        if not testadmin_user.check_password('Admin@2025'):
            testadmin_user.set_password('Admin@2025')
            testadmin_user.save()

        chef_user, _ = User.objects.get_or_create(
            username='chef_service',
            defaults={'is_staff': True, 'email': 'chef@ensmg.sn', 'first_name': 'Chef', 'last_name': 'Service'}
        )
        if not chef_user.check_password('Chef@2025'):
            chef_user.set_password('Chef@2025')
            chef_user.save()
        chef_user.groups.add(chef_group)

        agent_diallo, _ = User.objects.get_or_create(
            username='agent_diallo',
            defaults={'is_staff': True, 'email': 'diallo@ensmg.sn', 'first_name': 'Daouda', 'last_name': 'Diallo'}
        )
        if not agent_diallo.check_password('Agent@2025'):
            agent_diallo.set_password('Agent@2025')
            agent_diallo.save()
        agent_diallo.groups.add(agent_group)

        agent_ndiaye, _ = User.objects.get_or_create(
            username='agent_ndiaye',
            defaults={'is_staff': True, 'email': 'ndiaye@ensmg.sn', 'first_name': 'Fatoumata', 'last_name': 'Ndiaye'}
        )
        if not agent_ndiaye.check_password('Agent@2025'):
            agent_ndiaye.set_password('Agent@2025')
            agent_ndiaye.save()
        agent_ndiaye.groups.add(agent_group)

        admin_user.groups.add(admin_group)
        testadmin_user.groups.add(admin_group)
        self.stdout.write('  Utilisateurs: 5 créés/mis à jour')

        # ════════════════════════════════════════════════════════════
        #  PENDING RECORDS
        # ════════════════════════════════════════════════════════════
        PendingRecord = apps.get_model('core', 'PendingRecord')

        PendingRecord.objects.create(
            submitted_by=admin_user, app_label='purchasing', model_name='Achat',
            verbose_name='Achat fournitures bureau – Lot mars 2026',
            data={'fournisseur': 'Bureau Plus', 'montant': 187200},
            status=PendingRecord.Status.PENDING
        )
        PendingRecord.objects.create(
            submitted_by=admin_user, app_label='purchasing', model_name='Don',
            verbose_name='Don ordinateurs UNICEF – 3 unités',
            data={'donateur': 'UNICEF', 'quantite': 3},
            status=PendingRecord.Status.APPROVED,
            reviewed_by=admin_user, reviewed_at=timezone.now(),
            admin_comment='Accepté et enregistré en stock'
        )
        PendingRecord.objects.create(
            submitted_by=admin_user, app_label='inventory', model_name='OperationSortie',
            verbose_name='Sortie consommation fournitures – Service Technique',
            data={'type': 'CONSOMMATION_2E_GROUPE', 'montant': 8500},
            status=PendingRecord.Status.PENDING
        )
        PendingRecord.objects.create(
            submitted_by=admin_user, app_label='purchasing', model_name='RetourFournisseur',
            verbose_name='Retour écrans défectueux – TechAfrique',
            data={'fournisseur': 'TechAfrique', 'quantite': 1},
            status=PendingRecord.Status.REJECTED,
            reviewed_by=admin_user, reviewed_at=timezone.now(),
            admin_comment='Délai de retour dépassé selon contrat'
        )
        PendingRecord.objects.create(
            submitted_by=admin_user, app_label='purchasing', model_name='Pret',
            verbose_name='Prêt tablettes – séminaire AFD mars 2026',
            data={'service': 'Pédagogie', 'date': '2026-03-10'},
            status=PendingRecord.Status.PENDING
        )
        self.stdout.write('  PendingRecord: 5 créés')

        # ════════════════════════════════════════════════════════════
        #  RÉSUMÉ FINAL
        # ════════════════════════════════════════════════════════════
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('═══════════════════════════════════════════'))
        self.stdout.write(self.style.SUCCESS('RÉSUMÉ DES DONNÉES CHARGÉES (2023–2026):'))
        self.stdout.write(self.style.SUCCESS('═══════════════════════════════════════════'))
        self.stdout.write('  Exercices  : 4 (2023 CLOS, 2024 CLOS, 2025 CLOS, 2026 OUVERT)')
        self.stdout.write('  Unités     : 8')
        self.stdout.write('  Services   : 7')
        self.stdout.write('  Dépôts     : 5 (MAG-CENT, B-ADM-01, MAG-INF, MAG-LAB, MAG-TEC)')
        self.stdout.write('  Fournisseurs: 8')
        self.stdout.write('  Donateurs  : 5')
        self.stdout.write('  Sources ext: 6')
        self.stdout.write('  Matières   : 38 (CONSOMMABLE + IMMOBILISATION)')
        self.stdout.write('  ─────────────────────────────────────────')
        self.stdout.write('  Achats     : 30  (5+7+10+8 par exercice)')
        self.stdout.write('  Dons       : 15  (3+3+5+4 par exercice)')
        self.stdout.write('  Sorties    : 28  (5+7+10+6 par exercice)')
        self.stdout.write('  Transferts : 16  (3+4+5+4 par exercice)')
        self.stdout.write('  Dotations  : 10  (2+2+3+3 par exercice)')
        self.stdout.write('  Prêts      : 16  (3+4+5+4 par exercice)')
        self.stdout.write('  Retours prêt: 11 (2+3+4+2 par exercice)')
        self.stdout.write('  Ret. fourn.: 10 (2+2+4+2 par exercice)')
        self.stdout.write('  ─────────────────────────────────────────')
        self.stdout.write('  Mouvements directs: ENTREE + SORTIE + AJUSTEMENT par dépôt/exercice')
        self.stdout.write('  Utilisateurs: 5 (admin, testadmin, chef_service, agent_diallo, agent_ndiaye)')
        self.stdout.write('  PendingRecord: 5')
