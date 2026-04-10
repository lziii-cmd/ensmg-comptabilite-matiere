# catalog/management/commands/seed_catalog.py
import random
import re
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.apps import apps


def _norm(s: str) -> str:
    s = (s or "").strip().upper()
    s = re.sub(r"[^A-Z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "X"


def _mk_code(prefix: str, idx: int, width: int = 3) -> str:
    return f"{prefix}-{idx:0{width}d}"


class Command(BaseCommand):
    help = "Seed cohérent et riche du module catalog (comptes + catégories + sous-catégories + matières)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Supprime les données catalog avant de reseed.")
        parser.add_argument("--scale", choices=["small", "medium", "large"], default="medium")

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(42)

        scale = options["scale"]
        reset = options["reset"]

        self.stdout.write(self.style.MIGRATE_HEADING(f"SEED_CATALOG (scale={scale}, reset={reset})"))

        Unite = apps.get_model("core", "Unite")

        ComptePrincipal = apps.get_model("catalog", "ComptePrincipal")
        CompteDivisionnaire = apps.get_model("catalog", "CompteDivisionnaire")
        SousCompte = apps.get_model("catalog", "SousCompte")

        Categorie = apps.get_model("catalog", "Categorie")
        SousCategorie = apps.get_model("catalog", "SousCategorie")
        Matiere = apps.get_model("catalog", "Matiere")

        if reset:
            self.stdout.write(self.style.WARNING("RESET: suppression des données catalog ..."))
            Matiere.objects.all().delete()
            SousCategorie.objects.all().delete()
            Categorie.objects.all().delete()
            SousCompte.objects.all().delete()
            CompteDivisionnaire.objects.all().delete()
            ComptePrincipal.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("RESET catalog OK."))

        # 1) Unités
        unites = self._seed_unites(Unite)
        U = {u.abreviation: u for u in unites}

        # 2) Comptes (cohérents)
        sc_map = self._seed_comptes_coherents(ComptePrincipal, CompteDivisionnaire, SousCompte)

        # 3) Catégories/Sous-catégories (cohérentes)
        cats, sous = self._seed_categories_coherentes(Categorie, SousCategorie)

        # 4) Matières (cohérentes : unit, type_matiere, mapping comptable)
        matieres = self._seed_matieres_coherentes(
            Matiere=Matiere,
            SousCategorie=SousCategorie,
            sous_categories=sous,
            U=U,
            sc_map=sc_map,
            scale=scale,
        )

        self.stdout.write(self.style.SUCCESS("✅ Seed catalog terminé avec succès."))
        self.stdout.write(
            f"Résumé: Unités={len(unites)} | Sous-comptes={len(sc_map)} | Catégories={len(cats)} | "
            f"Sous-catégories={len(sous)} | Matières={len(matieres)}"
        )

    # -------------------------
    # Unités
    # -------------------------
    def _seed_unites(self, Unite):
        data = [
            ("U", "Unité"),
            ("PCS", "Pièce"),
            ("LOT", "Lot"),
            ("KG", "Kilogramme"),
            ("L", "Litre"),
            ("M", "Mètre"),
            ("M2", "Mètre carré"),
            ("M3", "Mètre cube"),
            ("BT", "Boîte"),
            ("PAQ", "Paquet"),
        ]
        out = []
        for ab, lib in data:
            u = Unite.objects.filter(abreviation=ab).first()
            if not u:
                u = Unite(abreviation=ab, libelle=lib)
                u.save()
            out.append(u)
        self.stdout.write(self.style.SUCCESS(f"Unités: {len(out)}"))
        return out

    # -------------------------
    # Comptes (cohérence)
    # -------------------------
    def _seed_comptes_coherents(self, ComptePrincipal, CompteDivisionnaire, SousCompte):
        """
        Objectif:
        - G1: immobilisations/biens durables (informatique, mobilier, labo, sécurité, énergie)
        - G2: consommables/charges (papeterie, toner, entretien, électricité, EPI, petit outillage)
        On retourne un mapping "FAMILLE_KEY" -> SousCompte (pour imputer les matières).
        """

        # Principaux (libellés stables)
        principals_spec = [
            (ComptePrincipal.Groupe.G1, "Matériel informatique (immobilisations)"),
            (ComptePrincipal.Groupe.G1, "Matériel mobilier (immobilisations)"),
            (ComptePrincipal.Groupe.G1, "Équipements de laboratoire (immobilisations)"),
            (ComptePrincipal.Groupe.G1, "Sécurité & incendie (immobilisations)"),
            (ComptePrincipal.Groupe.G2, "Fournitures de bureau & papeterie (consommables)"),
            (ComptePrincipal.Groupe.G2, "Encre, toner & consommables impression"),
            (ComptePrincipal.Groupe.G2, "Entretien & nettoyage (consommables)"),
            (ComptePrincipal.Groupe.G2, "Électricité & petits matériels (consommables)"),
            (ComptePrincipal.Groupe.G2, "EPI & sécurité (consommables)"),
            (ComptePrincipal.Groupe.G2, "Petit outillage & quincaillerie"),
        ]

        principals = []
        for grp, lib in principals_spec:
            p = ComptePrincipal.objects.filter(libelle=lib).first()
            if not p:
                p = ComptePrincipal(groupe=grp, libelle=lib, description="", actif=True)
                p.save()  # pin+code auto
            principals.append(p)

        # Divisionnaires + sous-comptes par principal (structure simple mais stable)
        # Chaque "famille" pointe vers 1 sous-compte dédié (cohérence).
        family_to_sc = {}

        def ensure_sc(principal_libelle: str, div_lib: str, sc_lib: str, family_key: str):
            p = ComptePrincipal.objects.filter(libelle=principal_libelle).first()
            d = CompteDivisionnaire.objects.filter(compte_principal=p, libelle=div_lib).first()
            if not d:
                d = CompteDivisionnaire(compte_principal=p, libelle=div_lib, description="", actif=True)
                d.save()
            sc = SousCompte.objects.filter(compte_divisionnaire=d, libelle=sc_lib).first()
            if not sc:
                sc = SousCompte(compte_divisionnaire=d, libelle=sc_lib, description="", actif=True)
                sc.save()
            family_to_sc[family_key] = sc

        # G1 (durables)
        ensure_sc(
            "Matériel informatique (immobilisations)",
            "Informatique / Parc & postes",
            "Informatique / Postes & PC",
            "INF_PC",
        )
        ensure_sc(
            "Matériel informatique (immobilisations)",
            "Informatique / Impression & numérisation",
            "Informatique / Imprimantes & scanners",
            "INF_IMPR",
        )
        ensure_sc(
            "Matériel informatique (immobilisations)",
            "Informatique / Réseau",
            "Informatique / Réseau & connectique durable",
            "INF_RESEAU",
        )

        ensure_sc(
            "Matériel mobilier (immobilisations)",
            "Mobilier / Bureau",
            "Mobilier / Bureaux & tables",
            "MOB_TABLE",
        )
        ensure_sc(
            "Matériel mobilier (immobilisations)",
            "Mobilier / Assises",
            "Mobilier / Chaises & fauteuils",
            "MOB_CHAISE",
        )
        ensure_sc(
            "Matériel mobilier (immobilisations)",
            "Mobilier / Rangement",
            "Mobilier / Armoires & rangement",
            "MOB_RANG",
        )

        ensure_sc(
            "Équipements de laboratoire (immobilisations)",
            "Laboratoire / Instruments",
            "Laboratoire / Instruments durables",
            "LAB_INSTRU",
        )
        ensure_sc(
            "Équipements de laboratoire (immobilisations)",
            "Laboratoire / Sécurité",
            "Laboratoire / Sécurité durable",
            "LAB_SEC",
        )

        ensure_sc(
            "Sécurité & incendie (immobilisations)",
            "Incendie / Équipements",
            "Incendie / Extincteurs & RIA",
            "SEC_EXT",
        )

        # G2 (consommables)
        ensure_sc(
            "Fournitures de bureau & papeterie (consommables)",
            "Bureau / Papeterie",
            "Papeterie / Papier & cahiers",
            "CON_PAP",
        )
        ensure_sc(
            "Fournitures de bureau & papeterie (consommables)",
            "Bureau / Écriture",
            "Bureau / Stylos, marqueurs, crayons",
            "CON_ECRI",
        )
        ensure_sc(
            "Fournitures de bureau & papeterie (consommables)",
            "Bureau / Classement",
            "Bureau / Classement & archivage",
            "CON_CLASS",
        )

        ensure_sc(
            "Encre, toner & consommables impression",
            "Impression / Toners",
            "Impression / Toners & cartouches",
            "CON_TON",
        )
        ensure_sc(
            "Encre, toner & consommables impression",
            "Impression / Divers",
            "Impression / Divers consommables",
            "CON_IMPR_DIV",
        )

        ensure_sc(
            "Entretien & nettoyage (consommables)",
            "Entretien / Produits",
            "Nettoyage / Détergents & produits",
            "NET_PROD",
        )
        ensure_sc(
            "Entretien & nettoyage (consommables)",
            "Entretien / Matériels",
            "Nettoyage / Balais, serpillières",
            "NET_MAT",
        )

        ensure_sc(
            "Électricité & petits matériels (consommables)",
            "Électricité / Câbles",
            "Électricité / Câbles & connectique",
            "ELEC_CABLE",
        )
        ensure_sc(
            "Électricité & petits matériels (consommables)",
            "Électricité / Éclairage",
            "Électricité / Ampoules & éclairage",
            "ELEC_LED",
        )
        ensure_sc(
            "Petit outillage & quincaillerie",
            "Quincaillerie / Fixation",
            "Quincaillerie / Vis, chevilles, colliers",
            "QUINC_FIX",
        )

        ensure_sc(
            "EPI & sécurité (consommables)",
            "EPI / Protection",
            "EPI / Gants, lunettes, masques",
            "EPI_PROT",
        )

        self.stdout.write(self.style.SUCCESS(f"Sous-comptes (familles): {len(family_to_sc)}"))
        return family_to_sc

    # -------------------------
    # Catégories / Sous-catégories
    # -------------------------
    def _seed_categories_coherentes(self, Categorie, SousCategorie):
        cat_spec = [
            ("Informatique", "Équipements informatiques et accessoires."),
            ("Mobilier", "Mobilier de bureau et rangement."),
            ("Laboratoire", "Équipements et consommables de laboratoire."),
            ("Consommables", "Fournitures consommables (bureautique, etc.)."),
            ("Électricité", "Éclairage, câbles, accessoires électriques."),
            ("Entretien & Nettoyage", "Produits et matériels de nettoyage."),
            ("Sécurité", "Sécurité, EPI, incendie."),
            ("Quincaillerie", "Fixations et petits matériels."),
        ]

        cats = []
        for lib, desc in cat_spec:
            c = Categorie.objects.filter(libelle=lib).first()
            if not c:
                c = Categorie(libelle=lib, description=desc, actif=True)
                c.save()  # code auto
            cats.append(c)

        cat_by_lib = {c.libelle: c for c in cats}

        sous_spec = {
            "Informatique": [
                ("Postes & PC", "PC, laptops, unités centrales, écrans."),
                ("Impression", "Imprimantes, scanners, consommables d’impression."),
                ("Réseau", "Switch, routeurs, câbles réseau, connectique."),
                ("Accessoires", "Souris, claviers, multiprises, etc."),
            ],
            "Mobilier": [
                ("Assises", "Chaises, fauteuils."),
                ("Tables & Bureaux", "Bureaux, tables de réunion."),
                ("Rangement", "Armoires, étagères, casiers."),
            ],
            "Laboratoire": [
                ("Instruments", "Balances, centrifugeuses, appareils."),
                ("Verrerie", "Béchers, éprouvettes, pipettes (souvent consommables)."),
                ("Sécurité Labo", "Gants, lunettes, blouses, etc."),
            ],
            "Consommables": [
                ("Papeterie", "Papier, cahiers, enveloppes."),
                ("Écriture", "Stylos, marqueurs, crayons."),
                ("Classement", "Chemises, classeurs, boîtes archives."),
            ],
            "Électricité": [
                ("Éclairage", "Ampoules, tubes, luminaires."),
                ("Câbles & Connectique", "Câbles, prises, adaptateurs."),
                ("Protection", "Disjoncteurs, fusibles (si utilisés)."),
            ],
            "Entretien & Nettoyage": [
                ("Produits", "Détergents, javel, savon."),
                ("Matériels", "Balais, serpillières, seaux."),
            ],
            "Sécurité": [
                ("Incendie", "Extincteurs, signalisation."),
                ("EPI", "Gants, masques, lunettes."),
            ],
            "Quincaillerie": [
                ("Fixation", "Vis, chevilles, colliers."),
                ("Petit outillage", "Tournevis, pinces, ruban, etc."),
            ],
        }

        sous = []
        for cat_lib, sc_list in sous_spec.items():
            cat = cat_by_lib[cat_lib]
            for sc_lib, sc_desc in sc_list:
                sc = SousCategorie.objects.filter(categorie=cat, libelle=sc_lib).first()
                if not sc:
                    sc = SousCategorie(
                        categorie=cat,
                        libelle=sc_lib,
                        description=sc_desc,
                        actif=True,
                    )
                    sc.save()  # code auto
                sous.append(sc)

        self.stdout.write(self.style.SUCCESS(f"Catégories: {len(cats)} | Sous-catégories: {len(sous)}"))
        return cats, sous

    # -------------------------
    # Matières (cohérence réelle)
    # -------------------------
    def _seed_matieres_coherentes(self, Matiere, SousCategorie, sous_categories, U, sc_map, scale: str):
        """
        On génère des matières à partir d'un catalogue "réaliste" par sous-catégorie.
        Chaque item définit:
        - code_prefix (court)
        - designation_base
        - type_matiere (consommable / reutilisable)
        - unite
        - famille comptable (clé -> sous_compte)
        - seuil_min cohérent
        """

        # volumes
        if scale == "small":
            multiplier = 1
        elif scale == "large":
            multiplier = 4
        else:
            multiplier = 2

        # Helper pour retrouver SousCategorie par (categorie_lib, sous_lib)
        def get_sc(cat_lib: str, sous_lib: str):
            return SousCategorie.objects.filter(categorie__libelle=cat_lib, libelle=sous_lib).first()

        # Catalogue cohérent
        catalog = []

        # INFORMATIQUE
        catalog += [
            # Postes & PC
            (get_sc("Informatique", "Postes & PC"), "INF-PC", "Ordinateur portable", "reutilisable", "PCS", "INF_PC", Decimal("1")),
            (get_sc("Informatique", "Postes & PC"), "INF-UC", "Unité centrale", "reutilisable", "PCS", "INF_PC", Decimal("1")),
            (get_sc("Informatique", "Postes & PC"), "INF-ECR", "Écran", "reutilisable", "PCS", "INF_PC", Decimal("1")),
            (get_sc("Informatique", "Postes & PC"), "INF-OND", "Onduleur", "reutilisable", "PCS", "INF_PC", Decimal("1")),
            # Impression
            (get_sc("Informatique", "Impression"), "INF-IMPR", "Imprimante", "reutilisable", "PCS", "INF_IMPR", Decimal("1")),
            (get_sc("Informatique", "Impression"), "CON-TON", "Toner", "consommable", "PCS", "CON_TON", Decimal("3")),
            (get_sc("Informatique", "Impression"), "CON-CART", "Cartouche d’encre", "consommable", "PCS", "CON_TON", Decimal("3")),
            (get_sc("Informatique", "Impression"), "CON-PAP", "Papier A4 (rame)", "consommable", "PAQ", "CON_PAP", Decimal("10")),
            # Réseau
            (get_sc("Informatique", "Réseau"), "INF-SWI", "Switch réseau", "reutilisable", "PCS", "INF_RESEAU", Decimal("1")),
            (get_sc("Informatique", "Réseau"), "INF-ROU", "Routeur", "reutilisable", "PCS", "INF_RESEAU", Decimal("1")),
            (get_sc("Informatique", "Réseau"), "ELEC-RJ45", "Câble RJ45", "consommable", "M", "ELEC_CABLE", Decimal("30")),
            # Accessoires
            (get_sc("Informatique", "Accessoires"), "INF-SOUR", "Souris", "reutilisable", "PCS", "INF_PC", Decimal("2")),
            (get_sc("Informatique", "Accessoires"), "INF-CLAV", "Clavier", "reutilisable", "PCS", "INF_PC", Decimal("2")),
            (get_sc("Informatique", "Accessoires"), "INF-MULT", "Multiprise", "reutilisable", "PCS", "ELEC_CABLE", Decimal("2")),
        ]

        # MOBILIER
        catalog += [
            (get_sc("Mobilier", "Assises"), "MOB-CH", "Chaise", "reutilisable", "PCS", "MOB_CHAISE", Decimal("2")),
            (get_sc("Mobilier", "Assises"), "MOB-FAU", "Fauteuil", "reutilisable", "PCS", "MOB_CHAISE", Decimal("1")),
            (get_sc("Mobilier", "Tables & Bureaux"), "MOB-BUR", "Bureau", "reutilisable", "PCS", "MOB_TABLE", Decimal("1")),
            (get_sc("Mobilier", "Tables & Bureaux"), "MOB-TAB", "Table réunion", "reutilisable", "PCS", "MOB_TABLE", Decimal("1")),
            (get_sc("Mobilier", "Rangement"), "MOB-ARM", "Armoire", "reutilisable", "PCS", "MOB_RANG", Decimal("1")),
            (get_sc("Mobilier", "Rangement"), "MOB-ETA", "Étagère", "reutilisable", "PCS", "MOB_RANG", Decimal("1")),
        ]

        # CONSOMMABLES
        catalog += [
            (get_sc("Consommables", "Papeterie"), "CON-PAP", "Papier A4 (rame)", "consommable", "PAQ", "CON_PAP", Decimal("10")),
            (get_sc("Consommables", "Papeterie"), "CON-CAH", "Cahier", "consommable", "PCS", "CON_PAP", Decimal("10")),
            (get_sc("Consommables", "Écriture"), "CON-STY", "Stylo bille", "consommable", "PCS", "CON_ECRI", Decimal("20")),
            (get_sc("Consommables", "Écriture"), "CON-MAR", "Marqueur", "consommable", "PCS", "CON_ECRI", Decimal("10")),
            (get_sc("Consommables", "Classement"), "CON-CLA", "Classeur", "consommable", "PCS", "CON_CLASS", Decimal("10")),
            (get_sc("Consommables", "Classement"), "CON-ARCH", "Boîte archives", "consommable", "PCS", "CON_CLASS", Decimal("10")),
        ]

        # ELECTRICITÉ
        catalog += [
            (get_sc("Électricité", "Éclairage"), "ELEC-LED", "Ampoule LED", "consommable", "PCS", "ELEC_LED", Decimal("10")),
            (get_sc("Électricité", "Éclairage"), "ELEC-TUBE", "Tube néon", "consommable", "PCS", "ELEC_LED", Decimal("10")),
            (get_sc("Électricité", "Câbles & Connectique"), "ELEC-CAB", "Câble électrique", "consommable", "M", "ELEC_CABLE", Decimal("20")),
            (get_sc("Électricité", "Câbles & Connectique"), "ELEC-PRI", "Prise", "consommable", "PCS", "ELEC_CABLE", Decimal("10")),
        ]

        # ENTRETIEN
        catalog += [
            (get_sc("Entretien & Nettoyage", "Produits"), "NET-JAV", "Eau de javel", "consommable", "L", "NET_PROD", Decimal("20")),
            (get_sc("Entretien & Nettoyage", "Produits"), "NET-DET", "Détergent", "consommable", "L", "NET_PROD", Decimal("20")),
            (get_sc("Entretien & Nettoyage", "Produits"), "NET-SAV", "Savon liquide", "consommable", "L", "NET_PROD", Decimal("20")),
            (get_sc("Entretien & Nettoyage", "Matériels"), "NET-BAL", "Balai", "consommable", "PCS", "NET_MAT", Decimal("10")),
            (get_sc("Entretien & Nettoyage", "Matériels"), "NET-SER", "Serpillière", "consommable", "PCS", "NET_MAT", Decimal("20")),
            (get_sc("Entretien & Nettoyage", "Matériels"), "NET-SEA", "Seau", "reutilisable", "PCS", "NET_MAT", Decimal("2")),
        ]

        # SÉCURITÉ
        catalog += [
            (get_sc("Sécurité", "Incendie"), "SEC-EXT", "Extincteur", "reutilisable", "PCS", "SEC_EXT", Decimal("1")),
            (get_sc("Sécurité", "EPI"), "EPI-GANT", "Gants de protection", "consommable", "PCS", "EPI_PROT", Decimal("20")),
            (get_sc("Sécurité", "EPI"), "EPI-LUN", "Lunettes de protection", "consommable", "PCS", "EPI_PROT", Decimal("10")),
            (get_sc("Sécurité", "EPI"), "EPI-MASQ", "Masque", "consommable", "PCS", "EPI_PROT", Decimal("50")),
        ]

        # QUINCAILLERIE
        catalog += [
            (get_sc("Quincaillerie", "Fixation"), "QUI-VIS", "Vis (boîte)", "consommable", "BT", "QUINC_FIX", Decimal("10")),
            (get_sc("Quincaillerie", "Fixation"), "QUI-CHV", "Chevilles (boîte)", "consommable", "BT", "QUINC_FIX", Decimal("10")),
            (get_sc("Quincaillerie", "Fixation"), "QUI-COL", "Colliers de serrage", "consommable", "PAQ", "QUINC_FIX", Decimal("10")),
            (get_sc("Quincaillerie", "Petit outillage"), "QUI-TOUR", "Tournevis", "reutilisable", "PCS", "QUINC_FIX", Decimal("2")),
            (get_sc("Quincaillerie", "Petit outillage"), "QUI-PINC", "Pince", "reutilisable", "PCS", "QUINC_FIX", Decimal("2")),
        ]

        # Nettoyage des entrées invalides (si une SousCategorie n'existe pas)
        catalog = [row for row in catalog if row[0] is not None]

        # Génération
        created = []
        existing_codes = set(Matiere.objects.values_list("code_court", flat=True))

        # Chaque ligne du catalogue va être déclinée avec variations (modèle, marque, capacité…)
        variations = {
            "Ordinateur portable": ["Core i5 / 8Go / 256Go", "Core i7 / 16Go / 512Go", "Ryzen 5 / 8Go / 256Go"],
            "Unité centrale": ["i5 / 8Go", "i7 / 16Go", "Ryzen 7 / 16Go"],
            "Écran": ['21"', '24"', '27"'],
            "Imprimante": ["Laser", "Jet d’encre", "Multifonction"],
            "Toner": ["Noir", "Cyan", "Magenta", "Jaune"],
            "Cartouche d’encre": ["Noir", "Couleur"],
            "Papier A4 (rame)": ["80g", "90g"],
            "Câble RJ45": ["Cat5e", "Cat6"],
            "Switch réseau": ["8 ports", "16 ports", "24 ports"],
            "Routeur": ["Standard", "Pro"],
            "Multiprise": ["4 prises", "6 prises"],
            "Chaise": ["standard", "confort", "avec accoudoirs"],
            "Bureau": ["120cm", "140cm", "160cm"],
            "Armoire": ["2 portes", "3 portes"],
            "Étagère": ["5 niveaux", "6 niveaux"],
            "Ampoule LED": ["9W", "12W", "18W"],
            "Tube néon": ["60cm", "120cm"],
            "Câble électrique": ["2.5mm²", "1.5mm²"],
            "Prise": ["simple", "double"],
            "Eau de javel": ["1L", "5L"],
            "Détergent": ["1L", "5L"],
            "Savon liquide": ["1L", "5L"],
            "Balai": ["simple", "renforcé"],
            "Serpillière": ["microfibre", "standard"],
            "Seau": ["10L", "15L"],
            "Extincteur": ["6kg", "9kg"],
            "Gants de protection": ["taille M", "taille L"],
            "Lunettes de protection": ["anti-buée", "standard"],
            "Masque": ["chirurgical", "FFP2"],
            "Vis (boîte)": ["bois", "métal"],
            "Chevilles (boîte)": ["mur", "placo"],
            "Colliers de serrage": ["petit", "grand"],
            "Tournevis": ["plat", "cruciforme"],
            "Pince": ["universelle", "coupante"],
            "Stylo bille": ["bleu", "noir", "rouge"],
            "Marqueur": ["noir", "couleur"],
            "Classeur": ["A4", "A5"],
            "Boîte archives": ["dos 8cm", "dos 10cm"],
            "Cahier": ["100 pages", "200 pages"],
        }

        # multiplicateur de richesse
        # - durable: moins de variantes
        # - consommables: plus de variantes
        for (sc, prefix, base_name, type_matiere, unite_abbr, family_key, seuil_min) in catalog:
            if type_matiere == "reutilisable":
                k = 1 * multiplier
            else:
                k = 2 * multiplier

            vars_list = variations.get(base_name, ["standard"])
            # on limite sans perdre la cohérence
            random.shuffle(vars_list)
            vars_list = vars_list[: max(2, min(len(vars_list), 2 * multiplier))]

            sc_obj = sc
            sous_compte = sc_map.get(family_key)

            # fallback sécurité : si pas de sous_compte mapping, on prend un sous-compte existant (mais normalement non)
            if not sous_compte:
                sous_compte = list(sc_map.values())[0]

            # unite
            unite = U.get(unite_abbr) if unite_abbr else None

            # type enum Matiere
            type_enum = (
                Matiere.TypeMatiere.CONSOMMABLE if type_matiere == "consommable" else Matiere.TypeMatiere.REUTILISABLE
            )

            # création variations
            idx = 1
            made_for_this = 0
            while made_for_this < k:
                var = vars_list[made_for_this % len(vars_list)]
                designation = f"{base_name} — {var}"

                # code matière stable & lisible (unique)
                code_candidate = _mk_code(prefix, idx, 3)  # ex: INF-PC-001
                idx += 1
                if code_candidate in existing_codes:
                    continue

                m = Matiere(
                    code_court=code_candidate,
                    designation=designation,
                    type_matiere=type_enum,
                    sous_categorie=sc_obj,
                    sous_compte=sous_compte,
                    unite=unite,
                    seuil_min=seuil_min,
                    actif=True,
                )
                m.save()
                created.append(m)
                existing_codes.add(code_candidate)
                made_for_this += 1

        self.stdout.write(self.style.SUCCESS(f"Matières: {len(created)} (cohérentes)"))
        return created
