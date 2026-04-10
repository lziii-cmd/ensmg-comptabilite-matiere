# purchasing/management/commands/seed_purchasing.py
import random
import re
from decimal import Decimal
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.apps import apps


def rand_date_in_year(year: int) -> date:
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))


def pick_weighted(items):
    # items = [(value, weight), ...]
    total = sum(w for _, w in items)
    r = random.uniform(0, total)
    upto = 0
    for v, w in items:
        if upto + w >= r:
            return v
        upto += w
    return items[-1][0]


def _slug_prefix(text: str, max_len: int = 10) -> str:
    # Garde lettres+chiffres, prend des initiales simples
    words = re.findall(r"[A-Za-z0-9]+", (text or "").upper())
    if not words:
        return "FOU"
    initials = "".join(w[0] for w in words)[:max_len]
    return initials or (words[0][:max_len] if words else "FOU")


def _ensure_unique_prefix_for_queryset(qs, field_name="code_prefix", fallback="FOU"):
    """
    Assure que chaque objet du queryset a un code_prefix non vide et UNIQUE.
    - si vide -> générer à partir du nom/raison_sociale
    - si doublon -> suffixer 2 chiffres
    """
    used = set()

    # précharger existants
    for obj in qs:
        p = (getattr(obj, field_name, "") or "").upper().strip()
        if p:
            used.add(p)

    for obj in qs:
        cur = (getattr(obj, field_name, "") or "").upper().strip()
        if cur and cur not in used:
            used.add(cur)

    # Deuxième passe: corriger vides et doublons
    already = set()
    for obj in qs:
        p = (getattr(obj, field_name, "") or "").upper().strip()

        # nom pour dériver
        base_name = getattr(obj, "raison_sociale", "") or getattr(obj, "nom", "") or str(obj)

        if not p:
            base = _slug_prefix(base_name, 8) or fallback
            candidate = base
            i = 1
            while candidate in already:
                i += 1
                candidate = f"{base}{i:02d}"[:12]
            setattr(obj, field_name, candidate)
            obj.save(update_fields=[field_name])
            already.add(candidate)
            continue

        # doublons
        if p in already:
            base = p[:8]
            i = 1
            candidate = f"{base}{i:02d}"[:12]
            while candidate in already:
                i += 1
                candidate = f"{base}{i:02d}"[:12]
            setattr(obj, field_name, candidate)
            obj.save(update_fields=[field_name])
            already.add(candidate)
            continue

        already.add(p)


