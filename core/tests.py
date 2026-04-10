from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from core.models import (
    Exercice, Depot, Service, Fournisseur, Donateur,
    Sequence, FournisseurSequence, Unite,
)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def make_exercice(annee=2025, statut=Exercice.Statut.OUVERT):
    return Exercice.objects.create(annee=annee, statut=statut)


def make_service(code="DIR", libelle="Direction"):
    return Service.objects.create(code=code, libelle=libelle, responsable="M. Diallo")


def make_fournisseur(raison_sociale="Electro Dakar"):
    return Fournisseur.objects.create(raison_sociale=raison_sociale)


# ─────────────────────────────────────────────
# Exercice
# ─────────────────────────────────────────────

class ExerciceTest(TestCase):

    def test_dates_auto_generees(self):
        ex = make_exercice(annee=2025)
        from datetime import date
        self.assertEqual(ex.date_debut, date(2025, 1, 1))
        self.assertEqual(ex.date_fin, date(2025, 12, 31))

    def test_code_auto_genere(self):
        ex = make_exercice(annee=2025)
        self.assertEqual(ex.code, "EX-2025")

    def test_str(self):
        ex = make_exercice(annee=2025)
        self.assertIn("EX-2025", str(ex))
        self.assertIn("OUVERT", str(ex))

    def test_un_seul_exercice_ouvert_a_la_fois(self):
        make_exercice(annee=2025, statut=Exercice.Statut.OUVERT)
        with self.assertRaises(Exception):
            make_exercice(annee=2026, statut=Exercice.Statut.OUVERT)

    def test_plusieurs_exercices_clos(self):
        make_exercice(annee=2023, statut=Exercice.Statut.CLOS)
        ex2 = make_exercice(annee=2024, statut=Exercice.Statut.CLOS)
        self.assertIsNotNone(ex2.pk)

    def test_courants_retourne_ouverts(self):
        ex = make_exercice(annee=2025, statut=Exercice.Statut.OUVERT)
        qs = Exercice.courants()
        self.assertIn(ex, qs)

    def test_courants_exclut_clos(self):
        make_exercice(annee=2024, statut=Exercice.Statut.CLOS)
        qs = Exercice.courants()
        self.assertEqual(qs.count(), 0)

    def test_est_courant_property(self):
        from datetime import date
        import datetime
        ex = make_exercice(annee=date.today().year)
        self.assertTrue(ex.est_courant)

    def test_annee_unique(self):
        make_exercice(annee=2025, statut=Exercice.Statut.OUVERT)
        with self.assertRaises(Exception):
            # Même année, statut différent → doit quand même échouer sur annee unique
            make_exercice(annee=2025, statut=Exercice.Statut.CLOS)


# ─────────────────────────────────────────────
# Service & Depot
# ─────────────────────────────────────────────

class ServiceTest(TestCase):

    def test_creation(self):
        s = make_service()
        self.assertEqual(s.code, "DIR")
        self.assertTrue(s.actif)

    def test_str_actif(self):
        s = make_service(code="ADM", libelle="Administration")
        self.assertIn("ADM", str(s))
        self.assertNotIn("inactif", str(s))

    def test_str_inactif(self):
        s = make_service()
        s.actif = False
        s.save()
        self.assertIn("inactif", str(s))


class DepotTest(TestCase):

    def setUp(self):
        self.service = make_service()

    def test_depot_type_depot(self):
        d = Depot.objects.create(
            identifiant="D01", nom="Magasin Principal",
            type_lieu=Depot.TypeLieu.DEPOT
        )
        self.assertEqual(d.type_lieu, "DEPOT")
        self.assertIsNone(d.service)

    def test_bureau_necessite_service(self):
        d = Depot(
            identifiant="B01", nom="Bureau Direction",
            type_lieu=Depot.TypeLieu.BUREAU,
        )
        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_bureau_avec_service_valide(self):
        d = Depot.objects.create(
            identifiant="B01", nom="Bureau Direction",
            type_lieu=Depot.TypeLieu.BUREAU,
            service=self.service,
        )
        self.assertEqual(d.service, self.service)

    def test_depot_ne_doit_pas_avoir_service(self):
        d = Depot(
            identifiant="D02", nom="Entrepôt",
            type_lieu=Depot.TypeLieu.DEPOT,
            service=self.service,
        )
        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_str(self):
        d = Depot.objects.create(
            identifiant="D01", nom="Magasin",
            type_lieu=Depot.TypeLieu.DEPOT
        )
        self.assertIn("D01", str(d))
        self.assertIn("Magasin", str(d))


# ─────────────────────────────────────────────
# Fournisseur
# ─────────────────────────────────────────────

