from django.test import TestCase
from django.core.exceptions import ValidationError
from catalog.models import Categorie, SousCategorie, Matiere
from catalog.models.compte import ComptePrincipal, CompteDivisionnaire, SousCompte
from core.models import Unite


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def make_categorie(libelle="Mobilier", code=None):
    kwargs = {"libelle": libelle}
    if code:
        kwargs["code"] = code
    return Categorie.objects.create(**kwargs)


def make_compte_principal(libelle="Mobilier de bureau", groupe=None):
    groupe = groupe or ComptePrincipal.Groupe.G1
    return ComptePrincipal.objects.create(libelle=libelle, groupe=groupe)


def make_sous_compte(libelle="Tables"):
    cp = make_compte_principal()
    cd = CompteDivisionnaire.objects.create(compte_principal=cp, libelle="Div 01")
    return SousCompte.objects.create(compte_divisionnaire=cd, libelle=libelle)


def make_matiere(code_court="TABLE01", designation="Table de bureau"):
    cat = make_categorie(libelle=f"Cat-{code_court}")
    scat = SousCategorie.objects.create(
        libelle=f"SousCat-{code_court}", categorie=cat
    )
    sc = make_sous_compte(libelle=f"SC-{code_court}")
    return Matiere.objects.create(
        code_court=code_court,
        designation=designation,
        sous_categorie=scat,
        sous_compte=sc,
    )


# ─────────────────────────────────────────────
# Categorie
# ─────────────────────────────────────────────

class CategorieCodeAutoTest(TestCase):
    """Le code est généré automatiquement à partir du libellé."""

    def test_code_auto_depuis_libelle(self):
        cat = Categorie.objects.create(libelle="Mobilier de Bureau")
        # initiales attendues : M D B → "MDB"
        self.assertFalse(cat.code == "")
        self.assertEqual(cat.code, "MDB")

    def test_code_explicite_respecte(self):
        cat = Categorie.objects.create(libelle="Informatique", code="INF")
        self.assertEqual(cat.code, "INF")

    def test_code_unique_suffix_si_collision(self):
        Categorie.objects.create(libelle="Matériel", code="MAT")
        cat2 = Categorie.objects.create(libelle="Matériel Audio")
        # "MA" ou "MAA" généré — dans tous les cas, unique
        self.assertNotEqual(cat2.code, "")
        self.assertEqual(Categorie.objects.filter(code=cat2.code).count(), 1)

    def test_str(self):
        cat = Categorie.objects.create(libelle="Mobilier", code="MOB")
        self.assertIn("MOB", str(cat))
        self.assertIn("Mobilier", str(cat))


# ─────────────────────────────────────────────
# SousCategorie
# ─────────────────────────────────────────────

class SousCategorieTest(TestCase):

    def setUp(self):
        self.cat = make_categorie("Informatique", code="INF")

    def test_creation_simple(self):
        scat = SousCategorie.objects.create(libelle="Ordinateurs", categorie=self.cat)
        self.assertFalse(scat.code == "")
        self.assertEqual(scat.categorie, self.cat)

    def test_unicite_libelle_par_categorie(self):
        SousCategorie.objects.create(libelle="Ordinateurs", categorie=self.cat)
        with self.assertRaises(Exception):
            SousCategorie.objects.create(libelle="Ordinateurs", categorie=self.cat)

    def test_meme_libelle_categories_differentes(self):
        cat2 = make_categorie("Mobilier", code="MOB")
        SousCategorie.objects.create(libelle="Bureaux", categorie=self.cat)
        # Pas d'erreur : libellé identique mais catégorie différente
        scat2 = SousCategorie.objects.create(libelle="Bureaux", categorie=cat2)
        self.assertIsNotNone(scat2.pk)

    def test_str(self):
        scat = SousCategorie.objects.create(libelle="Imprimantes", categorie=self.cat)
        self.assertIn("INF", str(scat))
        self.assertIn("Imprimantes", str(scat))


# ─────────────────────────────────────────────
# Plan comptable
# ─────────────────────────────────────────────