class Command(BaseCommand):
    help = "Seed purchasing: Achats + Dons (+ lignes)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Supprime les données purchasing avant reseed.")
        parser.add_argument("--scale", choices=["small", "medium", "large"], default="medium")
        parser.add_argument("--year", type=int, default=timezone.now().year)

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(42)

        year = options["year"]
        scale = options["scale"]
        reset = options["reset"]

        self.stdout.write(self.style.MIGRATE_HEADING(f"SEED_PURCHASING (year={year}, scale={scale}, reset={reset})"))

        # models
        Fournisseur = apps.get_model("core", "Fournisseur")
        Donateur = apps.get_model("core", "Donateur")
        Depot = apps.get_model("core", "Depot")

        Matiere = apps.get_model("catalog", "Matiere")

        Achat = apps.get_model("purchasing", "Achat")
        LigneAchat = apps.get_model("purchasing", "LigneAchat")
        Don = apps.get_model("purchasing", "Don")
        LigneDon = apps.get_model("purchasing", "LigneDon")

        # IMPORTANT : séquences fournisseur (sinon collisions si prefixes identiques)
        FournisseurSequence = apps.get_model("core", "FournisseurSequence")

        if reset:
            self.stdout.write(self.style.WARNING("RESET purchasing..."))
            LigneAchat.objects.all().delete()
            Achat.objects.all().delete()
            LigneDon.objects.all().delete()
            Don.objects.all().delete()
            # Optionnel mais conseillé: reset des séquences ACH/RET sur l'année
            FournisseurSequence.objects.filter(annee=year).delete()

        # prerequisites
        fournisseurs = list(Fournisseur.objects.all())
        donateurs = list(Donateur.objects.all())
        depots = list(Depot.objects.filter(type_lieu=getattr(Depot.TypeLieu, "DEPOT", "DEPOT")))
        matieres = list(Matiere.objects.filter(actif=True))

        if not fournisseurs:
            raise RuntimeError("Aucun fournisseur trouvé. Lance d'abord: python manage.py seed_core")
        if not donateurs:
            raise RuntimeError("Aucun donateur trouvé. Lance d'abord: python manage.py seed_core")
        if not depots:
            raise RuntimeError("Aucun dépôt trouvé. Lance d'abord: python manage.py seed_core")
        if not matieres:
            raise RuntimeError("Aucune matière trouvée. Lance d'abord: python manage.py seed_catalog")

        # 1) Forcer code_prefix unique pour fournisseurs ET donateurs (évite collisions)
        _ensure_unique_prefix_for_queryset(fournisseurs, field_name="code_prefix", fallback="FOU")
        self.stdout.write(self.style.SUCCESS(f"Fournisseurs: {len(fournisseurs)} code_prefix auto-complétés/uniques."))

        _ensure_unique_prefix_for_queryset(donateurs, field_name="code_prefix", fallback="DON")
        self.stdout.write(self.style.SUCCESS(f"Donateurs: {len(donateurs)} code_prefix auto-complétés/uniques."))

        # 2) Seed achats + lignes
        self._seed_achats(Achat, LigneAchat, year, scale, fournisseurs, depots, matieres)

        # 3) Seed dons + lignes
        self._seed_dons(Don, LigneDon, year, scale, donateurs, depots, matieres)

        self.stdout.write(self.style.SUCCESS("✅ SEED_PURCHASING terminé."))

    def _seed_achats(self, Achat, LigneAchat, year, scale, fournisseurs, depots, matieres):
        if scale == "small":
            n_achats = 30
            lignes_minmax = (1, 4)
        elif scale == "large":
            n_achats = 350
            lignes_minmax = (3, 10)
        else:
            n_achats = 140
            lignes_minmax = (2, 8)

        achats = []
        for i in range(n_achats):
            f = random.choice(fournisseurs)
            d = random.choice(depots)
            dt = rand_date_in_year(year)

            a = Achat(
                fournisseur=f,
                date_achat=dt,
                numero_facture=f"FAC-{year}-{i+1:05d}",
                depot=d,
                commentaire="Achat seed",
                tva_active=pick_weighted([(True, 0.35), (False, 0.65)]),
            )
            # ⚠️ ne jamais toucher a.code ici
            a.save()
            achats.append(a)

            nb_lignes = random.randint(*lignes_minmax)
            used = set()
            for _ in range(nb_lignes):
                m = random.choice(matieres)
                if m.id in used:
                    continue
                used.add(m.id)

                qte = Decimal(random.randint(1, 60))
                pu = (Decimal(random.randint(100, 500000)) / Decimal("1.0")).quantize(Decimal("0.000001"))

                la = LigneAchat(
                    achat=a,
                    matiere=m,
                    quantite=qte,
                    prix_unitaire=pu,
                    appreciation="",
                )
                la.save()

            # Recalcul totaux (le modèle le fait déjà dans save(), mais on verrouille)
            a.recompute_totaux()
            a.save(update_fields=["total_ht", "total_tva", "total_ttc", "code"])

        self.stdout.write(self.style.SUCCESS(f"Achats: {len(achats)} (+ lignes)"))

    def _seed_dons(self, Don, LigneDon, year, scale, donateurs, depots, matieres):
        if scale == "small":
            n_dons = 20
            lignes_minmax = (1, 3)
        elif scale == "large":
            n_dons = 200
            lignes_minmax = (2, 8)
        else:
            n_dons = 90
            lignes_minmax = (1, 6)

        dons = []
        for i in range(n_dons):
            donateur = random.choice(donateurs)
            depot = random.choice(depots)
            dt = rand_date_in_year(year)

            d = Don(
                donateur=donateur,
                date_don=dt,
                depot=depot,
                numero_piece=f"PV-{year}-{i+1:05d}",
                commentaire="Don seed",
            )
            d.save()
            dons.append(d)

            nb_lignes = random.randint(*lignes_minmax)
            used = set()
            for _ in range(nb_lignes):
                m = random.choice(matieres)
                if m.id in used:
                    continue
                used.add(m.id)

                qte = Decimal(random.randint(1, 50))
                pu = (Decimal(random.randint(0, 300000)) / Decimal("1.0")).quantize(Decimal("0.000001"))

                ld = LigneDon(
                    don=d,
                    matiere=m,
                    quantite=qte,
                    prix_unitaire=pu,
                    observation="",
                )
                ld.save()

            d.recompute_totaux()
            d.save(update_fields=["total_valeur", "code"])

        self.stdout.write(self.style.SUCCESS(f"Dons: {len(dons)} (+ lignes)"))
