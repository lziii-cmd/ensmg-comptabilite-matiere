from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError

from core.models import Exercice, Depot, Service, Fournisseur, Donateur
from catalog.models import Categorie, SousCategorie, Matiere
from catalog.models.compte import ComptePrincipal, CompteDivisionnaire, SousCompte
from purchasing.models import Achat, LigneAchat, Don, LigneDon, Pret, LignePret
from purchasing.models.retour import RetourFournisseur


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def make_exercice(annee=2025):
    return Exercice.objects.create(annee=annee, statut=Exercice.Statut.OUVERT)


def make_depot():
    return Depot.objects.create(
        identifiant="MAG01", nom="Magasin Principal",
        type_lieu=Depot.TypeLieu.DEPOT,
    )


def make_fournisseur(raison="Electro Dakar", prefix="ELECTRO"):
    f = Fournisseur.objects.create(raison_sociale=raison, code_prefix=prefix)
    return f


def make_donateur(raison="ONG Solidarité", prefix="ONG"):
    return Donateur.objects.create(raison_sociale=raison, code_prefix=prefix)


def make_matiere(code="TABLE01"):
    cat = Categorie.objects.create(libelle=f"Cat-{code}", code=code[:3])
    scat = SousCategorie.objects.create(libelle=f"Sous-{code}", categorie=cat)
    cp = ComptePrincipal.objects.create(libelle=f"CP-{code}", groupe=ComptePrincipal.Groupe.G1)
    cd = CompteDivisionnaire.objects.create(compte_principal=cp, libelle="Div")
    sc = SousCompte.objects.create(compte_divisionnaire=cd, libelle="SC")
    return Matiere.objects.create(
        code_court=code, designation=f"Matière {code}",
        sous_categorie=scat, sous_compte=sc,
    )


# ─────────────────────────────────────────────
# Achat
# ─────────────────────────────────────────────

class AchatTest(TestCase):

    def setUp(self):
        self.exercice = make_exercice()
        self.depot = make_depot()
        self.fournisseur = make_fournisseur()
        self.matiere = make_matiere("PC001")

    def _achat(self, tva=False):
        return Achat.objects.create(
            fournisseur=self.fournisseur,
            depot=self.depot,
            tva_active=tva,
        )

    def test_code_auto_genere(self):
        achat = self._achat()
        self.assertTrue(achat.code.startswith("ACH-"))
        self.assertIn("ELECTRO", achat.code)

    def test_codes_sequentiels(self):
        a1 = self._achat()
        a2 = self._achat()
        n1 = int(a1.code.split("-")[-1])
        n2 = int(a2.code.split("-")[-1])
        self.assertEqual(n2, n1 + 1)

    def test_total_zero_sans_lignes(self):
        achat = self._achat()
        self.assertEqual(achat.total_ht, Decimal("0"))
        self.assertEqual(achat.total_ttc, Decimal("0"))

    def test_total_ht_avec_lignes(self):
        achat = self._achat()
        LigneAchat.objects.create(
            achat=achat, matiere=self.matiere,
            quantite=Decimal("2"), prix_unitaire=Decimal("50000"),
        )
        achat.refresh_from_db()
        self.assertEqual(achat.total_ht, Decimal("100000"))

    def test_total_ttc_sans_tva(self):
        achat = self._achat(tva=False)
        LigneAchat.objects.create(
            achat=achat, matiere=self.matiere,
            quantite=Decimal("1"), prix_unitaire=Decimal("100000"),
        )
        achat.refresh_from_db()
        self.assertEqual(achat.total_tva, Decimal("0"))
        self.assertEqual(achat.total_ttc, achat.total_ht)

    def test_total_ttc_avec_tva(self):
        """TVA à 18% : 100 000 HT → 18 000 TVA → 118 000 TTC."""
        achat = self._achat(tva=True)
        LigneAchat.objects.create(
            achat=achat, matiere=self.matiere,
            quantite=Decimal("1"), prix_unitaire=Decimal("100000"),
        )
        achat.refresh_from_db()
        self.assertEqual(achat.total_ht, Decimal("100000"))
        self.assertEqual(achat.total_tva, Decimal("18000"))
        self.assertEqual(achat.total_ttc, Decimal("118000"))

    def test_plusieurs_lignes_cumulent_ht(self):
        achat = self._achat()
        m2 = make_matiere("CHAISE01")
        LigneAchat.objects.create(
            achat=achat, matiere=self.matiere,
            quantite=Decimal("3"), prix_unitaire=Decimal("20000"),
        )
        LigneAchat.objects.create(
            achat=achat, matiere=m2,
            quantite=Decimal("5"), prix_unitaire=Decimal("10000"),
        )
        achat.refresh_from_db()
        self.assertEqual(achat.total_ht, Decimal("110000"))

    def test_str(self):
        achat = self._achat()
        self.assertIn("ACH-", str(achat))


# ─────────────────────────────────────────────
# LigneAchat
# ─────────────────────────────────────────────

