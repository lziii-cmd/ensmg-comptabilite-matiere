# scripts/seed_db.py
# Seed DB ENSMG - Comptabilité Matières
# Exécution: python manage.py shell < scripts/seed_db.py

from decimal import Decimal
from datetime import datetime, date
from django.utils import timezone
from django.db import transaction
from django.apps import apps


# =============================================================================
# 0) DONNÉES À PERSONNALISER (4 blocs)
# =============================================================================

# 1) EXERCICES (année, date_debut, date_fin, statut: "OUVERT" / "CLOS")
EXERCICES = [
    # Exemple
    {"annee": 2024, "date_debut": date(2024, 1, 1), "date_fin": date(2024, 12, 31), "statut": "CLOS"},
    {"annee": 2025, "date_debut": date(2025, 1, 1), "date_fin": date(2025, 12, 31), "statut": "OUVERT"},
]

# 2) SERVICES (nom, responsable_nom)
SERVICES = [
    {"nom": "Finances", "responsable": "M. Diop"},
    {"nom": "Informatique", "responsable": "M. Fall"},
    {"nom": "Scolarité", "responsable": "Mme Ndiaye"},
]

# 3) DEPOTS + BUREAUX
# - depots: lieux de stock
# - bureaux: lieux d’affectation (stock interne, prélevé d’un dépôt)
DEPOTS = [
    {"identifiant": "MAG-CENTRAL", "nom": "Magasin Central", "localisation": "RDC", "actif": True},
    {"identifiant": "MAG-INFO", "nom": "Magasin Informatique", "localisation": "Bâtiment A", "actif": True},
]

BUREAUX = [
    {"identifiant": "BUR-FIN-02", "nom": "Bureau Finance 2", "localisation": "Etage 1", "actif": True, "service": "Finances"},
    {"identifiant": "BUR-INF-02", "nom": "Bureau Informatique 2", "localisation": "Etage 2", "actif": True, "service": "Informatique"},
]

# 4) CATALOGUE + STOCKS INITIAUX + AFFECTATIONS
# NB: selon ton projet, tes modèles peuvent être dans "catalog" / "core" etc.
CATEGORIES = [
    {"libelle": "Mobilier", "description": "Chaises, bureaux, armoires"},
    {"libelle": "Informatique", "description": "PC, imprimantes, accessoires"},
]

SOUS_CATEGORIES = [
    {"libelle": "Chaises", "categorie": "Mobilier"},
    {"libelle": "Bureaux", "categorie": "Mobilier"},
    {"libelle": "Ordinateurs", "categorie": "Informatique"},
    {"libelle": "Imprimantes", "categorie": "Informatique"},
]

# Matières minimales (code_court unique)
MATIERES = [
    {"code_court": "CHAISE", "designation": "Chaise de bureau", "sous_categorie": "Chaises"},
    {"code_court": "BUREAU", "designation": "Bureau standard", "sous_categorie": "Bureaux"},
    {"code_court": "PC", "designation": "Ordinateur Portable", "sous_categorie": "Ordinateurs"},
    {"code_court": "IMPR", "designation": "Imprimante Laser", "sous_categorie": "Imprimantes"},
]

# Stock initial par dépôt
# format: (depot_identifiant, matiere_code_court) -> quantite
STOCK_INITIAL = {
    ("MAG-CENTRAL", "CHAISE"): Decimal("100"),
    ("MAG-CENTRAL", "BUREAU"): Decimal("40"),
    ("MAG-INFO", "PC"): Decimal("25"),
    ("MAG-INFO", "IMPR"): Decimal("5"),
}

# Affectations (prélèvement dépôt -> bureau)
AFFECTATIONS = [
    # 5 chaises de MAG-CENTRAL vers Bureau Finance 2
    {"source_depot": "MAG-CENTRAL", "bureau": "BUR-FIN-02", "matiere": "CHAISE", "quantite": Decimal("5")},
    {"source_depot": "MAG-INFO", "bureau": "BUR-INF-02", "matiere": "PC", "quantite": Decimal("2")},
]

