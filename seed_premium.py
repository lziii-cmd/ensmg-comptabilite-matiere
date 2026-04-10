"""
Seed premium ENSMG — Comptabilite Matieres
Exercices 2022-2026 avec donnees coherentes et impact stock reel.
"""
import datetime
from decimal import Decimal
from django.core.management import call_command
from django.db import transaction
from django.contrib.auth import get_user_model

User = get_user_model()

# ==============================================================
# 0. FLUSH
# ==============================================================
print("Vidage de la base...")
call_command("flush", "--no-input", verbosity=0)
print("OK - base videe")

# ==============================================================
# 1. SUPERUSER
# ==============================================================
admin = User.objects.create_superuser("admin", "admin@ensmg.sn", "admin1234")
print(f"Superuser '{admin.username}' cree")

# ==============================================================
# 2. EXERCICES
# ==============================================================
from core.models import Exercice, Unite, Depot, Fournisseur, FournisseurSequence, Donateur, Service

exos = {}
for annee, statut in [(2022,"CLOS"),(2023,"CLOS"),(2024,"CLOS"),(2025,"CLOS"),(2026,"OUVERT")]:
    e = Exercice.objects.create(
        annee=annee,
        date_debut=datetime.date(annee,1,1),
        date_fin=datetime.date(annee,12,31),
        statut=statut,
    )
    exos[annee] = e
print(f"{len(exos)} exercices crees (2022-2026)")

# ==============================================================
# 3. UNITES
# ==============================================================
unites = {}
for abrev, libelle in [
    ("PCE","Piece"),("RME","Rame"),("BTE","Boite"),
    ("CTN","Carton"),("LTR","Litre"),("LOT","Lot"),
]:
    unites[abrev] = Unite.objects.create(abreviation=abrev, libelle=libelle)
print(f"{len(unites)} unites creees")

# ==============================================================
# 4. DEPOTS
# ==============================================================
depots = {}
for ident, nom, type_lieu, resp, loc in [
    ("MAGCEN","Magasin Central","DEPOT","M. Ibrahima DIALLO","Batiment Administratif - RDC"),
    ("DEPINFO","Depot Informatique","DEPOT","M. Cheikh SECK","Batiment Pedagogique - Salle Reseau"),
    ("DEPFOUR","Depot Fournitures","DEPOT","Mme Aminata FALL","Batiment Administratif - Aile Est"),
]:
    depots[ident] = Depot.objects.create(
        identifiant=ident, nom=nom, type_lieu=type_lieu,
        responsable=resp, localisation=loc,
    )
print(f"{len(depots)} depots crees")

# ==============================================================
# 5. SERVICES
# ==============================================================
services = {}
for code, libelle, resp in [
    ("DG","Direction Generale","Prof. Mamadou DIALLO"),
    ("SCO","Scolarite","Mme Fatou NDIAYE"),
    ("CPT","Comptabilite et Finances","M. Oumar FALL"),
    ("INFO","Service Informatique","M. Cheikh SECK"),
    ("BIB","Bibliotheque","Mme Aissatou BA"),
    ("LABGEO","Laboratoire de Geologie","Dr. Ibrahima SARR"),
    ("LABMIN","Laboratoire des Mines","Dr. Pape DIOP"),
    ("TECH","Service Technique","M. Moussa KANE"),
    ("RH","Ressources Humaines","Mme Mariama DIALLO"),
]:
    services[code] = Service.objects.create(code=code, libelle=libelle, responsable=resp)
print(f"{len(services)} services crees")

# ==============================================================
# 6. FOURNISSEURS
# ==============================================================
frs = {}
for rs, addr, tel, ninea, prefix in [
    ("DITEX SA","Dakar - Zone Industrielle","33 800 11 22","123456789D2001","DITEX"),
    ("BUREAU SENEGAL SARL","Dakar - Plateau","33 821 33 44","234567890D2001","BUREAUSN"),
    ("PAPETERIE MODERNE SARL","Dakar - Medina","33 822 55 66","345678901D2001","PAPMOD"),
    ("SAHEL INFORMATIQUE","Dakar - Liberte 6","33 867 77 88","456789012D2001","SAHELINF"),
    ("CLEAN SERVICES SENEGAL","Dakar - Grand Yoff","33 869 99 00","567890123D2001","CLEANSER"),
    ("ELECTRO DAKAR SARL","Dakar - Colobane","33 823 11 33","678901234D2001","ELECTRO"),
]:
    frs[prefix] = Fournisseur.objects.create(
        raison_sociale=rs, adresse=addr, numero=tel, ninea=ninea, code_prefix=prefix,
    )
print(f"{len(frs)} fournisseurs crees")

# ==============================================================
# 7. DONATEURS
# ==============================================================
dons_ref = {}
for rs, addr, tel, prefix in [
    ("UNESCO Dakar","Almadies, Dakar","+221 33 849 23 23","UNESCO"),
    ("Banque Mondiale","Dakar Plateau","+221 33 859 41 00","BANKMONDE"),
    ("Ambassade de France","Point E, Dakar","+221 33 839 51 00","AMBFRANCE"),
    ("Cooperation Allemande GIZ","Mermoz, Dakar","+221 33 869 65 00","GIZ"),
]:
    dons_ref[prefix] = Donateur.objects.create(
        raison_sociale=rs, adresse=addr, telephone=tel, code_prefix=prefix,
    )
