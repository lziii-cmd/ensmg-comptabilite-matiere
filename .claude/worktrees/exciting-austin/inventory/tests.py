from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError

from core.models import Exercice, Depot, Service
from catalog.models import Categorie, SousCategorie, Matiere
from catalog.models.compte import ComptePrincipal, CompteDivisionnaire, SousCompte
from inventory.models import MouvementStock, StockCourant
from inventory.models.operation_sortie import OperationSortie, LigneOperationSortie
from inventory.models.operation_transfert import OperationTransfert, LigneOperationTransfert


# ─────────────────────────────────────────────
# Fixtures communes
# ─────────────────────────────────────────────

class InventoryTestBase(TestCase):
    """Classe de base avec les objets de référence créés une fois."""

    def setUp(self):
        self.exercice = Exercice.objects.create(annee=2025, statut=Exercice.Statut.OUVERT)

        self.depot = Depot.objects.create(
            identifiant="MAG01", nom="Magasin Principal",
            type_lieu=Depot.TypeLieu.DEPOT,
        )
        service = Service.objects.create(
            code="DIR", libelle="Direction", responsable="M. Diallo"
        )
        self.bureau = Depot.objects.create(
            identifiant="BUR01", nom="Bureau Direction",
            type_lieu=Depot.TypeLieu.BUREAU, service=service,
        )

        cat = Categorie.objects.create(libelle="Mobilier", code="MOB")
        scat = SousCategorie.objects.create(libelle="Tables", categorie=cat)
        cp = ComptePrincipal.objects.create(libelle="Mobilier", groupe=ComptePrincipal.Groupe.G1)
        cd = CompteDivisionnaire.objects.create(compte_principal=cp, libelle="Div")
        sc = SousCompte.objects.create(compte_divisionnaire=cd, libelle="Tables")

        self.matiere = Matiere.objects.create(
            code_court="TABLE01",
            designation="Table de bureau",
            sous_categorie=scat,
            sous_compte=sc,
            seuil_min=Decimal("2"),
        )

    def _entree(self, quantite=10, cout_unitaire=50000, depot=None, exercice=None):
        return MouvementStock.objects.create(
            type=MouvementStock.Type.ENTREE,
            matiere=self.matiere,
            depot=depot or self.depot,
            exercice=exercice or self.exercice,
            quantite=Decimal(str(quantite)),
            cout_unitaire=Decimal(str(cout_unitaire)),
        )

    def _sortie(self, quantite=1, depot=None):
        return MouvementStock.objects.create(
            type=MouvementStock.Type.SORTIE,
            matiere=self.matiere,
            depot=depot or self.depot,
            exercice=self.exercice,
            quantite=Decimal(str(quantite)),
        )

    def _stock(self, depot=None):
        return StockCourant.objects.get(
            exercice=self.exercice,
            matiere=self.matiere,
            depot=depot or self.depot,
        )


# ─────────────────────────────────────────────
# MouvementStock — entrées
# ─────────────────────────────────────────────

class MouvementStockEntreeTest(InventoryTestBase):

    def test_entree_cree_stock_courant(self):
        self._entree(quantite=10, cout_unitaire=50000)
        sc = self._stock()
        self.assertEqual(sc.quantite, Decimal("10"))

    def test_premiere_entree_marquee_stock_initial(self):
        mvt = self._entree(quantite=10, cout_unitaire=50000)
        self.assertTrue(mvt.is_stock_initial)

    def test_deuxieme_entree_pas_stock_initial(self):
        self._entree(quantite=10, cout_unitaire=50000)
        mvt2 = self._entree(quantite=5, cout_unitaire=55000)
        self.assertFalse(mvt2.is_stock_initial)

    def test_cump_premiere_entree(self):
        self._entree(quantite=10, cout_unitaire=50000)
        sc = self._stock()
        self.assertEqual(sc.cump, Decimal("50000"))

    def test_cump_deuxieme_entree_moyenne_ponderee(self):
        """CUMP = (10×50000 + 5×60000) / 15 = 53333.333..."""
        self._entree(quantite=10, cout_unitaire=50000)
        self._entree(quantite=5, cout_unitaire=60000)
        sc = self._stock()
        expected = Decimal("53333.333333")
        self.assertAlmostEqual(float(sc.cump), float(expected), places=2)

    def test_cout_total_calcule(self):
        mvt = self._entree(quantite=4, cout_unitaire=25000)
        self.assertEqual(mvt.cout_total, Decimal("100000"))

    def test_matiere_marquee_est_stocke(self):
        self._entree(quantite=5, cout_unitaire=10000)
        self.matiere.refresh_from_db()
        self.assertTrue(self.matiere.est_stocke)

    def test_exercice_auto_depuis_date(self):
        """Si exercice non fourni, il est résolu depuis la date."""
        mvt = MouvementStock.objects.create(
            type=MouvementStock.Type.ENTREE,
            matiere=self.matiere,
            depot=self.depot,
            quantite=Decimal("3"),
            cout_unitaire=Decimal("1000"),
            # exercice non fourni volontairement
        )
        self.assertIsNotNone(mvt.exercice)

    def test_entree_sans_cout_unitaire_leve_erreur(self):
        with self.assertRaises(ValidationError):
            MouvementStock.objects.create(
                type=MouvementStock.Type.ENTREE,
                matiere=self.matiere,
                depot=self.depot,
                exercice=self.exercice,
                quantite=Decimal("5"),
                cout_unitaire=None,
            )

    def test_quantite_nulle_leve_erreur(self):
        with self.assertRaises(ValidationError):
            MouvementStock.objects.create(
                type=MouvementStock.Type.ENTREE,
                matiere=self.matiere,
                depot=self.depot,
                exercice=self.exercice,
                quantite=Decimal("0"),
                cout_unitaire=Decimal("1000"),
            )