class FournisseurTest(TestCase):

    def test_identifiant_auto_genere(self):
        f = make_fournisseur("Matériaux du Sahel")
        self.assertTrue(f.identifiant.startswith("FRS-"))
        self.assertGreater(len(f.identifiant), 4)

    def test_code_prefix_auto_depuis_raison_sociale(self):
        f = make_fournisseur("Electro Dakar")
        self.assertFalse(f.code_prefix == "")
        # Doit contenir des lettres issues de "Electro Dakar"
        self.assertTrue(f.code_prefix.isupper() or f.code_prefix.isalnum())

    def test_code_prefix_explicite_respecte(self):
        f = Fournisseur.objects.create(raison_sociale="Test", code_prefix="MONPREF")
        self.assertEqual(f.code_prefix, "MONPREF")

    def test_ninea_unique(self):
        Fournisseur.objects.create(raison_sociale="A", ninea="123456789")
        with self.assertRaises(Exception):
            Fournisseur.objects.create(raison_sociale="B", ninea="123456789")

    def test_ninea_null_non_unique(self):
        Fournisseur.objects.create(raison_sociale="A", ninea=None)
        f2 = Fournisseur.objects.create(raison_sociale="B", ninea=None)
        self.assertIsNotNone(f2.pk)

    def test_str(self):
        f = make_fournisseur("Electro Dakar")
        self.assertIn("Electro Dakar", str(f))


# ─────────────────────────────────────────────
# Donateur
# ─────────────────────────────────────────────

class DonateurTest(TestCase):

    def test_identifiant_format(self):
        from django.utils import timezone
        d = Donateur.objects.create(raison_sociale="Amis de l'ENSMG")
        year = timezone.now().year
        self.assertIn(str(year), d.identifiant)
        self.assertTrue(d.identifiant.startswith("DON-"))

    def test_identifiants_sequentiels(self):
        d1 = Donateur.objects.create(raison_sociale="Donateur Alpha")
        d2 = Donateur.objects.create(raison_sociale="Donateur Alpha")
        # Les deux doivent exister avec des identifiants différents
        self.assertNotEqual(d1.identifiant, d2.identifiant)

    def test_str(self):
        d = Donateur.objects.create(raison_sociale="ONG Solidarité")
        self.assertEqual(str(d), "ONG Solidarité")


# ─────────────────────────────────────────────
# Sequence (numérotation des pièces)
# ─────────────────────────────────────────────

class SequenceTest(TestCase):

    def setUp(self):
        self.exercice = make_exercice(annee=2025)

    def test_premier_code(self):
        code = Sequence.next_code("ACH", self.exercice)
        self.assertEqual(code, "ACH-2025-0001")

    def test_incrementation(self):
        Sequence.next_code("ACH", self.exercice)
        code2 = Sequence.next_code("ACH", self.exercice)
        self.assertEqual(code2, "ACH-2025-0002")

    def test_types_independants(self):
        code_ach = Sequence.next_code("ACH", self.exercice)
        code_sor = Sequence.next_code("SOR", self.exercice)
        self.assertEqual(code_ach, "ACH-2025-0001")
        self.assertEqual(code_sor, "SOR-2025-0001")

    def test_pas_de_collision_concurrente(self):
        """Vérifie que 10 appels successifs produisent 10 codes distincts."""
        codes = [Sequence.next_code("ACH", self.exercice) for _ in range(10)]
        self.assertEqual(len(set(codes)), 10)


# ─────────────────────────────────────────────
# FournisseurSequence
# ─────────────────────────────────────────────

class FournisseurSequenceTest(TestCase):

    def setUp(self):
        self.fournisseur = make_fournisseur("Electro Dakar")
        self.fournisseur.code_prefix = "ELECTRO"
        self.fournisseur.save()

    def test_premier_code_achat(self):
        code = FournisseurSequence.generate_code(self.fournisseur, 2025, "ACH")
        self.assertEqual(code, "ACH-ELECTRO-2025-00001")

    def test_incrementation(self):
        FournisseurSequence.generate_code(self.fournisseur, 2025, "ACH")
        code2 = FournisseurSequence.generate_code(self.fournisseur, 2025, "ACH")
        self.assertEqual(code2, "ACH-ELECTRO-2025-00002")

    def test_retour_independant_achat(self):
        code_ach = FournisseurSequence.generate_code(self.fournisseur, 2025, "ACH")
        code_ret = FournisseurSequence.generate_code(self.fournisseur, 2025, "RET")
        self.assertEqual(code_ach, "ACH-ELECTRO-2025-00001")
        self.assertEqual(code_ret, "RET-ELECTRO-2025-00001")

    def test_annees_independantes(self):
        code_25 = FournisseurSequence.generate_code(self.fournisseur, 2025, "ACH")
        code_26 = FournisseurSequence.generate_code(self.fournisseur, 2026, "ACH")
        self.assertIn("2025", code_25)
        self.assertIn("2026", code_26)
        self.assertIn("00001", code_25)
        self.assertIn("00001", code_26)

    def test_pas_de_collision_10_codes(self):
        codes = [FournisseurSequence.generate_code(self.fournisseur, 2025, "ACH") for _ in range(10)]
        self.assertEqual(len(set(codes)), 10)