class LigneAchatTest(TestCase):

    def setUp(self):
        self.exercice = make_exercice()
        self.depot = make_depot()
        self.fournisseur = make_fournisseur()
        self.matiere = make_matiere("TABLE02")
        self.achat = Achat.objects.create(
            fournisseur=self.fournisseur, depot=self.depot
        )

    def test_total_ligne_calcule(self):
        ligne = LigneAchat.objects.create(
            achat=self.achat, matiere=self.matiere,
            quantite=Decimal("4"), prix_unitaire=Decimal("25000"),
        )
        self.assertEqual(ligne.total_ligne_ht, Decimal("100000"))

    def test_quantite_nulle_leve_erreur(self):
        ligne = LigneAchat(
            achat=self.achat, matiere=self.matiere,
            quantite=Decimal("0"), prix_unitaire=Decimal("1000"),
        )
        with self.assertRaises(ValidationError):
            ligne.full_clean()

    def test_prix_negatif_leve_erreur(self):
        ligne = LigneAchat(
            achat=self.achat, matiere=self.matiere,
            quantite=Decimal("1"), prix_unitaire=Decimal("-100"),
        )
        with self.assertRaises(ValidationError):
            ligne.full_clean()

    def test_str(self):
        ligne = LigneAchat.objects.create(
            achat=self.achat, matiere=self.matiere,
            quantite=Decimal("2"), prix_unitaire=Decimal("10000"),
        )
        self.assertIn("2", str(ligne))


# ─────────────────────────────────────────────
# Don
# ─────────────────────────────────────────────

class DonTest(TestCase):

    def setUp(self):
        self.depot = make_depot()
        self.donateur = make_donateur()
        self.matiere = make_matiere("STYLO01")
        make_exercice()

    def _don(self):
        return Don.objects.create(donateur=self.donateur, depot=self.depot)

    def test_code_auto_genere(self):
        don = self._don()
        self.assertTrue(don.code.startswith("DON-"))
        self.assertIn("ONG", don.code)

    def test_codes_sequentiels(self):
        d1 = self._don()
        d2 = self._don()
        n1 = int(d1.code.split("-")[-1])
        n2 = int(d2.code.split("-")[-1])
        self.assertEqual(n2, n1 + 1)

    def test_total_valeur_avec_lignes(self):
        don = self._don()
        LigneDon.objects.create(
            don=don, matiere=self.matiere,
            quantite=Decimal("10"), prix_unitaire=Decimal("500"),
        )
        don.refresh_from_db()
        self.assertEqual(don.total_valeur, Decimal("5000"))

    def test_valorisation_facultative_zero(self):
        """Un don sans prix unitaire doit avoir total = 0."""
        don = self._don()
        LigneDon.objects.create(
            don=don, matiere=self.matiere,
            quantite=Decimal("5"), prix_unitaire=Decimal("0"),
        )
        don.refresh_from_db()
        self.assertEqual(don.total_valeur, Decimal("0"))

    def test_str(self):
        don = self._don()
        self.assertIn("DON-", str(don))


# ─────────────────────────────────────────────
# Prêt
# ─────────────────────────────────────────────

class PretTest(TestCase):

    def setUp(self):
        self.depot = make_depot()
        self.service = Service.objects.create(
            code="FIN", libelle="Finance", responsable="M. Sall"
        )
        self.matiere = make_matiere("CHAISE02")
        make_exercice()

    def _pret(self):
        return Pret.objects.create(service=self.service, depot=self.depot)

    def test_code_auto_genere(self):
        pret = self._pret()
        self.assertTrue(pret.code.startswith("PRET-"))
        self.assertIn("FIN", pret.code)

    def test_codes_sequentiels(self):
        p1 = self._pret()
        p2 = self._pret()
        n1 = int(p1.code.split("-")[-1])
        n2 = int(p2.code.split("-")[-1])
        self.assertEqual(n2, n1 + 1)

    def test_non_clos_par_defaut(self):
        pret = self._pret()
        self.assertFalse(pret.est_clos)

    def test_ligne_pret_quantite_nulle_leve_erreur(self):
        pret = self._pret()
        ligne = LignePret(
            pret=pret, matiere=self.matiere,
            quantite=Decimal("0"),
        )
        with self.assertRaises(ValidationError):
            ligne.full_clean()

    def test_str(self):
        pret = self._pret()
        self.assertIn("PRET-", str(pret))


# ─────────────────────────────────────────────
# RetourFournisseur
# ─────────────────────────────────────────────

class RetourFournisseurTest(TestCase):

    def setUp(self):
        self.depot = make_depot()
        self.fournisseur = make_fournisseur("Matériaux SA", "MATSА")
        make_exercice()

    def test_code_auto_genere(self):
        retour = RetourFournisseur.objects.create(
            fournisseur=self.fournisseur, depot=self.depot
        )
        self.assertTrue(retour.code.startswith("RET-"))

    def test_codes_sequentiels(self):
        r1 = RetourFournisseur.objects.create(
            fournisseur=self.fournisseur, depot=self.depot
        )
        r2 = RetourFournisseur.objects.create(
            fournisseur=self.fournisseur, depot=self.depot
        )
        n1 = int(r1.code.split("-")[-1])
        n2 = int(r2.code.split("-")[-1])
        self.assertEqual(n2, n1 + 1)

    def test_fournisseur_obligatoire(self):
        retour = RetourFournisseur(depot=self.depot)
        with self.assertRaises(ValidationError):
            retour.full_clean()

    def test_str(self):
        retour = RetourFournisseur.objects.create(
            fournisseur=self.fournisseur, depot=self.depot
        )
        self.assertIn("RET-", str(retour))