# Quelques achats, dons, sorties, transferts (générés automatiquement sur l'exercice OUVERT)
NB_ACHATS = 3
NB_DONS = 2
NB_SORTIES = 2
NB_TRANSFERTS = 2


# =============================================================================
# 1) HELPERS / RESOLUTION MODELES
# =============================================================================

def get_model(app_label, model_name):
    return apps.get_model(app_label, model_name)

def aware_midnight(d: date):
    tz = timezone.get_current_timezone()
    return datetime.combine(d, datetime.min.time(), tzinfo=tz)

def get_open_exercice():
    Exercice = get_model("core", "Exercice")
    # on privilégie OUVERT (sinon le + récent)
    ex = Exercice.objects.filter(statut=getattr(Exercice.Statut, "OUVERT", "OUVERT")).order_by("-date_debut").first()
    if ex:
        return ex
    return Exercice.objects.order_by("-date_debut").first()

def ensure(obj, defaults=None, **lookup):
    defaults = defaults or {}
    instance, created = obj.objects.get_or_create(**lookup, defaults=defaults)
    if not created and defaults:
        changed = False
        for k, v in defaults.items():
            if getattr(instance, k) != v:
                setattr(instance, k, v)
                changed = True
        if changed:
            instance.save()
    return instance

def pick(seq, i):
    return seq[i % len(seq)]


# =============================================================================
# 2) SEED
# =============================================================================