# ─────────────────────────────────────────────
# MouvementStock — sorties
# ─────────────────────────────────────────────

class MouvementStockSortieTest(InventoryTestBase):

    def setUp(self):
        super().setUp()
        self._entree(quantite=10, cout_unitaire=50000)

    def test_sortie_diminue_stock(self):
        self._sortie(quantite=3)
        sc = self._stock()
        self.assertEqual(sc.quantite, Decimal("7"))

    def test_sortie_stock_insuffisant_leve_erreur(self):
        with self.assertRaises((ValidationError, Exception)):
            self._sortie(quantite=99)

    def test_plusieurs_sorties_successives(self):
        self._sortie(quantite=4)
        self._sortie(quantite=3)
        sc = self._stock()
        self.assertEqual(sc.quantite, Decimal("3"))

    def test_sortie_exactement_tout_le_stock(self):
        self._sortie(quantite=10)
        sc = self._stock()
        self.assertEqual(sc.quantite, Decimal("0"))


# ─────────────────────────────────────────────
# MouvementStock — transferts
# ─────────────────────────────────────────────

class MouvementStockTransfertTest(InventoryTestBase):

    def setUp(self):
        super().setUp()
        self._entree(quantite=10, cout_unitaire=50000)

    def test_transfert_diminue_source_augmente_destination(self):
        MouvementStock.objects.create(
            type=MouvementStock.Type.TRANSFERT,
            matiere=self.matiere,
            exercice=self.exercice,
            source_depot=self.depot,
            destination_depot=self.bureau,
            quantite=Decimal("4"),
        )
        src = self._stock(depot=self.depot)
        dst = self._stock(depot=self.bureau)
        self.assertEqual(src.quantite, Decimal("6"))
        self.assertEqual(dst.quantite, Decimal("4"))

    def test_transfert_stock_insuffisant_leve_erreur(self):
        with self.assertRaises(Exception):
            MouvementStock.objects.create(
                type=MouvementStock.Type.TRANSFERT,
                matiere=self.matiere,
                exercice=self.exercice,
                source_depot=self.depot,
                destination_depot=self.bureau,
                quantite=Decimal("999"),
            )

    def test_transfert_depots_identiques_leve_erreur(self):
        with self.assertRaises(ValidationError):
            MouvementStock.objects.create(
                type=MouvementStock.Type.TRANSFERT,
                matiere=self.matiere,
                exercice=self.exercice,
                source_depot=self.depot,
                destination_depot=self.depot,
                quantite=Decimal("2"),
            )

    def test_transfert_sans_depot_source_leve_erreur(self):
        with self.assertRaises(ValidationError):
            MouvementStock.objects.create(
                type=MouvementStock.Type.TRANSFERT,
                matiere=self.matiere,
                exercice=self.exercice,
                destination_depot=self.bureau,
                quantite=Decimal("2"),
            )


# ─────────────────────────────────────────────
# OperationSortie
# ─────────────────────────────────────────────

class OperationSortieTest(InventoryTestBase):

    def setUp(self):
        super().setUp()
        self._entree(quantite=20, cout_unitaire=30000)

    def test_code_auto_genere(self):
        op = OperationSortie.objects.create(
            type_sortie=OperationSortie.TypeSortie.REFORME_DESTRUCTION,
            depot=self.depot,
        )
        self.assertTrue(op.code.startswith("SO-2025-"))

    def test_code_sequentiel(self):
        op1 = OperationSortie.objects.create(
            type_sortie=OperationSortie.TypeSortie.REFORME_DESTRUCTION,
            depot=self.depot,
        )
        op2 = OperationSortie.objects.create(
            type_sortie=OperationSortie.TypeSortie.PERTE_VOL_DEFICIT,
            depot=self.depot,
        )
        n1 = int(op1.code.split("-")[-1])
        n2 = int(op2.code.split("-")[-1])
        self.assertEqual(n2, n1 + 1)

    def test_total_valeur_calcule_depuis_lignes(self):
        op = OperationSortie.objects.create(
            type_sortie=OperationSortie.TypeSortie.REFORME_DESTRUCTION,
            depot=self.depot,
        )
        LigneOperationSortie.objects.create(
            operation=op,
            matiere=self.matiere,
            quantite=Decimal("2"),
            prix_unitaire=Decimal("30000"),
        )
        op.refresh_from_db()
        self.assertEqual(op.total_valeur, Decimal("60000"))

    def test_str(self):
        op = OperationSortie.objects.create(
            type_sortie=OperationSortie.TypeSortie.REFORME_DESTRUCTION,
            depot=self.depot,
        )
        self.assertIn("SO-", str(op))