print(f"{len(dons_ref)} donateurs crees")

# ==============================================================
# 8. PLAN COMPTABLE
# ==============================================================
from catalog.models import ComptePrincipal, CompteDivisionnaire, SousCompte, Categorie, SousCategorie, Matiere

cp_info  = ComptePrincipal.objects.create(groupe="G1", libelle="Materiel Informatique")
cp_mob   = ComptePrincipal.objects.create(groupe="G1", libelle="Mobilier et Equipements")
cp_four  = ComptePrincipal.objects.create(groupe="G2", libelle="Fournitures de Bureau")
cp_entr  = ComptePrincipal.objects.create(groupe="G2", libelle="Produits d Entretien")
cp_cinfo = ComptePrincipal.objects.create(groupe="G2", libelle="Consommables Informatiques")
print(f"ComptesPrincipaux: {cp_info.code}, {cp_mob.code}, {cp_four.code}, {cp_entr.code}, {cp_cinfo.code}")

cd_ordi  = CompteDivisionnaire.objects.create(compte_principal=cp_info, libelle="Ordinateurs et Peripheriques")
cd_proj  = CompteDivisionnaire.objects.create(compte_principal=cp_info, libelle="Materiel de Projection")
cd_reseau= CompteDivisionnaire.objects.create(compte_principal=cp_info, libelle="Reseaux et Connectique")
cd_mob   = CompteDivisionnaire.objects.create(compte_principal=cp_mob,  libelle="Mobilier de Bureau")
cd_equip = CompteDivisionnaire.objects.create(compte_principal=cp_mob,  libelle="Equipements Divers")
cd_paper = CompteDivisionnaire.objects.create(compte_principal=cp_four, libelle="Papeterie")
cd_docs  = CompteDivisionnaire.objects.create(compte_principal=cp_four, libelle="Documents et Classement")
cd_nett  = CompteDivisionnaire.objects.create(compte_principal=cp_entr, libelle="Produits de Nettoyage")
cd_toner = CompteDivisionnaire.objects.create(compte_principal=cp_cinfo,libelle="Toners et Cartouches")
cd_acc   = CompteDivisionnaire.objects.create(compte_principal=cp_cinfo,libelle="Accessoires Informatiques")

sc_port  = SousCompte.objects.create(compte_divisionnaire=cd_ordi,  libelle="Ordinateurs portables")
sc_desk  = SousCompte.objects.create(compte_divisionnaire=cd_ordi,  libelle="Ordinateurs de bureau")
sc_impr  = SousCompte.objects.create(compte_divisionnaire=cd_ordi,  libelle="Imprimantes et Scanners")
sc_proj  = SousCompte.objects.create(compte_divisionnaire=cd_proj,  libelle="Videoprojecteurs")
sc_net   = SousCompte.objects.create(compte_divisionnaire=cd_reseau, libelle="Switches et Routeurs")
sc_bur   = SousCompte.objects.create(compte_divisionnaire=cd_mob,   libelle="Bureaux et Tables")
sc_chaise= SousCompte.objects.create(compte_divisionnaire=cd_mob,   libelle="Chaises et Sieges")
sc_range = SousCompte.objects.create(compte_divisionnaire=cd_mob,   libelle="Armoires et Rangements")
sc_clim  = SousCompte.objects.create(compte_divisionnaire=cd_equip, libelle="Climatiseurs")
sc_ond   = SousCompte.objects.create(compte_divisionnaire=cd_equip, libelle="Onduleurs")
sc_papi  = SousCompte.objects.create(compte_divisionnaire=cd_paper, libelle="Rames de Papier")
sc_stylo = SousCompte.objects.create(compte_divisionnaire=cd_paper, libelle="Stylos et Crayons")
sc_cahier= SousCompte.objects.create(compte_divisionnaire=cd_paper, libelle="Cahiers et Carnets")
sc_chem  = SousCompte.objects.create(compte_divisionnaire=cd_docs,  libelle="Chemises et Dossiers")
sc_envel = SousCompte.objects.create(compte_divisionnaire=cd_docs,  libelle="Enveloppes")
sc_deterg= SousCompte.objects.create(compte_divisionnaire=cd_nett,  libelle="Detergents")
sc_desinf= SousCompte.objects.create(compte_divisionnaire=cd_nett,  libelle="Desinfectants")
sc_toner = SousCompte.objects.create(compte_divisionnaire=cd_toner, libelle="Toners")
sc_encre = SousCompte.objects.create(compte_divisionnaire=cd_toner, libelle="Cartouches Encre")
sc_usb   = SousCompte.objects.create(compte_divisionnaire=cd_acc,   libelle="Cles USB et Memoires")
print("Plan comptable cree")

# ==============================================================
# 9. CATEGORIES ET SOUS-CATEGORIES
# ==============================================================
cat_info  = Categorie.objects.create(code="INF",   libelle="Materiel Informatique")
cat_mob   = Categorie.objects.create(code="MOB",   libelle="Mobilier de Bureau")
cat_equip = Categorie.objects.create(code="EQUIP", libelle="Equipements Divers")
cat_four  = Categorie.objects.create(code="FOUR",  libelle="Fournitures de Bureau")
cat_entr  = Categorie.objects.create(code="ENTR",  libelle="Produits d Entretien")
cat_cinfo = Categorie.objects.create(code="CINFO", libelle="Consommables Informatiques")