@transaction.atomic
def run():
    print("==> Seed: démarrage")

    # --- Models ---
    Exercice = get_model("core", "Exercice")
    Depot = get_model("core", "Depot")

    # Certains projets ont Service dans core, d'autres non.
    # Si tu n'as pas encore Service, commente le bloc "Service".
    try:
        Service = get_model("core", "Service")
        HAS_SERVICE = True
    except Exception:
        Service = None
        HAS_SERVICE = False

    Categorie = get_model("catalog", "Categorie")
    SousCategorie = get_model("catalog", "SousCategorie")
    Matiere = get_model("catalog", "Matiere")

    MouvementStock = get_model("inventory", "MouvementStock")

    # Achats / Dons (selon ton projet, c'est "purchasing" avec Achat/Don)
    Achat = get_model("purchasing", "Achat")
    LigneAchat = get_model("purchasing", "LigneAchat")
    Don = get_model("purchasing", "Don")
    LigneDon = get_model("purchasing", "LigneDon")

    Fournisseur = get_model("core", "Fournisseur")
    Donateur = get_model("core", "Donateur")

    # Sorties définitives (operation_sortie)
    OperationSortie = get_model("inventory", "OperationSortie")
    LigneOperationSortie = get_model("inventory", "LigneOperationSortie")

    print("==> (1) Exercices")
    # Adapter si ton modèle Exercice a d'autres champs obligatoires
    for e in EXERCICES:
        # statut: "OUVERT"/"CLOS" -> Exercice.Statut.*
        statut = e["statut"]
        if hasattr(Exercice, "Statut"):
            statut = getattr(Exercice.Statut, e["statut"], e["statut"])
        ensure(
            Exercice,
            annee=e["annee"],
            defaults={
                "date_debut": e["date_debut"],
                "date_fin": e["date_fin"],
                "statut": statut,
            },
        )

    ex_open = get_open_exercice()
    if not ex_open:
        raise RuntimeError("Aucun exercice trouvé. Vérifie EXERCICES.")

    print(f"   -> Exercice ouvert: {getattr(ex_open, 'annee', ex_open)}")

    print("==> (2) Services")
    services_map = {}
    if HAS_SERVICE:
        for s in SERVICES:
            srv = ensure(Service, nom=s["nom"], defaults={"responsable": s["responsable"]})
            services_map[s["nom"]] = srv
    else:
        print("   (Service non trouvé dans core.Service: ok si pas encore créé)")

    print("==> (3) Dépôts & bureaux (même modèle Depot)")
    depots_map = {}
    for d in DEPOTS:
        dep = ensure(
            Depot,
            identifiant=d["identifiant"],
            defaults={
                "nom": d["nom"],
                "localisation": d.get("localisation", ""),
                "actif": d.get("actif", True),
            },
        )
        depots_map[d["identifiant"]] = dep

    for b in BUREAUX:
        dep = ensure(
            Depot,
            identifiant=b["identifiant"],
            defaults={
                "nom": b["nom"],
                "localisation": b.get("localisation", ""),
                "actif": b.get("actif", True),
            },
        )
        # Si tu as ajouté plus tard des champs bureau (service/responsable) sur Depot,
        # tu peux les setter ici.
        if HAS_SERVICE and "service" in b and hasattr(dep, "service_id"):
            dep.service = services_map.get(b["service"])
            dep.save(update_fields=["service"])
        depots_map[b["identifiant"]] = dep

    print("==> (4) Catégories / Sous-catégories / Matières")
    cats = {}
    for c in CATEGORIES:
        obj = ensure(Categorie, libelle=c["libelle"], defaults={"description": c.get("description", ""), "actif": True})
        cats[c["libelle"]] = obj

    sous = {}
    for sc in SOUS_CATEGORIES:
        cat = cats[sc["categorie"]]
        obj = ensure(
            SousCategorie,
            categorie=cat,
            libelle=sc["libelle"],
            defaults={"description": "", "actif": True},
        )
        sous[sc["libelle"]] = obj

    mat_map = {}
    for m in MATIERES:
        sc = sous[m["sous_categorie"]]
        # Matiere.save() dérive categorie automatiquement chez toi
        obj = ensure(
            Matiere,
            code_court=m["code_court"],
            defaults={
                "designation": m["designation"],
                "sous_categorie": sc,
                "actif": True,
            },
        )
        mat_map[m["code_court"]] = obj

    print("==> (5) Stock initial (MouvementStock ENTREE + is_stock_initial=True)")
    # On place le stock initial sur l'exercice OUVERT (tu peux changer)
    for (depot_idf, mat_code), qte in STOCK_INITIAL.items():
        depot = depots_map[depot_idf]
        mat = mat_map[mat_code]

        mvt, created = MouvementStock.objects.get_or_create(
            type=MouvementStock.Type.ENTREE,
            exercice=ex_open,
            depot=depot,
            matiere=mat,
            is_stock_initial=True,
            defaults={
                "date": aware_midnight(ex_open.date_debut),
                "quantite": qte,
                "cout_unitaire": Decimal("0"),
                "reference": f"INIT-{getattr(ex_open,'annee','')}",
                "commentaire": "Stock initial (seed)",
                "source_doc_type": "seed.StockInitial",
                "source_doc_id": int(f"{depot.pk}{mat.pk}"),
            },
        )
        if created:
            # Optionnel : marquer Matiere.est_stocke=True si ton modèle l’a
            if hasattr(mat, "est_stocke") and not mat.est_stocke:
                mat.est_stocke = True
                mat.save(update_fields=["est_stocke"])

    print("==> (6) Fournisseurs + Donateurs")
    # Fournisseurs
    fournisseurs = []
    for name in ["ELECTRO PLUS", "BTP SERVICES", "PAPETERIE CENTRALE"]:
        f = ensure(Fournisseur, raison_sociale=name, defaults={"adresse": "", "numero": "", "courriel": ""})
        fournisseurs.append(f)

    # Donateurs (ton format demandé: DON-NOM DONATEUR-2025-0001)
    # On force un nom, et on laisse le modèle générer identifiant si tu as déjà codé différemment.
    donateurs = []
    for name in ["AMIS ENSMG", "ONG EDUCATION"]:
        d = ensure(Donateur, raison_sociale=name, defaults={"code_prefix": "", "adresse": "", "telephone": "", "courriel": "", "actif": True})
        donateurs.append(d)

    # --- Petites fonctions pour créer Achat/Don avec lignes ---
    def create_achat(i: int):
        f = pick(fournisseurs, i)
        depot = pick(list(depots_map.values()), i)
        d_achat = date(getattr(ex_open, "annee", timezone.now().year), 1, min(10 + i, 28))

        achat = Achat.objects.create(
            fournisseur=f,
            date_achat=d_achat,
            tva_active=(i % 2 == 0),
            depot=depot,
            commentaire="Achat seed",
            numero_facture=f"F-{getattr(ex_open,'annee','')}-{i+1:03d}",
        )
        # 2 lignes
        mats = list(mat_map.values())
        for j in range(2):
            mat = mats[(i + j) % len(mats)]
            q = Decimal("2") + Decimal(i + j)
            pu = Decimal("10000") + Decimal((i + j) * 1500)
            LigneAchat.objects.create(
                achat=achat,
                matiere=mat,
                quantite=q,
                prix_unitaire=pu,
                appreciation="Ligne achat seed",
            )
        # triggers admin normally creates mouvements; ici on ne passe pas par admin.
        # Si tu veux simuler les mouvements, on peut en créer ici aussi (ENTREE).
        return achat

    def create_don(i: int):
        dnr = pick(donateurs, i)
        depot = pick(list(depots_map.values()), i + 1)
        d_don = date(getattr(ex_open, "annee", timezone.now().year), 2, min(5 + i, 28))

        don = Don.objects.create(
            donateur=dnr,
            date_don=d_don,
            depot=depot,
            commentaire="Don seed",
            numero_piece=f"PV-DON-{getattr(ex_open,'annee','')}-{i+1:03d}",
        )
        mats = list(mat_map.values())
        for j in range(2):
            mat = mats[(i + 1 + j) % len(mats)]
            q = Decimal("1") + Decimal(j)
            pu = Decimal("0")
            LigneDon.objects.create(
                don=don,
                matiere=mat,
                quantite=q,
                prix_unitaire=pu,
                observation="Ligne don seed",
            )
        return don

    print("==> (7) Générer achats / dons (sur exercice OUVERT)")
    for i in range(NB_ACHATS):
        create_achat(i)
    for i in range(NB_DONS):
        create_don(i)

    print("==> (8) Transferts dépôt -> dépôt (MouvementStock TRANSFERT)")
    dep_list = [depots_map[d["identifiant"]] for d in DEPOTS]
    if len(dep_list) >= 2:
        for i in range(NB_TRANSFERTS):
            src = dep_list[i % len(dep_list)]
            dst = dep_list[(i + 1) % len(dep_list)]
            mat = pick(list(mat_map.values()), i)
            q = Decimal("1") + Decimal(i)

            MouvementStock.objects.create(
                type=MouvementStock.Type.TRANSFERT,
                date=aware_midnight(date(getattr(ex_open,"annee",timezone.now().year), 3, min(10+i, 28))),
                exercice=ex_open,
                matiere=mat,
                depot=None,
                source_depot=src,
                destination_depot=dst,
                quantite=q,
                cout_unitaire=Decimal("0"),
                reference=f"TRF-{getattr(ex_open,'annee','')}-{i+1:03d}",
                commentaire="Transfert seed",
                source_doc_type="seed.Transfert",
                source_doc_id=1000 + i,
            )

    print("==> (9) Sorties définitives (OperationSortie + lignes)")
    # On en crée quelques-unes sur l'exercice OUVERT
    # IMPORTANT: ce modèle doit exister (inventory.OperationSortie)
    if OperationSortie:
        dep = dep_list[0]
        for i in range(NB_SORTIES):
            s = OperationSortie.objects.create(
                date_sortie=date(getattr(ex_open,"annee",timezone.now().year), 4, min(10+i, 28)),
                depot=dep,
                type_sortie=getattr(OperationSortie.TypeSortie, "REFORME_DESTRUCTION", "REFORME_DESTRUCTION"),
                motif_principal="Réforme / destruction (seed)",
                commentaire="Sortie définitive seed",
            )
            mat = pick(list(mat_map.values()), i)
            LigneOperationSortie.objects.create(
                operation=s,
                matiere=mat,
                quantite=Decimal("1"),
                prix_unitaire=Decimal("0"),
                commentaire="Ligne sortie seed",
            )

    print("==> (10) Affectations bureau (si tu as déjà ton modèle Affectation plus tard, on branchera)")
    # Ici, pour l’instant, on NE crée pas (car tu n’as pas encore envoyé ton modèle affectation).
    # Les données AFFECTATIONS sont prêtes: dès que ton modèle existe, on les instancie ici.

    print("✅ Seed terminé avec succès.")


run()
