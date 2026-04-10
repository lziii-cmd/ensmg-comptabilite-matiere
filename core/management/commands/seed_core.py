# core/management/commands/seed_core.py
import random
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.apps import apps


def model_has_field(Model, field_name: str) -> bool:
    return any(f.name == field_name for f in Model._meta.get_fields())


def is_fk_field(Model, field_name: str) -> bool:
    for f in Model._meta.get_fields():
        if f.name == field_name:
            return getattr(f, "many_to_one", False) and getattr(f, "related_model", None) is not None
    return False


class Command(BaseCommand):
    help = "Seed CORE: exercices, services, depots/bureaux, donateurs, fournisseurs, sequences."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Supprime les données core avant reseed.")
        parser.add_argument("--year", type=int, default=timezone.now().year, help="Année N (exercice courant).")
        parser.add_argument("--scale", choices=["small", "medium", "large"], default="medium")

    @transaction.atomic
    def handle(self, *args, **opts):
        random.seed(42)

        year = opts["year"]
        scale = opts["scale"]
        reset = opts["reset"]

        self.stdout.write(self.style.MIGRATE_HEADING(f"SEED_CORE (year={year}, scale={scale}, reset={reset})"))

        # Models
        Exercice = apps.get_model("core", "Exercice")
        Service = apps.get_model("core", "Service")
        Depot = apps.get_model("core", "Depot")
        Fournisseur = apps.get_model("core", "Fournisseur")
        Donateur = apps.get_model("core", "Donateur")

        Sequence = apps.get_model("core", "Sequence")
        FournisseurSequence = apps.get_model("core", "FournisseurSequence")

        # constants
        try:
            from core.constants import PIECE_TYPE_CHOICES
        except Exception as e:
            raise Exception("Impossible d'importer core.constants.PIECE_TYPE_CHOICES") from e

        if reset:
            self._reset_all(
                Depot=Depot,
                Service=Service,
                Exercice=Exercice,
                Fournisseur=Fournisseur,
                Donateur=Donateur,
                Sequence=Sequence,
                FournisseurSequence=FournisseurSequence,
            )

        exos = self._seed_exercices(Exercice, year)
        exo_current = Exercice.objects.filter(annee=year).first() or exos[1]

        services = self._seed_services(Service, scale=scale)
        depots, bureaux = self._seed_depots_bureaux(Depot, services)
        fournisseurs = self._seed_fournisseurs(Fournisseur, scale=scale)
        donateurs = self._seed_donateurs(Donateur, scale=scale)

        self._seed_sequences(Sequence, exos, PIECE_TYPE_CHOICES)
        self._seed_fournisseur_sequences(FournisseurSequence, fournisseurs, year)

        self.stdout.write(self.style.SUCCESS("✅ Seed CORE terminé avec succès."))
        self.stdout.write(
            f"Résumé: Exercices={len(exos)} | Services={len(services)} | Depots={len(depots)} | "
            f"Bureaux={len(bureaux)} | Fournisseurs={len(fournisseurs)} | Donateurs={len(donateurs)}"
        )

    # -------------------------
    # RESET
    # -------------------------
    def _reset_all(self, Depot, Service, Exercice, Fournisseur, Donateur, Sequence, FournisseurSequence):
        self.stdout.write(self.style.WARNING("RESET: suppression données core..."))

        FournisseurSequence.objects.all().delete()
        self.stdout.write(" - deleted core.FournisseurSequence")

        Sequence.objects.all().delete()
        self.stdout.write(" - deleted core.Sequence")

        Donateur.objects.all().delete()
        self.stdout.write(" - deleted core.Donateur")

        Fournisseur.objects.all().delete()
        self.stdout.write(" - deleted core.Fournisseur")

        Depot.objects.all().delete()
        self.stdout.write(" - deleted core.Depot")

        Service.objects.all().delete()
        self.stdout.write(" - deleted core.Service")

        Exercice.objects.all().delete()
        self.stdout.write(" - deleted core.Exercice")

        self.stdout.write(self.style.SUCCESS("RESET core OK."))

    # -------------------------
    # EXERCICES
    # -------------------------
    def _seed_exercices(self, Exercice, year: int):
        years = [year - 1, year, year + 1]
        out = []

        for y in years:
            ex = Exercice.objects.filter(annee=y).first()
            if not ex:
                kwargs = {"annee": y}

                # si ton Exercice a un champ statut
                if model_has_field(Exercice, "statut") and hasattr(Exercice, "Statut"):
                    kwargs["statut"] = Exercice.Statut.OUVERT if y == year else Exercice.Statut.CLOS

                ex = Exercice(**kwargs)
                ex.save()

            # ajuster statut
            if model_has_field(Exercice, "statut") and hasattr(Exercice, "Statut"):
                target = Exercice.Statut.OUVERT if y == year else Exercice.Statut.CLOS
                if ex.statut != target:
                    ex.statut = target
                    ex.save(update_fields=["statut"])

            out.append(ex)

        self.stdout.write(self.style.SUCCESS(f"Exercices: {len(out)}"))
        return out

    # -------------------------
    # SERVICES
    # -------------------------
    def _seed_services(self, Service, scale: str):
        base = [
            ("DIR", "Direction", "Directeur"),
            ("ADM", "Administration", "Chef Administration"),
            ("FIN", "Comptabilité / Finance", "Chef Finance"),
            ("INF", "Service Informatique", "Responsable IT"),
            ("LOG", "Logistique", "Chef Logistique"),
            ("LAB", "Laboratoires", "Chef Lab"),
            ("BIB", "Bibliothèque", "Chef Bibliothèque"),
            ("SEC", "Sécurité", "Chef Sécurité"),
            ("PAT", "Patrimoine / Maintenance", "Chef Maintenance"),
            ("PED", "Pédagogie", "Responsable Pédagogie"),
            ("SCOL", "Scolarité", "Chef Scolarité"),
        ]
        if scale == "small":
            data = base[:8]
        elif scale == "large":
            data = base
        else:
            data = base[:10]

        out = {}
        for code, lib, resp in data:
            s = Service.objects.filter(code=code).first()
            if not s:
                kwargs = {"code": code}
                if model_has_field(Service, "libelle"):
                    kwargs["libelle"] = lib
                if model_has_field(Service, "responsable"):
                    kwargs["responsable"] = resp
                if model_has_field(Service, "actif"):
                    kwargs["actif"] = True
                s = Service(**kwargs)
                s.save()
            else:
                updates = []
                if model_has_field(Service, "libelle") and getattr(s, "libelle", None) != lib:
                    s.libelle = lib
                    updates.append("libelle")
                if model_has_field(Service, "responsable") and getattr(s, "responsable", None) != resp:
                    s.responsable = resp
                    updates.append("responsable")
                if model_has_field(Service, "actif") and getattr(s, "actif", True) is False:
                    s.actif = True
                    updates.append("actif")
                if updates:
                    s.save(update_fields=updates)

            out[code] = s

        self.stdout.write(self.style.SUCCESS(f"Services: {len(out)}"))
        return out

    # -------------------------
    # DEPOTS + BUREAUX
    # -------------------------
    def _seed_depots_bureaux(self, Depot, services_map):
        depot_has_service = model_has_field(Depot, "service")
        depot_service_is_fk = is_fk_field(Depot, "service") if depot_has_service else False

        # required fields
        for req in ["identifiant", "nom", "type_lieu"]:
            if not model_has_field(Depot, req):
                raise Exception(f"Depot doit avoir le champ '{req}'")

        has_actif = model_has_field(Depot, "actif")

        depots_mag = []
        depots_bureaux = []

        depots_data = [
            ("MAG-CENT", "Magasin Central"),
            ("MAG-INF", "Magasin Informatique"),
            ("MAG-MOB", "Magasin Mobilier"),
            ("MAG-LAB", "Magasin Laboratoire"),
        ]

        for ident, nom in depots_data:
            d = Depot.objects.filter(identifiant=ident).first()
            if not d:
                kwargs = {
                    "identifiant": ident,
                    "nom": nom,
                    "type_lieu": Depot.TypeLieu.DEPOT,
                }
                if has_actif:
                    kwargs["actif"] = True
                d = Depot(**kwargs)
                d.save()
            depots_mag.append(d)

        bureaux_data = [
            ("B-DIR-01", "Bureau Direction", "DIR"),
            ("B-ADM-01", "Bureau Administration", "ADM"),
            ("B-FIN-01", "Bureau Finance", "FIN"),
            ("B-INF-01", "Bureau Informatique", "INF"),
            ("B-LOG-01", "Bureau Logistique", "LOG"),
            ("B-LAB-01", "Laboratoire 1", "LAB"),
            ("B-BIB-01", "Bibliothèque", "BIB"),
            ("B-SEC-01", "Poste Sécurité", "SEC"),
        ]

        for ident, nom, service_code in bureaux_data:
            s = services_map[service_code]
            d = Depot.objects.filter(identifiant=ident).first()
            if not d:
                kwargs = {
                    "identifiant": ident,
                    "nom": nom,
                    "type_lieu": Depot.TypeLieu.BUREAU,
                }
                if has_actif:
                    kwargs["actif"] = True

                if depot_has_service:
                    if depot_service_is_fk:
                        kwargs["service"] = s
                    else:
                        kwargs["service"] = f"{s.code} — {getattr(s, 'libelle', '')}".strip()

                d = Depot(**kwargs)
                d.save()

            depots_bureaux.append(d)

        self.stdout.write(self.style.SUCCESS(f"Dépôts: {len(depots_mag)} | Bureaux: {len(depots_bureaux)}"))
        return depots_mag, depots_bureaux

    # -------------------------
    # FOURNISSEURS
    # -------------------------
    def _seed_fournisseurs(self, Fournisseur, scale: str):
        if scale == "small":
            n = 10
        elif scale == "large":
            n = 80
        else:
            n = 35

        pool = [
            "SEN TECH SARL", "AFRIMAT", "ELECTRO PLUS", "GLOBAL OFFICE", "LAB SUPPLIES",
            "MOBILIER PRO", "NET PLUS", "DIGI STORE", "SAHEL COMMERCE", "URBAN STOCK",
            "FOURNITURE EXPRESS", "KHEWEUL SERVICES", "DAKAR BUSINESS", "SEN MARKET", "PRO LOGISTIC",
            "EQUIPEMENTS MINES", "GEO TOOLS", "ENERGIE SERVICES", "SECURITE PRO", "LABO CENTER",
        ]

        out = []
        for _ in range(n):
            rs = f"{random.choice(pool)} {random.randint(1, 999)}"
            f = Fournisseur.objects.filter(raison_sociale=rs).first()
            if not f:
                kwargs = {"raison_sociale": rs}

                if model_has_field(Fournisseur, "adresse"):
                    kwargs["adresse"] = f"Rue {random.randint(1, 200)}"
                if model_has_field(Fournisseur, "numero"):
                    kwargs["numero"] = f"+221 77 {random.randint(100,999)} {random.randint(100,999)}"
                if model_has_field(Fournisseur, "telephone"):
                    kwargs["telephone"] = f"+221 77 {random.randint(100,999)} {random.randint(100,999)}"
                if model_has_field(Fournisseur, "courriel"):
                    kwargs["courriel"] = f"contact{random.randint(1,9999)}@example.com"
                if model_has_field(Fournisseur, "ninea"):
                    kwargs["ninea"] = None

                # si tu as code_prefix
                if model_has_field(Fournisseur, "code_prefix"):
                    # prefix stable (3 lettres)
                    base = "".join([c for c in rs.upper() if c.isalpha()])[:3] or "FOU"
                    kwargs["code_prefix"] = base

                f = Fournisseur(**kwargs)
                f.save()
            out.append(f)

        self.stdout.write(self.style.SUCCESS(f"Fournisseurs: {len(out)}"))
        return out

    # -------------------------
    # DONATEURS
    # -------------------------
    def _seed_donateurs(self, Donateur, scale: str):
        if scale == "small":
            n = 10
        elif scale == "large":
            n = 50
        else:
            n = 25

        pool = [
            "Association des Anciens", "ONG Éducation", "Fondation Solidarité", "Partenaire Privé",
            "Ami de l'École", "Entreprise Sponsor", "Collectif Alumni", "Donateur anonyme",
            "Coopération", "Projet Appui", "Réseau Alumni", "Fondation Recherche",
        ]

        out = []
        for _ in range(n):
            rs = f"{random.choice(pool)} {random.randint(1, 999)}"
            d = Donateur.objects.filter(raison_sociale=rs).first()
            if not d:
                kwargs = {"raison_sociale": rs}
                if model_has_field(Donateur, "adresse"):
                    kwargs["adresse"] = f"Adresse {random.randint(1, 200)}"
                if model_has_field(Donateur, "telephone"):
                    kwargs["telephone"] = f"+221 76 {random.randint(100,999)} {random.randint(100,999)}"
                if model_has_field(Donateur, "courriel"):
                    kwargs["courriel"] = f"don{random.randint(1,9999)}@example.com"
                if model_has_field(Donateur, "remarque"):
                    kwargs["remarque"] = ""
                if model_has_field(Donateur, "actif"):
                    kwargs["actif"] = True

                d = Donateur(**kwargs)
                d.save()
            out.append(d)

        self.stdout.write(self.style.SUCCESS(f"Donateurs: {len(out)}"))
        return out

    # -------------------------
    # SEQUENCES (EXERCICE x TYPE_PIECE)
    # -------------------------
    def _seed_sequences(self, Sequence, exercices, PIECE_TYPE_CHOICES):
        # choices: [("ACH","Achat"), ...]
        types = [t[0] for t in PIECE_TYPE_CHOICES]

        created = 0
        for exo in exercices:
            for t in types:
                obj = Sequence.objects.filter(type_piece=t, exercice=exo).first()
                if not obj:
                    Sequence.objects.create(type_piece=t, exercice=exo, dernier_numero=0)
                    created += 1

        self.stdout.write(self.style.SUCCESS(f"Sequences: {created} créées (type_piece x exercice)"))

    # -------------------------
    # FOURNISSEUR SEQUENCES (FOURNISSEUR x ANNEE x ACH/RET)
    # -------------------------
    def _seed_fournisseur_sequences(self, FournisseurSequence, fournisseurs, year: int):
        created = 0
        for f in fournisseurs:
            for t in ["ACH", "RET"]:
                obj = FournisseurSequence.objects.filter(fournisseur=f, annee=year, type_doc=t).first()
                if not obj:
                    FournisseurSequence.objects.create(fournisseur=f, annee=year, type_doc=t, next_seq=1)
                    created += 1
        self.stdout.write(self.style.SUCCESS(f"FournisseurSequence: {created} créées (ACH/RET)"))