scat_ordi  = SousCategorie.objects.create(categorie=cat_info,  code="ORDI",   libelle="Ordinateurs")
scat_impr  = SousCategorie.objects.create(categorie=cat_info,  code="IMPR",   libelle="Imprimantes")
scat_proj  = SousCategorie.objects.create(categorie=cat_info,  code="PROJ",   libelle="Projecteurs")
scat_reseau= SousCategorie.objects.create(categorie=cat_info,  code="RESEAU", libelle="Reseau et Connectique")
scat_bur   = SousCategorie.objects.create(categorie=cat_mob,   code="BURE",   libelle="Bureaux et Tables")
scat_chais = SousCategorie.objects.create(categorie=cat_mob,   code="CHAIS",  libelle="Chaises et Sieges")
scat_rang  = SousCategorie.objects.create(categorie=cat_mob,   code="RANG",   libelle="Rangements")
scat_clim  = SousCategorie.objects.create(categorie=cat_equip, code="CLIM",   libelle="Climatisation")
scat_alim  = SousCategorie.objects.create(categorie=cat_equip, code="ALIM",   libelle="Alimentation Electrique")
scat_pap   = SousCategorie.objects.create(categorie=cat_four,  code="PAP",    libelle="Papeterie")
scat_doc   = SousCategorie.objects.create(categorie=cat_four,  code="DOC",    libelle="Documents et Classement")
scat_nett  = SousCategorie.objects.create(categorie=cat_entr,  code="NETT",   libelle="Nettoyage et Hygiene")
scat_ton   = SousCategorie.objects.create(categorie=cat_cinfo, code="TON",    libelle="Toners et Cartouches")
scat_acc   = SousCategorie.objects.create(categorie=cat_cinfo, code="ACC",    libelle="Accessoires USB")
print("Categories et sous-categories creees")

# ==============================================================
# 10. MATIERES
# ==============================================================
PCE=unites["PCE"]; RME=unites["RME"]; BTE=unites["BTE"]
LTR=unites["LTR"]; LOT=unites["LOT"]

mat = {}
for code, desig, type_m, souscat, souscompte, unite, seuil in [
    # G1 - reutilisable (immobilisations)
    ("ORD-PORT",   "Ordinateur portable HP EliteBook 840",    "reutilisable", scat_ordi,  sc_port,   PCE, 5),
    ("ORD-DESK",   "Ordinateur de bureau DELL OptiPlex 7010", "reutilisable", scat_ordi,  sc_desk,   PCE, 2),
    ("IMP-LASER",  "Imprimante laser HP LaserJet Pro M404",   "reutilisable", scat_impr,  sc_impr,   PCE, 1),
    ("IMP-JET",    "Imprimante jet d encre Canon PIXMA G3420","reutilisable", scat_impr,  sc_impr,   PCE, 0),
    ("VIDEO-PROJ", "Videoprojecteur EPSON EB-X51",            "reutilisable", scat_proj,  sc_proj,   PCE, 1),
    ("SWITCH-24",  "Switch reseau TP-Link TL-SG1024 24 ports","reutilisable", scat_reseau,sc_net,    PCE, 1),
    ("BUREAU-STD", "Bureau standard 160x80 cm stratifie",     "reutilisable", scat_bur,   sc_bur,    PCE, 2),
    ("CHAISE-DIR", "Chaise de direction ergonomique cuir",    "reutilisable", scat_chais, sc_chaise, PCE, 2),
    ("CHAISE-VISI","Chaise visiteur tissu gris",              "reutilisable", scat_chais, sc_chaise, PCE, 2),
    ("ARMOIRE-MET","Armoire metallique 2 portes 4 etageres",  "reutilisable", scat_rang,  sc_range,  PCE, 1),
    ("CLIM-15",    "Climatiseur 1.5CV Inverter SAMSUNG",      "reutilisable", scat_clim,  sc_clim,   PCE, 1),
    ("ONDULEUR-1K","Onduleur 1000VA avec AVR EATON",          "reutilisable", scat_alim,  sc_ond,    PCE, 1),
    # G2 - consommable
    ("PAPI-A4",    "Rame papier A4 80g/m2 Double A",          "consommable",  scat_pap,   sc_papi,   RME, 20),
    ("STYLO-BX",   "Boite de 10 stylos bille Bic bleu",       "consommable",  scat_pap,   sc_stylo,  BTE, 10),
    ("CAHIER-100", "Cahier 100 pages grand format seyes",     "consommable",  scat_pap,   sc_cahier, PCE, 10),
    ("CHEM-CART",  "Paquet 10 chemises cartonnees",           "consommable",  scat_doc,   sc_chem,   LOT, 10),
    ("ENVEL-A4",   "Lot 50 enveloppes kraft A4 90g",          "consommable",  scat_doc,   sc_envel,  LOT, 10),
    ("TONER-HP",   "Toner HP CF280A 85A LaserJet",            "consommable",  scat_ton,   sc_toner,  PCE,  3),
    ("CART-ENC",   "Cartouche d encre HP 302 tri-couleur",    "consommable",  scat_ton,   sc_encre,  PCE,  3),
    ("CLE-USB-32", "Cle USB 32Go SanDisk Ultra",              "consommable",  scat_acc,   sc_usb,    PCE,  5),
    ("DETERG-5L",  "Detergent liquide vaisselle 5L",          "consommable",  scat_nett,  sc_deterg, LTR, 10),
    ("DESINFECT",  "Desinfectant surfaces 1L Anios",          "consommable",  scat_nett,  sc_desinf, LTR,  5),
    ("JAVEL-5L",   "Eau de Javel 5L 9.6 degres",              "consommable",  scat_nett,  sc_desinf, LTR, 10),
]:
    mat[code] = Matiere.objects.create(
        code_court=code, designation=desig, type_matiere=type_m,
        sous_categorie=souscat, sous_compte=souscompte,
        unite=unite, seuil_min=Decimal(str(seuil)),
    )