class ComptePrincipalTest(TestCase):

    def test_code_sequentiel_g1(self):
        cp1 = ComptePrincipal.objects.create(libelle="Mob", groupe=ComptePrincipal.Groupe.G1)
        cp2 = ComptePrincipal.objects.create(libelle="Info", groupe=ComptePrincipal.Groupe.G1)
        self.assertEqual(cp1.code, "10")
        self.assertEqual(cp2.code, "11")

    def test_code_sequentiel_g2(self):
        cp = ComptePrincipal.objects.create(libelle="Conso", groupe=ComptePrincipal.Groupe.G2)
        self.assertEqual(cp.code, "20")

    def test_pin_incremental(self):
        cp1 = ComptePrincipal.objects.create(libelle="A", groupe=ComptePrincipal.Groupe.G1)
        cp2 = ComptePrincipal.objects.create(libelle="B", groupe=ComptePrincipal.Groupe.G1)
        self.assertEqual(cp2.pin, cp1.pin + 1)

    def test_str(self):
        cp = ComptePrincipal.objects.create(libelle="Mobilier", groupe=ComptePrincipal.Groupe.G1)
        self.assertIn(cp.code, str(cp))
        self.assertIn("Mobilier", str(cp))


class CompteDivisionnairetTest(TestCase):

    def setUp(self):
        self.cp = ComptePrincipal.objects.create(libelle="Mobilier", groupe=ComptePrincipal.Groupe.G1)

    def test_code_format(self):
        cd = CompteDivisionnaire.objects.create(compte_principal=self.cp, libelle="Tables")
        self.assertEqual(cd.code, f"{self.cp.code}.01")

    def test_pin_sequentiel_par_principal(self):
        cd1 = CompteDivisionnaire.objects.create(compte_principal=self.cp, libelle="A")
        cd2 = CompteDivisionnaire.objects.create(compte_principal=self.cp, libelle="B")
        self.assertEqual(cd1.pin, 1)
        self.assertEqual(cd2.pin, 2)
        self.assertEqual(cd2.code, f"{self.cp.code}.02")


class SousCompteTest(TestCase):

    def setUp(self):
        cp = ComptePrincipal.objects.create(libelle="Mobilier", groupe=ComptePrincipal.Groupe.G1)
        self.cd = CompteDivisionnaire.objects.create(compte_principal=cp, libelle="Div")

    def test_code_format(self):
        sc = SousCompte.objects.create(compte_divisionnaire=self.cd, libelle="Tables")
        self.assertEqual(sc.code, f"{self.cd.code}.01")

    def test_plusieurs_sous_comptes(self):
        sc1 = SousCompte.objects.create(compte_divisionnaire=self.cd, libelle="A")
        sc2 = SousCompte.objects.create(compte_divisionnaire=self.cd, libelle="B")
        self.assertEqual(sc1.code, f"{self.cd.code}.01")
        self.assertEqual(sc2.code, f"{self.cd.code}.02")


# ─────────────────────────────────────────────
# Matiere
# ─────────────────────────────────────────────

class MatiereTest(TestCase):

    def setUp(self):
        self.cat = make_categorie("Informatique", code="INF")
        self.scat = SousCategorie.objects.create(libelle="Ordinateurs", categorie=self.cat)
        self.sc = make_sous_compte("Sous-compte PC")

    def _make(self, code="PC001", designation="Ordinateur de bureau", type_matiere=None):
        kwargs = dict(code_court=code, designation=designation,
                      sous_categorie=self.scat, sous_compte=self.sc)
        if type_matiere:
            kwargs["type_matiere"] = type_matiere
        return Matiere.objects.create(**kwargs)

    def test_categorie_auto_depuis_sous_categorie(self):
        mat = self._make()
        self.assertEqual(mat.categorie, self.cat)

    def test_code_court_unique(self):
        self._make("PC001")
        with self.assertRaises(Exception):
            self._make("PC001")

    def test_type_matiere_defaut_reutilisable(self):
        mat = self._make()
        self.assertEqual(mat.type_matiere, Matiere.TypeMatiere.REUTILISABLE)

    def test_type_matiere_consommable(self):
        mat = self._make(type_matiere=Matiere.TypeMatiere.CONSOMMABLE)
        self.assertEqual(mat.type_matiere, Matiere.TypeMatiere.CONSOMMABLE)

    def test_est_stocke_false_par_defaut(self):
        mat = self._make()
        self.assertFalse(mat.est_stocke)

    def test_str(self):
        mat = self._make("PC001", "Ordinateur")
        self.assertIn("PC001", str(mat))
        self.assertIn("Ordinateur", str(mat))

    def test_sous_categorie_mauvaise_categorie_leve_erreur(self):
        autre_cat = make_categorie("Autre", code="AUT")
        autre_scat = SousCategorie.objects.create(libelle="Divers", categorie=autre_cat)
        mat = Matiere(
            code_court="ERR01",
            designation="Test erreur",
            sous_categorie=autre_scat,
            sous_compte=self.sc,
            categorie=self.cat,  # Catégorie incohérente avec la sous-catégorie
        )
        with self.assertRaises(ValidationError):
            mat.full_clean()
