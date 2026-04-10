"""
Django management command to create a rich test database for ENSMG Comptabilité Matières.

This command populates the database with:
- 4 fiscal years (2023-2026)
- Multiple services, depots, fournisseurs, donateurs
- Chart of accounts (ComptePrincipal, CompteDivisionnaire, SousCompte)
- Material categories and items
- 200+ movements per fiscal year including:
  - Purchases (Achat with LigneAchat)
  - Donations (Don with LigneDon)
  - External stock entries (ExternalStockEntry/LegsEntry)
  - Allocations (Dotation with LigneDotation)
  - Loans (Pret with LignePret)
  - Loan returns (RetourPret with LigneRetourPret)
  - Supplier returns (RetourFournisseur with LigneRetour)
  - Exit operations (OperationSortie with LigneOperationSortie)
  - Transfer operations (OperationTransfert with LigneOperationTransfert)

All authentication and system tables are preserved during database reset.
"""

import os
import sys
from decimal import Decimal
from collections import defaultdict
from datetime import datetime, timedelta
import random

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

# Core models
from core.models.exercice import Exercice
from core.models.service import Service
from core.models.depot import Depot
from core.models.fournisseur import Fournisseur
from core.models.donateur import Donateur
from core.models.external_source import ExternalSource
from core.models.fournisseur_sequence import FournisseurSequence

# Unite is in core, not catalog
from core.models.unite import Unite

# Catalog models
from catalog.models.compte import ComptePrincipal, CompteDivisionnaire, SousCompte
from catalog.models.categorie import Categorie
from catalog.models.souscategorie import SousCategorie
from catalog.models.matiere import Matiere

# Purchasing models
from purchasing.models.achat import Achat
from purchasing.models.ligne_achat import LigneAchat
from purchasing.models.don import Don, LigneDon
from purchasing.models.external_stock_entry import ExternalStockEntry
from purchasing.models.external_stock_entry_line import ExternalStockEntryLine
from purchasing.models.legs_entry import LegsEntry
from purchasing.models.dotation import Dotation, LigneDotation
from purchasing.models.pret import Pret, LignePret
from purchasing.models.retour_pret import RetourPret, LigneRetourPret
from purchasing.models.retour import RetourFournisseur
from purchasing.models.ligne_retour import LigneRetour

# Inventory models
from inventory.models.operation_sortie import OperationSortie, LigneOperationSortie
from inventory.models.operation_transfert import OperationTransfert, LigneOperationTransfert
from inventory.models.mouvement_stock import MouvementStock