print(f"{len(mat)} matieres creees")

# ==============================================================
# HELPERS TRANSACTIONS
# ==============================================================
from purchasing.models import Achat, LigneAchat, Don, LigneDon, Dotation, LigneDotation

MAGCEN = depots["MAGCEN"]

def d(y,m,j): return datetime.date(y,m,j)
def D(v):     return Decimal(str(v))

def achat(fournisseur, depot, date, lignes, tva=False):
    a = Achat.objects.create(fournisseur=fournisseur, depot=depot, date_achat=date, tva_active=tva)
    for code, qte, pu in lignes:
        LigneAchat.objects.create(achat=a, matiere=mat[code], quantite=D(qte), prix_unitaire=D(pu))
    a.refresh_from_db()
    return a

def don(donateur, depot, date, lignes):
    from inventory.models import MouvementStock
    from inventory.services.exercice import exercice_courant
    from django.utils import timezone as tz
    dn = Don.objects.create(donateur=donateur, depot=depot, date_don=date)
    for code, qte, pu in lignes:
        LigneDon.objects.create(don=dn, matiere=mat[code], quantite=D(qte), prix_unitaire=D(pu))
    # Les dons n'ont pas de signal auto -> on cree les mouvements manuellement
    dn.refresh_from_db()
    exo = exercice_courant(dn.date_don)
    aware_dt = tz.make_aware(datetime.datetime.combine(dn.date_don, datetime.time.min))
    for ligne in dn.lignes.select_related("matiere").all():
        if not ligne.matiere_id or (ligne.quantite or 0) <= 0:
            continue
        MouvementStock.objects.get_or_create(
            source_doc_type="purchasing.LigneDon",
            source_doc_id=ligne.id,
            defaults=dict(
                type="ENTREE",
                date=aware_dt,
                exercice=exo,
                matiere=ligne.matiere,
                depot=depot,
                quantite=ligne.quantite,
                cout_unitaire=ligne.prix_unitaire or D("0"),
                reference=dn.code or "",
                commentaire=f"Entree de stock - Don {dn.code}",
            ),
        )
    return dn

def dotation(depot, beneficiaire, service, date, lignes):
    dt = Dotation.objects.create(
        depot=depot, beneficiaire=beneficiaire, service=service,
        date=date, statut=Dotation.Statut.BROUILLON,
    )
    for code, qte, pu in lignes:
        LigneDotation.objects.create(
            dotation=dt, matiere=mat[code], quantity=D(qte), unit_price=D(pu)
        )
    dt.statut = Dotation.Statut.VALIDE
    dt.save()
    dt.generer_documents()
    return dt

# ==============================================================
# EXERCICE 2022
# ==============================================================
print("\n--- Exercice 2022 ---")

achat(frs["DITEX"], MAGCEN, d(2022,1,15), [
    ("ORD-PORT",  15, 580000),
    ("ORD-DESK",   5, 450000),
    ("IMP-LASER",  4, 145000),
    ("VIDEO-PROJ", 3, 245000),
    ("SWITCH-24",  3, 185000),
], tva=True)

achat(frs["BUREAUSN"], MAGCEN, d(2022,2,10), [
    ("BUREAU-STD",  25,  75000),
    ("CHAISE-DIR",  40,  32000),
    ("CHAISE-VISI", 10,  18000),
    ("ARMOIRE-MET", 20, 115000),
    ("CLIM-15",      5, 300000),
    ("ONDULEUR-1K",  8,  45000),
])

achat(frs["PAPMOD"], MAGCEN, d(2022,3,5), [
    ("PAPI-A4",   300, 3200),
    ("STYLO-BX",  500, 1800),
    ("CAHIER-100",200, 1400),
    ("CHEM-CART", 150,  600),
    ("ENVEL-A4",  100,  200),
])

achat(frs["SAHELINF"], MAGCEN, d(2022,4,20), [
    ("TONER-HP",  20, 24000),
    ("CART-ENC",  30, 14500),
    ("CLE-USB-32",50,  8500),
])

achat(frs["CLEANSER"], MAGCEN, d(2022,5,8), [
    ("DETERG-5L", 60, 2400),
    ("DESINFECT", 40, 2800),
    ("JAVEL-5L",  30, 1800),
])

# Stock entrees 2022: ORD-PORT=20, IMP-LASER=6, VIDEO-PROJ=6 (apres dons)

don(dons_ref["UNESCO"], MAGCEN, d(2022,6,15), [
    ("ORD-PORT",   5, 600000),
    ("VIDEO-PROJ", 3, 260000),
    ("PAPI-A4",  100,      0),
])