# ─────────────────────────────────────────────
# OperationTransfert
# ─────────────────────────────────────────────

class OperationTransfertTest(InventoryTestBase):

    def setUp(self):
        super().setUp()
        self._entree(quantite=20, cout_unitaire=30000)

    def test_code_auto_genere(self):
        op = OperationTransfert.objects.create(
            depot_source=self.depot,
            depot_destination=self.bureau,
            motif=OperationTransfert.Motif.AFFECTATION,
        )
        self.assertTrue(op.code.startswith("TR-2025-"))

    def test_depots_identiques_leve_erreur(self):
        with self.assertRaises(ValidationError):
            op = OperationTransfert(
                depot_source=self.depot,
                depot_destination=self.depot,
            )
            op.full_clean()

    def test_str_contient_fleche(self):
        op = OperationTransfert.objects.create(
            depot_source=self.depot,
            depot_destination=self.bureau,
        )
        self.assertIn("→", str(op))


# ─────────────────────────────────────────────
# FicheAffectation
# ─────────────────────────────────────────────

class FicheAffectationTest(InventoryTestBase):
    """Tests unitaires pour le modèle FicheAffectation."""

    def setUp(self):
        super().setUp()
        # Créer une Dotation et une LigneDotation minimales pour les tests
        from purchasing.models import Dotation, LigneDotation
        from catalog.models.compte import ComptePrincipal, CompteDivisionnaire, SousCompte

        self.dotation = Dotation.objects.create(
            depot=self.depot,
            statut=Dotation.Statut.VALIDE,
        )
        self.ligne_dotation = LigneDotation.objects.create(
            dotation=self.dotation,
            matiere=self.matiere,
            quantite=Decimal("2"),
            depot=self.depot,
        )

    def _fiche(self, **kwargs):
        from inventory.models import FicheAffectation
        defaults = dict(
            dotation=self.dotation,
            ligne_dotation=self.ligne_dotation,
            matiere=self.matiere,
            depot=self.depot,
            beneficiaire="Moussa Diallo",
            quantite=Decimal("1"),
        )
        defaults.update(kwargs)
        return FicheAffectation.objects.create(**defaults)

    def test_code_auto_genere(self):
        """Le code est généré automatiquement au format FA-AAAA-NNNNN."""
        from inventory.models import FicheAffectation
        fiche = self._fiche()
        self.assertTrue(fiche.code.startswith("FA-"))
        self.assertRegex(fiche.code, r"^FA-\d{4}-\d{5}$")

    def test_codes_sequentiels(self):
        """Deux fiches créées dans la même année ont des codes distincts et croissants."""
        from inventory.models import FicheAffectation
        fiche1 = self._fiche()
        # Détacher la ligne_dotation de la première fiche pour pouvoir en créer une seconde
        fiche2 = FicheAffectation.objects.create(
            dotation=self.dotation,
            matiere=self.matiere,
            depot=self.depot,
            beneficiaire="Fatou Sow",
            quantite=Decimal("1"),
        )
        self.assertNotEqual(fiche1.code, fiche2.code)
        n1 = int(fiche1.code.split("-")[-1])
        n2 = int(fiche2.code.split("-")[-1])
        self.assertGreater(n2, n1)

    def test_statut_par_defaut_est_affecte(self):
        """Le statut initial d'une fiche est AFFECTE."""
        from inventory.models import FicheAffectation
        fiche = self._fiche()
        self.assertEqual(fiche.statut, FicheAffectation.Statut.AFFECTE)

    def test_str_contient_code_et_beneficiaire(self):
        """La représentation textuelle contient le code et le bénéficiaire."""
        fiche = self._fiche()
        s = str(fiche)
        self.assertIn(fiche.code, s)
        self.assertIn("Moussa Diallo", s)

    def test_quantite_liee_a_matiere_et_depot(self):
        """La fiche référence correctement la matière et le dépôt source."""
        fiche = self._fiche()
        self.assertEqual(fiche.matiere, self.matiere)
        self.assertEqual(fiche.depot, self.depot)