class Command(BaseCommand):
    help = "Create a rich test database with 200+ movements per fiscal year (2023-2026)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-clear",
            action="store_true",
            help="Skip clearing existing data",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting database population..."))

        if not options["skip_clear"]:
            self.clear_database()

        self.rng = random.Random(42)
        self.stock_tracker = defaultdict(lambda: Decimal("0"))

        try:
            # Create base data
            self.create_exercices()
            self.create_services()
            self.create_depots()
            self.create_fournisseurs()
            self.create_donateurs()
            self.create_external_sources()
            self.create_unites()
            self.create_chart_of_accounts()
            self.create_categories()
            self.create_matieres()

            # Create movements for each fiscal year
            for year in [2023, 2024, 2025, 2026]:
                self.stdout.write(f"Creating movements for year {year}...")
                self.create_movements_for_year(year)

            self.stdout.write(self.style.SUCCESS("Database population completed successfully!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
            raise

    def clear_database(self):
        """Clear all data except auth tables, content type, and migrations."""
        self.stdout.write("Clearing database...")

        with connection.cursor() as cursor:
            # Disable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = OFF")

            # List of tables to preserve
            preserve_tables = {
                "auth_user",
                "auth_group",
                "auth_permission",
                "auth_user_groups",
                "auth_user_user_permissions",
                "django_content_type",
                "django_migrations",
                "django_admin_log",
            }

            # Get all tables
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            all_tables = cursor.fetchall()

            for (table_name,) in all_tables:
                if table_name not in preserve_tables:
                    try:
                        cursor.execute(f"DELETE FROM {table_name}")
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f"Could not clear {table_name}: {str(e)}")
                        )

            # Re-enable foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")
            connection.commit()

        self.stdout.write(self.style.SUCCESS("Database cleared"))

    def create_exercices(self):
        """Create fiscal years 2023-2026."""
        self.stdout.write("Creating exercices...")
        for year in [2023, 2024, 2025, 2026]:
            Exercice.objects.get_or_create(
                annee=year,
                defaults={"statut": "OUVERT" if year == 2026 else "CLOS"},
            )

    def create_services(self):
        """Create administrative services."""
        self.stdout.write("Creating services...")
        self.services = []
        service_data = [
            {"code": "DIR", "libelle": "Direction", "responsable": "Dr. Mamadou Sall"},
            {"code": "LOG", "libelle": "Logistique", "responsable": "Mr. Ousmane Diallo"},
            {"code": "REC", "libelle": "Recherche", "responsable": "Prof. Fatou Gueye"},
            {
                "code": "ENS",
                "libelle": "Enseignement",
                "responsable": "Prof. Amadou Ba",
            },
            {
                "code": "ADM",
                "libelle": "Administration",
                "responsable": "Ms. Aissatou Ndiaye",
            },
        ]
        for data in service_data:
            service, _ = Service.objects.get_or_create(
                code=data["code"],
                defaults={
                    "libelle": data["libelle"],
                    "responsable": data["responsable"],
                    "actif": True,
                },
            )
            self.services.append(service)

    def create_depots(self):
        """Create depots and bureaux."""
        self.stdout.write("Creating depots...")
        self.depots = []

        # Main depot
        depot, _ = Depot.objects.get_or_create(
            identifiant="DEP001",
            defaults={
                "nom": "Dépôt Principal",
                "type_lieu": "DEPOT",
                "responsable": "Mr. Ousmane Diallo",
                "actif": True,
            },
        )
        self.depots.append(depot)

        # Secondary depots
        secondary_depots = [
            {"identifiant": "DEP002", "nom": "Dépôt Chimie"},
            {"identifiant": "DEP003", "nom": "Dépôt Géologie"},
            {"identifiant": "DEP004", "nom": "Dépôt Informatique"},
        ]

        for data in secondary_depots:
            depot, _ = Depot.objects.get_or_create(
                identifiant=data["identifiant"],
                defaults={
                    "nom": data["nom"],
                    "type_lieu": "DEPOT",
                    "responsable": "Mr. Ousmane Diallo",
                    "actif": True,
                },
            )
            self.depots.append(depot)

        # Bureau locations (linked to services)
        bureau_data = [
            {"identifiant": "BUR001", "nom": "Bureau Direction", "service": self.services[0]},
            {"identifiant": "BUR002", "nom": "Bureau Logistique", "service": self.services[1]},
            {"identifiant": "BUR003", "nom": "Bureau Recherche", "service": self.services[2]},
        ]

        for data in bureau_data:
            bureau, _ = Depot.objects.get_or_create(
                identifiant=data["identifiant"],
                defaults={
                    "nom": data["nom"],
                    "type_lieu": "BUREAU",
                    "service": data["service"],
                    "responsable": data["service"].responsable,
                    "actif": True,
                },
            )
            self.depots.append(bureau)

    def create_fournisseurs(self):
        """Create suppliers."""
        self.stdout.write("Creating fournisseurs...")
        self.fournisseurs = []
        fournisseur_data = [
            {
                "raison_sociale": "Agro-Import Senegal",
                "adresse": "Dakar",
                "numero": "+221-33-822-1234",
                "ninea": "000000000000001",
            },
            {
                "raison_sociale": "Chimie Plus",
                "adresse": "Thiès",
                "numero": "+221-33-951-5678",
                "ninea": "000000000000002",
            },
            {
                "raison_sociale": "Geo Equipments",
                "adresse": "Dakar",
                "numero": "+221-33-823-9999",
                "ninea": "000000000000003",
            },
            {
                "raison_sociale": "Lab Supplies International",
                "adresse": "Abidjan, Côte d'Ivoire",
                "numero": "+225-22-222-2222",
                "ninea": "000000000000004",
            },
            {
                "raison_sociale": "Senegal Industrial",
                "adresse": "Kaolack",
                "numero": "+221-33-941-1111",
                "ninea": "000000000000005",
            },
            {
                "raison_sociale": "West Africa Trading",
                "adresse": "Bamako, Mali",
                "numero": "+223-76-000-0000",
                "ninea": "000000000000006",
            },
        ]

        for data in fournisseur_data:
            fournisseur, _ = Fournisseur.objects.get_or_create(
                ninea=data["ninea"],
                defaults={
                    "raison_sociale": data["raison_sociale"],
                    "adresse": data["adresse"],
                    "numero": data["numero"],
                },
            )
            self.fournisseurs.append(fournisseur)

    def create_donateurs(self):
        """Create donors."""
        self.stdout.write("Creating donateurs...")
        self.donateurs = []
        donateur_data = [
            {
                "raison_sociale": "Fondation Gates",
                "adresse": "Seattle, USA",
                "telephone": "+1-206-555-0001",
            },
            {
                "raison_sociale": "UNESCO Senegal",
                "adresse": "Dakar",
                "telephone": "+221-33-889-0001",
            },
            {
                "raison_sociale": "Agence Française Développement",
                "adresse": "Paris, France",
                "telephone": "+33-1-5305-5005",
            },
            {
                "raison_sociale": "Union Africaine",
                "adresse": "Addis Abéba, Éthiopie",
                "telephone": "+251-11-551-7700",
            },
            {
                "raison_sociale": "Programme Alimentaire Mondial",
                "adresse": "Rome, Italie",
                "telephone": "+39-06-5459-2111",
            },
        ]

        for data in donateur_data:
            donateur, _ = Donateur.objects.get_or_create(
                raison_sociale=data["raison_sociale"],
                defaults={
                    "adresse": data["adresse"],
                    "telephone": data["telephone"],
                    "actif": True,
                },
            )
            self.donateurs.append(donateur)

    def create_external_sources(self):
        """Create external stock sources."""
        self.stdout.write("Creating external sources...")
        self.external_sources = []
        source_data = [
            {"name": "Ministry of Education", "acronym": "MOE", "source_type": "MINISTRY"},
            {"name": "UNDP", "acronym": "UNDP", "source_type": "PARTNER"},
            {"name": "World Bank", "acronym": "WB", "source_type": "PARTNER"},
            {
                "name": "Legacy from Dr. Seck",
                "acronym": "LEGS-SECK",
                "source_type": "LEGS",
            },
            {"name": "Partner University Gift", "acronym": "PUG", "source_type": "OTHER"},
        ]

        for data in source_data:
            source, _ = ExternalSource.objects.get_or_create(
                name=data["name"],
                defaults={
                    "acronym": data["acronym"],
                    "source_type": data["source_type"],
                },
            )
            self.external_sources.append(source)

    def create_unites(self):
        """Create measurement units."""
        self.stdout.write("Creating unites...")
        self.unites = []
        unite_data = [
            {"abreviation": "KG", "libelle": "Kilogramme"},
            {"abreviation": "L", "libelle": "Litre"},
            {"abreviation": "M", "libelle": "Mètre"},
            {"abreviation": "M2", "libelle": "Mètre carré"},
            {"abreviation": "M3", "libelle": "Mètre cube"},
            {"abreviation": "UN", "libelle": "Unité"},
            {"abreviation": "BOX", "libelle": "Boîte"},
            {"abreviation": "SAC", "libelle": "Sac"},
            {"abreviation": "JRN", "libelle": "Jour/Homme"},
            {"abreviation": "H", "libelle": "Heure"},
        ]

        for data in unite_data:
            unite, _ = Unite.objects.get_or_create(
                abreviation=data["abreviation"],
                defaults={"libelle": data["libelle"]},
            )
            self.unites.append(unite)

    def create_chart_of_accounts(self):
        """Create chart of accounts.

        Les codes sont auto-générés par le modèle (save()) :
          - ComptePrincipal  : G1 → 10-19, G2 → 20-29
          - CompteDivisionnaire : {principal.code}.01, .02 …
          - SousCompte : {div.code}.01, .02 …
        On ne passe donc jamais de code explicite à get_or_create.
        """
        self.stdout.write("Creating chart of accounts...")
        self.comptes_divisionnaires = []

        # Comptes principaux – codes auto-générés dans save()
        main_accounts = [
            {"libelle": "Acquisitions et entrées en stock",  "groupe": "G1"},
            {"libelle": "Dotations et dons reçus",           "groupe": "G1"},
            {"libelle": "Sorties et consommations",          "groupe": "G2"},
            {"libelle": "Transferts et prêts",               "groupe": "G2"},
        ]

        for main_data in main_accounts:
            compte_principal, _ = ComptePrincipal.objects.get_or_create(
                libelle=main_data["libelle"],
                defaults={
                    "groupe": main_data["groupe"],
                    "actif": True,
                },
            )

            # Comptes divisionnaires – codes auto-générés dans save()
            div_libelles = [
                f"{main_data['libelle']} - Catégorie A",
                f"{main_data['libelle']} - Catégorie B",
                f"{main_data['libelle']} - Catégorie C",
                f"{main_data['libelle']} - Catégorie D",
            ]
            for div_libelle in div_libelles:
                compte_div, _ = CompteDivisionnaire.objects.get_or_create(
                    compte_principal=compte_principal,
                    libelle=div_libelle,
                    defaults={"actif": True},
                )
                self.comptes_divisionnaires.append(compte_div)

                # Sous-comptes – codes auto-générés dans save()
                for i in range(1, 4):
                    SousCompte.objects.get_or_create(
                        compte_divisionnaire=compte_div,
                        libelle=f"Sous-compte {div_libelle} - {i}",
                        defaults={"actif": True},
                    )

    def create_categories(self):
        """Create material categories."""
        self.stdout.write("Creating categories...")
        self.matieres = []
        self.sous_comptes_by_id = {}

        category_data = [
            {
                "libelle": "Produits Chimiques",
                "sous_categories": ["Acides", "Bases", "Solvants"],
            },
            {
                "libelle": "Équipements de Laboratoire",
                "sous_categories": ["Verrerie", "Instruments", "Accessoires"],
            },
            {
                "libelle": "Matériaux Géologiques",
                "sous_categories": ["Minéraux", "Roches", "Fossiles"],
            },
            {
                "libelle": "Fournitures de Bureau",
                "sous_categories": ["Papier", "Stylos", "Classement"],
            },
            {
                "libelle": "Équipements Informatiques",
                "sous_categories": ["Ordinateurs", "Périphériques", "Logiciels"],
            },
        ]

        for cat_data in category_data:
            categorie, _ = Categorie.objects.get_or_create(
                libelle=cat_data["libelle"],
                defaults={"actif": True},
            )

            for sous_cat_libelle in cat_data["sous_categories"]:
                sous_categorie, _ = SousCategorie.objects.get_or_create(
                    categorie=categorie,
                    libelle=sous_cat_libelle,
                    defaults={"actif": True},
                )

    def create_matieres(self):
        """Create material items with stock initialization."""
        self.stdout.write("Creating matieres...")
        self.matieres_list = []

        matiere_data = [
            # Produits Chimiques - Acides
            {
                "code_court": "HCL001",
                "designation": "Acide Chlorhydrique 37%",
                "type_matiere": "consommable",
                "categorie_libelle": "Produits Chimiques",
                "sous_categorie_libelle": "Acides",
                "unite_abrev": "L",
                "prix_unitaire": Decimal("8500"),
            },
            {
                "code_court": "HSO001",
                "designation": "Acide Sulfurique 98%",
                "type_matiere": "consommable",
                "categorie_libelle": "Produits Chimiques",
                "sous_categorie_libelle": "Acides",
                "unite_abrev": "L",
                "prix_unitaire": Decimal("12000"),
            },
            {
                "code_court": "HNO001",
                "designation": "Acide Nitrique 69%",
                "type_matiere": "consommable",
                "categorie_libelle": "Produits Chimiques",
                "sous_categorie_libelle": "Acides",
                "unite_abrev": "L",
                "prix_unitaire": Decimal("15000"),
            },
            # Produits Chimiques - Bases
            {
                "code_court": "NAOH01",
                "designation": "Hydroxyde de Sodium",
                "type_matiere": "consommable",
                "categorie_libelle": "Produits Chimiques",
                "sous_categorie_libelle": "Bases",
                "unite_abrev": "KG",
                "prix_unitaire": Decimal("5000"),
            },
            {
                "code_court": "KMNO01",
                "designation": "Permanganate de Potassium",
                "type_matiere": "consommable",
                "categorie_libelle": "Produits Chimiques",
                "sous_categorie_libelle": "Bases",
                "unite_abrev": "KG",
                "prix_unitaire": Decimal("25000"),
            },
            # Produits Chimiques - Solvants
            {
                "code_court": "ETH001",
                "designation": "Éthanol 96%",
                "type_matiere": "consommable",
                "categorie_libelle": "Produits Chimiques",
                "sous_categorie_libelle": "Solvants",
                "unite_abrev": "L",
                "prix_unitaire": Decimal("18000"),
            },
            {
                "code_court": "ACE001",
                "designation": "Acétone",
                "type_matiere": "consommable",
                "categorie_libelle": "Produits Chimiques",
                "sous_categorie_libelle": "Solvants",
                "unite_abrev": "L",
                "prix_unitaire": Decimal("7500"),
            },
            # Équipements de Laboratoire - Verrerie
            {
                "code_court": "BALM01",
                "designation": "Ballon monocol 500ml",
                "type_matiere": "reutilisable",
                "categorie_libelle": "Équipements de Laboratoire",
                "sous_categorie_libelle": "Verrerie",
                "unite_abrev": "UN",
                "prix_unitaire": Decimal("12000"),
            },
            {
                "code_court": "FLAK01",
                "designation": "Fiole jaugée 100ml",
                "type_matiere": "reutilisable",
                "categorie_libelle": "Équipements de Laboratoire",
                "sous_categorie_libelle": "Verrerie",
                "unite_abrev": "UN",
                "prix_unitaire": Decimal("8500"),
            },
            {
                "code_court": "BURR01",
                "designation": "Burette 25ml",
                "type_matiere": "reutilisable",
                "categorie_libelle": "Équipements de Laboratoire",
                "sous_categorie_libelle": "Verrerie",
                "unite_abrev": "UN",
                "prix_unitaire": Decimal("15000"),
            },
            # Équipements de Laboratoire - Instruments
            {
                "code_court": "THERM01",
                "designation": "Thermomètre -10 à 110°C",
                "type_matiere": "reutilisable",
                "categorie_libelle": "Équipements de Laboratoire",
                "sous_categorie_libelle": "Instruments",
                "unite_abrev": "UN",
                "prix_unitaire": Decimal("5000"),
            },
            {
                "code_court": "PH001",
                "designation": "Papier pH",
                "type_matiere": "consommable",
                "categorie_libelle": "Équipements de Laboratoire",
                "sous_categorie_libelle": "Instruments",
                "unite_abrev": "BOX",
                "prix_unitaire": Decimal("3500"),
            },
            # Matériaux Géologiques
            {
                "code_court": "MINQ01",
                "designation": "Cristaux de Quartz",
                "type_matiere": "reutilisable",
                "categorie_libelle": "Matériaux Géologiques",
                "sous_categorie_libelle": "Minéraux",
                "unite_abrev": "KG",
                "prix_unitaire": Decimal("45000"),
            },
            {
                "code_court": "MINC01",
                "designation": "Cristaux de Calcite",
                "type_matiere": "reutilisable",
                "categorie_libelle": "Matériaux Géologiques",
                "sous_categorie_libelle": "Minéraux",
                "unite_abrev": "KG",
                "prix_unitaire": Decimal("35000"),
            },
            {
                "code_court": "GRAN01",
                "designation": "Granite Échantillon",
                "type_matiere": "reutilisable",
                "categorie_libelle": "Matériaux Géologiques",
                "sous_categorie_libelle": "Roches",
                "unite_abrev": "UN",
                "prix_unitaire": Decimal("25000"),
            },
            # Fournitures de Bureau
            {
                "code_court": "PAP001",
                "designation": "Papier A4 80gr 500 feuilles",
                "type_matiere": "consommable",
                "categorie_libelle": "Fournitures de Bureau",
                "sous_categorie_libelle": "Papier",
                "unite_abrev": "BOX",
                "prix_unitaire": Decimal("6500"),
            },
            {
                "code_court": "STYL01",
                "designation": "Stylo à bille Bleu",
                "type_matiere": "consommable",
                "categorie_libelle": "Fournitures de Bureau",
                "sous_categorie_libelle": "Stylos",
                "unite_abrev": "BOX",
                "prix_unitaire": Decimal("4000"),
            },
            # Équipements Informatiques
            {
                "code_court": "ORDI01",
                "designation": "Ordinateur Portable Dell",
                "type_matiere": "reutilisable",
                "categorie_libelle": "Équipements Informatiques",
                "sous_categorie_libelle": "Ordinateurs",
                "unite_abrev": "UN",
                "prix_unitaire": Decimal("850000"),
            },
            {
                "code_court": "SOURIS01",
                "designation": "Souris Logitech Sans fil",
                "type_matiere": "reutilisable",
                "categorie_libelle": "Équipements Informatiques",
                "sous_categorie_libelle": "Périphériques",
                "unite_abrev": "UN",
                "prix_unitaire": Decimal("25000"),
            },
        ]

        for m_data in matiere_data:
            categorie = Categorie.objects.get(libelle=m_data["categorie_libelle"])
            sous_categorie = SousCategorie.objects.get(
                categorie=categorie,
                libelle=m_data["sous_categorie_libelle"],
            )
            sous_compte = SousCompte.objects.filter(actif=True).first()
            unite = Unite.objects.get(abreviation=m_data["unite_abrev"])

            matiere, _ = Matiere.objects.get_or_create(
                code_court=m_data["code_court"],
                defaults={
                    "designation": m_data["designation"],
                    "type_matiere": m_data["type_matiere"],
                    "sous_categorie": sous_categorie,
                    "categorie": categorie,
                    "sous_compte": sous_compte,
                    "unite": unite,
                    "est_stocke": True,
                    "actif": True,
                },
            )
            self.matieres_list.append((matiere, m_data["prix_unitaire"]))

    def create_initial_stock(self, year):
        """Initialize generous stock at start of each fiscal year."""
        self.stdout.write(f"Creating initial stock for year {year}...")
        
        depot_main = self.depots[0]  # Main depot
        
        for matiere, prix_unitaire in self.matieres_list:
            # Give generous initial quantities depending on type
            if matiere.type_matiere == "consommable":
                quantity = Decimal(str(self.rng.randint(100, 500)))
            else:
                quantity = Decimal(str(self.rng.randint(5, 50)))
            
            # Create initial stock movement
            MouvementStock.objects.create(
                matiere=matiere,
                depot=depot_main,
                type="ENTREE",
                quantite=quantity,
                cout_unitaire=prix_unitaire,
                is_stock_initial=True,
                date=datetime(year, 1, 1),
                reference="INIT-" + str(year),
            )
            
            # Track in memory
            self.stock_tracker[(matiere.id, depot_main.id)] = quantity

    def create_movements_for_year(self, year):
        """Create all movements (200+) for a fiscal year."""
        self.create_initial_stock(year)
        
        # Create FournisseurSequence for each supplier
        for fournisseur in self.fournisseurs:
            FournisseurSequence.objects.get_or_create(
                fournisseur=fournisseur,
                annee=year,
                type_doc="ACH",
                defaults={"next_seq": 1},
            )
        
        movements_created = 0
        
        # 50 Purchases
        movements_created += self.create_achats(year)
        
        # 15 Donations
        movements_created += self.create_dons(year)
        
        # 10 External stock entries / Legs entries
        movements_created += self.create_external_stock_entries(year)
        
        # 12 Allocations
        movements_created += self.create_dotations(year)
        
        # 25 Loans
        movements_created += self.create_prets(year)
        
        # 15 Loan returns
        movements_created += self.create_retour_prets(year)
        
        # 8 Supplier returns
        movements_created += self.create_retour_fournisseurs(year)
        
        # 40 Exit operations
        movements_created += self.create_operation_sorties(year)
        
        # 25 Transfer operations
        movements_created += self.create_operation_transferts(year)
        
        self.stdout.write(
            self.style.SUCCESS(f"Created {movements_created} movements for year {year}")
        )

    def create_achats(self, year):
        """Create 50 purchases per year."""
        count = 0
        nb_achats = 50
        
        for i in range(nb_achats):
            fournisseur = self.rng.choice(self.fournisseurs)
            depot = self.rng.choice(self.depots)
            
            date_achat = self._random_date(year)
            numero_facture = f"FACT-{fournisseur.code_prefix}-{year}-{i+1:04d}"
            
            achat = Achat.objects.create(
                fournisseur=fournisseur,
                date_achat=date_achat,
                depot=depot,
                numero_facture=numero_facture,
                tva_active=self.rng.choice([True, False]),
                commentaire=f"Achat {i+1} auprès de {fournisseur.raison_sociale}",
            )
            
            # Create 2-4 ligne achats
            num_lignes = self.rng.randint(2, 4)
            for j in range(num_lignes):
                matiere, prix_unitaire = self.rng.choice(self.matieres_list)
                quantite = Decimal(str(self.rng.randint(5, 100)))
                
                LigneAchat.objects.create(
                    achat=achat,
                    matiere=matiere,
                    quantite=quantite,
                    prix_unitaire=prix_unitaire,
                    appreciation="BON",
                )
                
                # Update stock tracker
                key = (matiere.id, depot.id)
                self.stock_tracker[key] += quantite
                
                # Create stock movement
                MouvementStock.objects.create(
                    matiere=matiere,
                    depot=depot,
                    type="ENTREE",
                    quantite=quantite,
                    cout_unitaire=prix_unitaire,
                    date=date_achat,
                    reference=achat.code,
                )
            
            count += 1
        
        return count

    def create_dons(self, year):
        """Create 15 donations per year."""
        count = 0
        nb_dons = 15
        
        for i in range(nb_dons):
            donateur = self.rng.choice(self.donateurs)
            depot = self.rng.choice(self.depots)
            
            date_don = self._random_date(year)
            
            don = Don.objects.create(
                donateur=donateur,
                date_don=date_don,
                depot=depot,
                commentaire=f"Don de {donateur.raison_sociale} - {i+1}",
            )
            
            # Create 2-4 ligne dons
            num_lignes = self.rng.randint(2, 4)
            for j in range(num_lignes):
                matiere, prix_unitaire = self.rng.choice(self.matieres_list)
                quantite = Decimal(str(self.rng.randint(5, 50)))
                
                LigneDon.objects.create(
                    don=don,
                    matiere=matiere,
                    quantite=quantite,
                    prix_unitaire=prix_unitaire,
                    observation="Reçu en bon état",
                )
                
                # Update stock
                key = (matiere.id, depot.id)
                self.stock_tracker[key] += quantite
                
                # Create stock movement
                MouvementStock.objects.create(
                    matiere=matiere,
                    depot=depot,
                    type="ENTREE",
                    quantite=quantite,
                    cout_unitaire=prix_unitaire,
                    date=date_don,
                    reference=don.code,
                )
            
            count += 1
        
        return count

    def create_external_stock_entries(self, year):
        """Create 10 external stock entries and legs entries per year."""
        count = 0
        nb_entries = 10
        
        for i in range(nb_entries):
            is_legs = self.rng.choice([True, False])
            
            if is_legs:
                # Use LEGS source
                source = next(
                    (s for s in self.external_sources if s.source_type == "LEGS"), 
                    self.external_sources[0]
                )
            else:
                # Use other sources
                source = self.rng.choice(
                    [s for s in self.external_sources if s.source_type != "LEGS"]
                )
            
            depot = self.rng.choice(self.depots)
            received_date = self._random_date(year)
            document_number = f"EXT-{i+1:04d}-{year}"
            
            entry = ExternalStockEntry.objects.create(
                source=source,
                received_date=received_date,
                depot=depot,
                document_number=document_number,
                comment=f"Entrée externe de {source.name}",
            )
            
            # Create 2-3 lignes
            num_lignes = self.rng.randint(2, 3)
            for j in range(num_lignes):
                matiere, prix_unitaire = self.rng.choice(self.matieres_list)
                quantity = Decimal(str(self.rng.randint(5, 100)))
                
                ExternalStockEntryLine.objects.create(
                    entry=entry,
                    matiere=matiere,
                    quantity=quantity,
                    unit_price=prix_unitaire,
                    note="Entrée reçue en bon état",
                )
                
                # Update stock
                key = (matiere.id, depot.id)
                self.stock_tracker[key] += quantity
                
                # Create stock movement
                MouvementStock.objects.create(
                    matiere=matiere,
                    depot=depot,
                    type="ENTREE",
                    quantite=quantity,
                    cout_unitaire=prix_unitaire,
                    date=received_date,
                    reference=entry.code,
                )
            
            count += 1
        
        return count

    def create_dotations(self, year):
        """Create 12 allocations per year."""
        count = 0
        nb_dotations = 12
        
        type_dotations = ["1ER_GROUPE", "2EME_GROUPE"]
        
        for i in range(nb_dotations):
            depot = self.rng.choice(self.depots)
            beneficiaire = self.rng.choice(self.services).responsable
            
            date_dotation = self._random_date(year)
            
            dotation = Dotation.objects.create(
                date=date_dotation,
                depot=depot,
                type_dotation=self.rng.choice(type_dotations),
                beneficiaire=beneficiaire,
                comment=f"Dotation {i+1} année {year}",
            )
            
            # Create 2-3 lignes
            num_lignes = self.rng.randint(2, 3)
            for j in range(num_lignes):
                matiere, prix_unitaire = self.rng.choice(self.matieres_list)
                quantity = Decimal(str(self.rng.randint(5, 100)))
                
                LigneDotation.objects.create(
                    dotation=dotation,
                    matiere=matiere,
                    quantity=quantity,
                    unit_price=prix_unitaire,
                    note="Dotation allouée",
                )
                
                # Update stock
                key = (matiere.id, depot.id)
                self.stock_tracker[key] += quantity
                
                # Create stock movement
                MouvementStock.objects.create(
                    matiere=matiere,
                    depot=depot,
                    type="ENTREE",
                    quantite=quantity,
                    cout_unitaire=prix_unitaire,
                    date=date_dotation,
                    reference=dotation.code,
                )
            
            count += 1
        
        return count

    def create_prets(self, year):
        """Create 25 loans per year (at least 15 marked as closed)."""
        count = 0
        nb_prets = 25
        
        for i in range(nb_prets):
            service = self.rng.choice(self.services)
            depot = self.rng.choice(self.depots)
            
            date_pret = self._random_date(year)
            
            pret = Pret.objects.create(
                service=service,
                date_pret=date_pret,
                depot=depot,
                commentaire=f"Prêt au service {service.libelle}",
            )
            
            # Mark first 15+ as closed
            if i < 15:
                pret.est_clos = True
                pret.save()
            
            # Create 2-3 lignes
            num_lignes = self.rng.randint(2, 3)
            for j in range(num_lignes):
                matiere, _ = self.rng.choice(self.matieres_list)
                quantite = Decimal(str(self.rng.randint(2, 20)))
                
                # Check stock availability
                key = (matiere.id, depot.id)
                available = self.stock_tracker[key]
                
                if available >= quantite:
                    LignePret.objects.create(
                        pret=pret,
                        matiere=matiere,
                        quantite=quantite,
                        observation="Prêt enregistré",
                    )
                    
                    # Remove from stock
                    self.stock_tracker[key] -= quantite
                    
                    # Create stock movement
                    MouvementStock.objects.create(
                        matiere=matiere,
                        depot=depot,
                        type="SORTIE",
                        quantite=quantite,
                        date=date_pret,
                        reference=pret.code,
                    )
            
            count += 1
        
        return count

    def create_retour_prets(self, year):
        """Create 15 loan returns for closed loans."""
        count = 0
        
        closed_prets = Pret.objects.filter(est_clos=True)[:15]
        
        for pret in closed_prets:
            date_retour = pret.date_pret + timedelta(days=self.rng.randint(30, 180))
            
            if date_retour.year != year:
                continue
            
            retour = RetourPret.objects.create(
                pret=pret,
                date_retour=date_retour,
                commentaire="Retour du prêt",
            )
            
            # Return materials from original pret
            for ligne_pret in pret.lignes.all():
                LigneRetourPret.objects.create(
                    retour=retour,
                    matiere=ligne_pret.matiere,
                    quantite=ligne_pret.quantite,
                    observation="Retour OK",
                )
                
                # Restore stock
                key = (ligne_pret.matiere.id, pret.depot.id)
                self.stock_tracker[key] += ligne_pret.quantite
                
                # Create stock movement (retour de prêt = coût nul)
                MouvementStock.objects.create(
                    matiere=ligne_pret.matiere,
                    depot=pret.depot,
                    type="ENTREE",
                    quantite=ligne_pret.quantite,
                    cout_unitaire=Decimal("0"),
                    date=date_retour,
                    reference=retour.code,
                )
            
            count += 1
        
        return count

    def create_retour_fournisseurs(self, year):
        """Create 8 supplier returns per year."""
        count = 0
        nb_retours = 8
        
        for i in range(nb_retours):
            fournisseur = self.rng.choice(self.fournisseurs)
            depot = self.rng.choice(self.depots)
            
            date_retour = self._random_date(year)
            
            retour = RetourFournisseur.objects.create(
                fournisseur=fournisseur,
                date_retour=date_retour,
                depot=depot,
                commentaire=f"Retour au fournisseur {fournisseur.raison_sociale}",
            )
            
            # Create 1-2 lignes
            num_lignes = self.rng.randint(1, 2)
            for j in range(num_lignes):
                matiere, _ = self.rng.choice(self.matieres_list)
                quantite = Decimal(str(self.rng.randint(2, 20)))
                
                # Check stock
                key = (matiere.id, depot.id)
                available = self.stock_tracker[key]
                
                if available >= quantite:
                    LigneRetour.objects.create(
                        retour=retour,
                        matiere=matiere,
                        quantite=quantite,
                    )
                    
                    # Remove from stock
                    self.stock_tracker[key] -= quantite
                    
                    # Create stock movement
                    MouvementStock.objects.create(
                        matiere=matiere,
                        depot=depot,
                        type="SORTIE",
                        quantite=quantite,
                        date=date_retour,
                        reference=retour.code,
                    )
            
            count += 1
        
        return count

    def create_operation_sorties(self, year):
        """Create 40 exit operations per year."""
        count = 0
        nb_sorties = 40
        
        sortie_types = [
            "REFORME_DESTRUCTION",
            "PERTE_VOL_DEFICIT",
            "CONSOMMATION_2E_GROUPE",
            "CERTIFICAT_ADMIN",
            "FIN_GESTION",
            "VENTE",
        ]
        
        for i in range(nb_sorties):
            depot = self.rng.choice(self.depots)
            type_sortie = self.rng.choice(sortie_types)
            
            date_sortie = self._random_date(year)
            
            operation = OperationSortie.objects.create(
                type_sortie=type_sortie,
                date_sortie=date_sortie,
                depot=depot,
                motif_principal=f"Motif {type_sortie}",
            )
            
            # Create 2-3 lignes
            num_lignes = self.rng.randint(2, 3)
            for j in range(num_lignes):
                matiere, prix_unitaire = self.rng.choice(self.matieres_list)
                quantite = Decimal(str(self.rng.randint(1, 20)))
                
                # Check stock
                key = (matiere.id, depot.id)
                available = self.stock_tracker[key]
                
                if available >= quantite:
                    LigneOperationSortie.objects.create(
                        operation=operation,
                        matiere=matiere,
                        quantite=quantite,
                        prix_unitaire=prix_unitaire,
                        commentaire=f"Sortie - {type_sortie}",
                    )
                    
                    # Remove from stock
                    self.stock_tracker[key] -= quantite
                    
                    # Create stock movement
                    MouvementStock.objects.create(
                        matiere=matiere,
                        depot=depot,
                        type="SORTIE",
                        quantite=quantite,
                        cout_unitaire=prix_unitaire,
                        date=date_sortie,
                        reference=operation.code,
                    )
            
            count += 1
        
        return count

    def create_operation_transferts(self, year):
        """Create 25 transfer operations per year."""
        count = 0
        nb_transferts = 25
        
        motifs = ["AFFECTATION", "MUTATION", "RETOUR", "AUTRE"]
        
        for i in range(nb_transferts):
            depot_source = self.rng.choice(self.depots)
            depot_destination = self.rng.choice(
                [d for d in self.depots if d != depot_source]
            )
            
            date_operation = self._random_date(year)
            motif = self.rng.choice(motifs)
            
            operation = OperationTransfert.objects.create(
                date_operation=date_operation,
                depot_source=depot_source,
                depot_destination=depot_destination,
                motif=motif,
                description=f"Transfert de {depot_source.nom} à {depot_destination.nom}",
            )
            
            # Create 2-3 lignes
            num_lignes = self.rng.randint(2, 3)
            for j in range(num_lignes):
                matiere, prix_unitaire = self.rng.choice(self.matieres_list)
                quantite = Decimal(str(self.rng.randint(2, 30)))
                
                # Check stock at source
                key_source = (matiere.id, depot_source.id)
                available = self.stock_tracker[key_source]
                
                if available >= quantite:
                    LigneOperationTransfert.objects.create(
                        operation=operation,
                        matiere=matiere,
                        quantite=quantite,
                        cout_unitaire=prix_unitaire,
                        commentaire="Transfert enregistré",
                    )
                    
                    # Remove from source, add to destination
                    self.stock_tracker[key_source] -= quantite
                    key_dest = (matiere.id, depot_destination.id)
                    self.stock_tracker[key_dest] += quantite
                    
                    # Create stock movements
                    MouvementStock.objects.create(
                        matiere=matiere,
                        depot=depot_source,
                        type="SORTIE",
                        quantite=quantite,
                        cout_unitaire=prix_unitaire,
                        date=date_operation,
                        reference=operation.code,
                    )
                    MouvementStock.objects.create(
                        matiere=matiere,
                        depot=depot_destination,
                        type="ENTREE",
                        quantite=quantite,
                        cout_unitaire=prix_unitaire,
                        date=date_operation,
                        reference=operation.code,
                    )
            
            count += 1
        
        return count

    def _random_date(self, year):
        """Generate a random date within the given year."""
        day = self.rng.randint(1, 365)
        return datetime(year, 1, 1) + timedelta(days=day-1)