don(dons_ref["BANKMONDE"], MAGCEN, d(2022,9,20), [
    ("IMP-LASER",  2, 150000),
    ("CAHIER-100",50,       0),
])

print("  Achats et dons 2022 OK")

# Dotations 2022 (stock suffisant verifie)
dotation(MAGCEN,"Direction Generale",       services["DG"],     d(2022,2,20), [
    ("ORD-PORT",   2, 580000),("VIDEO-PROJ",1, 245000),
    ("BUREAU-STD", 5,  75000),("CHAISE-DIR",8,  32000),
    ("ARMOIRE-MET",2, 115000),("CLIM-15",   1, 300000),
    ("ONDULEUR-1K",1,  45000),("PAPI-A4",  50,   3200),
    ("STYLO-BX", 100,   1800),
])

dotation(MAGCEN,"Scolarite",                services["SCO"],    d(2022,3,15), [
    ("ORD-PORT",   3, 580000),("IMP-LASER", 1, 145000),
    ("BUREAU-STD", 8,  75000),("CHAISE-DIR",10, 32000),
    ("ARMOIRE-MET",3, 115000),("PAPI-A4",  100,  3200),
    ("STYLO-BX", 200,   1800),("CAHIER-100",50,  1400),
])

dotation(MAGCEN,"Service Informatique",     services["INFO"],   d(2022,4,25), [
    ("ORD-PORT",   4, 580000),("IMP-LASER",  2, 145000),
    ("SWITCH-24",  1, 185000),("ONDULEUR-1K",2,  45000),
    ("TONER-HP",   5,  24000),("CART-ENC",  10,  14500),
    ("CLE-USB-32",20,   8500),
])

dotation(MAGCEN,"Bibliotheque",             services["BIB"],    d(2022,6,20), [
    ("ORD-PORT",   2, 580000),("IMP-LASER",  1, 145000),
    ("ORD-DESK",   2, 450000),("BUREAU-STD", 5,  75000),
    ("CHAISE-DIR",10,  32000),("ARMOIRE-MET",2, 115000),
    ("PAPI-A4",   50,   3200),("CAHIER-100",30,   1400),
])

dotation(MAGCEN,"Laboratoire de Geologie",  services["LABGEO"], d(2022,8,10), [
    ("ORD-PORT",   2, 580000),("VIDEO-PROJ", 2, 245000),
    ("BUREAU-STD", 5,  75000),("CHAISE-DIR", 5,  32000),
    ("ARMOIRE-MET",3, 115000),("TONER-HP",   5,  24000),
    ("PAPI-A4",   40,   3200),
])

dotation(MAGCEN,"Laboratoire des Mines",    services["LABMIN"], d(2022,10,5), [
    ("ORD-PORT",   2, 580000),("VIDEO-PROJ", 1, 245000),
    ("BUREAU-STD", 2,  75000),("CHAISE-DIR", 5,  32000),
    ("ARMOIRE-MET",2, 115000),("PAPI-A4",   30,   3200),
    ("CAHIER-100",30,   1400),
])

dotation(MAGCEN,"Service Technique",        services["TECH"],   d(2022,11,15), [
    ("ORD-PORT",   1, 580000),("CLIM-15",    1, 300000),
    ("ONDULEUR-1K",2,  45000),("PAPI-A4",   20,   3200),
    ("DETERG-5L", 20,   2400),("JAVEL-5L",  10,   1800),
])

print("  Dotations 2022 OK")
# Stock restant 2022: ORD-PORT=4, IMP-LASER=2, VIDEO-PROJ=2, SWITCH-24=2, ORD-DESK=3 ...

# ==============================================================
# EXERCICE 2023
# ==============================================================
print("\n--- Exercice 2023 ---")

achat(frs["DITEX"], MAGCEN, d(2023,1,18), [
    ("ORD-PORT",  12, 620000),("ORD-DESK",   4, 480000),
    ("IMP-LASER",  4, 155000),("VIDEO-PROJ", 3, 260000),
    ("ONDULEUR-1K",5,  47000),
], tva=True)

achat(frs["BUREAUSN"], MAGCEN, d(2023,2,15), [
    ("BUREAU-STD",  15,  80000),("CHAISE-DIR",  30,  35000),
    ("CHAISE-VISI", 10,  19000),("ARMOIRE-MET", 10, 120000),
    ("CLIM-15",      3, 320000),
])

achat(frs["PAPMOD"], MAGCEN, d(2023,3,8), [
    ("PAPI-A4",   250, 3300),("STYLO-BX",  400, 1900),
    ("CAHIER-100",150, 1500),("CHEM-CART", 100,  620),
    ("ENVEL-A4",   80,  220),
])

achat(frs["SAHELINF"], MAGCEN, d(2023,4,12), [
    ("TONER-HP",  18, 25000),("CART-ENC",  25, 15000),
    ("CLE-USB-32",35,  9000),
])

achat(frs["CLEANSER"], MAGCEN, d(2023,5,20), [
    ("DETERG-5L", 45, 2500),("DESINFECT", 35, 2900),
    ("JAVEL-5L",  25, 1900),
])

don(dons_ref["GIZ"], MAGCEN, d(2023,8,10), [
    ("ORD-PORT",   4, 640000),("IMP-LASER", 2, 160000),
    ("SWITCH-24",  2, 190000),
])

print("  Achats et dons 2023 OK")

dotation(MAGCEN,"Ressources Humaines",      services["RH"],     d(2023,2,25), [
    ("ORD-PORT",   2, 620000),("BUREAU-STD", 3,  80000),
    ("CHAISE-DIR", 5,  35000),("ARMOIRE-MET",1, 120000),
    ("PAPI-A4",   30,   3300),("STYLO-BX",  50,   1900),
])

dotation(MAGCEN,"Comptabilite et Finances", services["CPT"],    d(2023,3,20), [
    ("ORD-PORT",   2, 620000),("IMP-LASER",  1, 155000),
    ("BUREAU-STD", 4,  80000),("CHAISE-DIR", 8,  35000),
    ("ARMOIRE-MET",2, 120000),("PAPI-A4",   50,   3300),
    ("STYLO-BX", 100,   1900),("CAHIER-100",30,   1500),
])

dotation(MAGCEN,"Service Informatique",     services["INFO"],   d(2023,5,15), [
    ("ORD-PORT",   3, 620000),("IMP-LASER",  1, 155000),
    ("SWITCH-24",  1, 190000),("ONDULEUR-1K",2,  47000),
    ("TONER-HP",   5,  25000),("CART-ENC",  10,  15000),
    ("CLE-USB-32",15,   9000),
])

dotation(MAGCEN,"Laboratoire de Geologie",  services["LABGEO"], d(2023,7,20), [
    ("ORD-PORT",   2, 620000),("ORD-DESK",   2, 480000),
    ("BUREAU-STD", 5,  80000),("CHAISE-DIR", 5,  35000),
    ("ARMOIRE-MET",2, 120000),("PAPI-A4",   30,   3300),
    ("STYLO-BX",  50,   1900),
])

dotation(MAGCEN,"Laboratoire des Mines",    services["LABMIN"], d(2023,9,10), [
    ("ORD-PORT",   3, 620000),("ORD-DESK",   2, 480000),
    ("BUREAU-STD", 3,  80000),("CHAISE-DIR", 5,  35000),
    ("ARMOIRE-MET",2, 120000),("TONER-HP",   3,  25000),
    ("PAPI-A4",   30,   3300),
])

dotation(MAGCEN,"Bibliotheque",             services["BIB"],    d(2023,11,5), [
    ("ORD-PORT",   2, 620000),("IMP-LASER",  1, 155000),
    ("CLIM-15",    1, 320000),("PAPI-A4",   25,   3300),
    ("CAHIER-100",50,   1500),
])

print("  Dotations 2023 OK")

# ==============================================================
# EXERCICE 2024
# ==============================================================
print("\n--- Exercice 2024 ---")

achat(frs["DITEX"], MAGCEN, d(2024,1,20), [
    ("ORD-PORT",  15, 650000),("ORD-DESK",   5, 500000),
    ("IMP-LASER",  5, 160000),("VIDEO-PROJ", 4, 275000),
    ("SWITCH-24",  3, 200000),("ONDULEUR-1K",8,  48000),
], tva=True)

achat(frs["BUREAUSN"], MAGCEN, d(2024,2,14), [
    ("BUREAU-STD",  20,  82000),("CHAISE-DIR",  35,  36000),
    ("CHAISE-VISI", 15,  20000),("ARMOIRE-MET", 15, 125000),
    ("CLIM-15",      5, 330000),
])

achat(frs["PAPMOD"], MAGCEN, d(2024,3,10), [
    ("PAPI-A4",   350, 3400),("STYLO-BX",  500, 2000),
    ("CAHIER-100",200, 1600),("CHEM-CART", 150,  650),
    ("ENVEL-A4",  100,  230),
])

achat(frs["SAHELINF"], MAGCEN, d(2024,4,8), [
    ("TONER-HP",  20, 26000),("CART-ENC",  30, 15500),
    ("CLE-USB-32",45,  9500),
])

achat(frs["CLEANSER"], MAGCEN, d(2024,6,3), [
    ("DETERG-5L", 55, 2600),("DESINFECT", 40, 3000),
    ("JAVEL-5L",  30, 2000),
])

don(dons_ref["UNESCO"], MAGCEN, d(2024,5,20), [
    ("ORD-PORT",   3, 670000),("VIDEO-PROJ", 2, 285000),
    ("PAPI-A4",  150,      0),
])

don(dons_ref["AMBFRANCE"], MAGCEN, d(2024,9,15), [
    ("CAHIER-100",50,       0),("CLIM-15",    2, 340000),
    ("ONDULEUR-1K",3,  50000),
])

print("  Achats et dons 2024 OK")

dotation(MAGCEN,"Direction Generale",       services["DG"],     d(2024,2,20), [
    ("ORD-PORT",   2, 650000),("BUREAU-STD", 5,  82000),
    ("CHAISE-DIR", 5,  36000),("ARMOIRE-MET",2, 125000),
    ("CLIM-15",    1, 330000),("ONDULEUR-1K",2,  48000),
    ("PAPI-A4",   60,   3400),
])

dotation(MAGCEN,"Scolarite",                services["SCO"],    d(2024,3,18), [
    ("ORD-PORT",   3, 650000),("IMP-LASER",  1, 160000),
    ("BUREAU-STD", 5,  82000),("CHAISE-DIR", 8,  36000),
    ("ARMOIRE-MET",3, 125000),("PAPI-A4",   80,   3400),
    ("STYLO-BX", 150,   2000),("CAHIER-100",50,   1600),
])

dotation(MAGCEN,"Service Informatique",     services["INFO"],   d(2024,5,12), [
    ("ORD-PORT",   3, 650000),("IMP-LASER",  2, 160000),
    ("SWITCH-24",  1, 200000),("ONDULEUR-1K",3,  48000),
    ("TONER-HP",   5,  26000),("CART-ENC",  15,  15500),
    ("CLE-USB-32",20,   9500),
])

dotation(MAGCEN,"Laboratoire de Geologie",  services["LABGEO"], d(2024,7,15), [
    ("ORD-PORT",   2, 650000),("VIDEO-PROJ", 2, 275000),
    ("BUREAU-STD", 5,  82000),("CHAISE-DIR", 5,  36000),
    ("ARMOIRE-MET",2, 125000),("PAPI-A4",   50,   3400),
    ("TONER-HP",   3,  26000),
])

dotation(MAGCEN,"Ressources Humaines",      services["RH"],     d(2024,9,20), [
    ("ORD-PORT",   2, 650000),("BUREAU-STD", 4,  82000),
    ("CHAISE-DIR", 5,  36000),("ARMOIRE-MET",2, 125000),
    ("CLIM-15",    2, 330000),("PAPI-A4",   40,   3400),
])

dotation(MAGCEN,"Comptabilite et Finances", services["CPT"],    d(2024,10,8), [
    ("ORD-PORT",   2, 650000),("IMP-LASER",  1, 160000),
    ("BUREAU-STD", 1,  82000),("CHAISE-DIR", 5,  36000),
    ("ARMOIRE-MET",1, 125000),("PAPI-A4",   50,   3400),
    ("STYLO-BX", 100,   2000),("CAHIER-100",40,   1600),
])

dotation(MAGCEN,"Service Technique",        services["TECH"],   d(2024,11,10), [
    ("ORD-PORT",   1, 650000),("ONDULEUR-1K",2,  48000),
    ("CLIM-15",    1, 330000),("PAPI-A4",   30,   3400),
    ("DETERG-5L", 20,   2600),("JAVEL-5L",  10,   2000),
])

print("  Dotations 2024 OK")

# ==============================================================
# EXERCICE 2025
# ==============================================================
print("\n--- Exercice 2025 ---")

achat(frs["DITEX"], MAGCEN, d(2025,1,22), [
    ("ORD-PORT",  12, 680000),("IMP-LASER",  4, 165000),
    ("VIDEO-PROJ", 3, 285000),("SWITCH-24",  2, 210000),
    ("ONDULEUR-1K",6,  50000),
], tva=True)

achat(frs["BUREAUSN"], MAGCEN, d(2025,2,12), [
    ("BUREAU-STD",  18,  85000),("CHAISE-DIR",  30,  37000),
    ("ARMOIRE-MET", 12, 130000),("CLIM-15",      4, 340000),
])

achat(frs["PAPMOD"], MAGCEN, d(2025,3,6), [
    ("PAPI-A4",   300, 3500),("STYLO-BX",  400, 2100),
    ("CAHIER-100",200, 1700),("CHEM-CART", 120,  680),
])

achat(frs["SAHELINF"], MAGCEN, d(2025,4,10), [
    ("TONER-HP",  16, 27000),("CART-ENC",  22, 16000),
    ("CLE-USB-32",30,  9800),
])

achat(frs["CLEANSER"], MAGCEN, d(2025,5,15), [
    ("DETERG-5L", 40, 2700),("DESINFECT", 30, 3100),
    ("JAVEL-5L",  25, 2000),
])

don(dons_ref["BANKMONDE"], MAGCEN, d(2025,5,28), [
    ("ORD-PORT",   4, 700000),("PAPI-A4",  100,      0),
])

don(dons_ref["GIZ"], MAGCEN, d(2025,10,12), [
    ("CAHIER-100",50,       0),("IMP-LASER", 2, 170000),
    ("SWITCH-24",  1, 215000),
])

print("  Achats et dons 2025 OK")

dotation(MAGCEN,"Scolarite",                services["SCO"],    d(2025,2,20), [
    ("ORD-PORT",   2, 680000),("IMP-LASER",  1, 165000),
    ("BUREAU-STD", 5,  85000),("CHAISE-DIR", 8,  37000),
    ("ARMOIRE-MET",2, 130000),("PAPI-A4",   60,   3500),
    ("STYLO-BX", 100,   2100),
])

dotation(MAGCEN,"Direction Generale",       services["DG"],     d(2025,3,18), [
    ("ORD-PORT",   2, 680000),("BUREAU-STD", 4,  85000),
    ("CHAISE-DIR", 5,  37000),("CLIM-15",    1, 340000),
    ("PAPI-A4",   40,   3500),
])

dotation(MAGCEN,"Service Informatique",     services["INFO"],   d(2025,5,20), [
    ("ORD-PORT",   3, 680000),("IMP-LASER",  1, 165000),
    ("SWITCH-24",  1, 210000),("ONDULEUR-1K",2,  50000),
    ("TONER-HP",   4,  27000),("CART-ENC",  10,  16000),
    ("CLE-USB-32",10,   9800),
])

dotation(MAGCEN,"Comptabilite et Finances", services["CPT"],    d(2025,7,10), [
    ("ORD-PORT",   2, 680000),("BUREAU-STD", 3,  85000),
    ("CHAISE-DIR", 4,  37000),("ARMOIRE-MET",2, 130000),
    ("PAPI-A4",   50,   3500),("STYLO-BX",  80,   2100),
    ("CAHIER-100",40,   1700),
])

dotation(MAGCEN,"Laboratoire de Geologie",  services["LABGEO"], d(2025,9,8), [
    ("ORD-PORT",   2, 680000),("VIDEO-PROJ", 1, 285000),
    ("BUREAU-STD", 3,  85000),("CHAISE-DIR", 4,  37000),
    ("ARMOIRE-MET",2, 130000),("PAPI-A4",   30,   3500),
    ("TONER-HP",   3,  27000),
])

dotation(MAGCEN,"Laboratoire des Mines",    services["LABMIN"], d(2025,11,5), [
    ("ORD-PORT",   2, 680000),("VIDEO-PROJ", 1, 285000),
    ("BUREAU-STD", 3,  85000),("CHAISE-DIR", 4,  37000),
    ("ARMOIRE-MET",2, 130000),("PAPI-A4",   30,   3500),
    ("CAHIER-100",40,   1700),
])

print("  Dotations 2025 OK")

# ==============================================================
# EXERCICE 2026 (annee courante - operations partielles)
# ==============================================================
print("\n--- Exercice 2026 (annee courante) ---")

achat(frs["DITEX"], MAGCEN, d(2026,1,20), [
    ("ORD-PORT",  15, 700000),("ORD-DESK",   5, 540000),
    ("IMP-LASER",  5, 170000),("VIDEO-PROJ", 4, 295000),
    ("SWITCH-24",  3, 215000),("ONDULEUR-1K",8,  52000),
], tva=True)

achat(frs["BUREAUSN"], MAGCEN, d(2026,2,8), [
    ("BUREAU-STD",  20,  88000),("CHAISE-DIR",  35,  38000),
    ("CHAISE-VISI", 12,  22000),("ARMOIRE-MET", 15, 135000),
    ("CLIM-15",      5, 350000),
])

achat(frs["PAPMOD"], MAGCEN, d(2026,1,25), [
    ("PAPI-A4",   300, 3600),("STYLO-BX",  450, 2200),
    ("CAHIER-100",200, 1800),("CHEM-CART", 150,  700),
    ("ENVEL-A4",  100,  250),
])

achat(frs["SAHELINF"], MAGCEN, d(2026,3,12), [
    ("TONER-HP",  18, 28000),("CART-ENC",  25, 16500),
    ("CLE-USB-32",40,  10000),
])

achat(frs["CLEANSER"], MAGCEN, d(2026,3,20), [
    ("DETERG-5L", 50, 2750),("DESINFECT", 35, 3200),
    ("JAVEL-5L",  28, 2100),
])

don(dons_ref["GIZ"], MAGCEN, d(2026,3,28), [
    ("ORD-PORT",   3, 720000),("PAPI-A4",   80,      0),
])

print("  Achats et dons 2026 OK")

dotation(MAGCEN,"Direction Generale",       services["DG"],     d(2026,2,15), [
    ("ORD-PORT",   2, 700000),("BUREAU-STD", 4,  88000),
    ("CHAISE-DIR", 5,  38000),("ARMOIRE-MET",2, 135000),
    ("PAPI-A4",   50,   3600),
])

dotation(MAGCEN,"Scolarite",                services["SCO"],    d(2026,3,10), [
    ("ORD-PORT",   2, 700000),("IMP-LASER",  1, 170000),
    ("BUREAU-STD", 5,  88000),("CHAISE-DIR", 8,  38000),
    ("ARMOIRE-MET",2, 135000),("PAPI-A4",   60,   3600),
    ("STYLO-BX", 100,   2200),
])

dotation(MAGCEN,"Service Informatique",     services["INFO"],   d(2026,4,5), [
    ("ORD-PORT",   3, 700000),("IMP-LASER",  1, 170000),
    ("SWITCH-24",  1, 215000),("ONDULEUR-1K",2,  52000),
    ("TONER-HP",   4,  28000),("CART-ENC",  10,  16500),
    ("CLE-USB-32",15,  10000),
])

print("  Dotations 2026 OK")

# ==============================================================
# RECAPITULATIF
# ==============================================================
from inventory.models import MouvementStock, StockCourant
from purchasing.models import Achat, Don, Dotation

print("\n===== RECAP =====")
print(f"Exercices   : {Exercice.objects.count()}")
print(f"Fournisseurs: {Fournisseur.objects.count()}")
print(f"Donateurs   : {Donateur.objects.count()}")
print(f"Services    : {Service.objects.count()}")
print(f"Depots      : {Depot.objects.count()}")
print(f"Matieres    : {Matiere.objects.count()}")
print(f"Achats      : {Achat.objects.count()}")
print(f"Dons        : {Don.objects.count()}")
print(f"Dotations   : {Dotation.objects.count()}")
print(f"Mouvements  : {MouvementStock.objects.count()}")
print(f"StockCourant: {StockCourant.objects.count()} lignes")
print("\nSeed premium termine avec succes !")
