# core/templatetags/dashboard_tags.py
import json
from datetime import timedelta

from django import template
from django.apps import apps
from django.utils import timezone

register = template.Library()


@register.simple_tag
def get_dashboard_stats():
    """
    Retourne un dictionnaire de statistiques pour le dashboard admin.
    Chaque bloc est protégé par try/except pour ne pas planter si l'app n'est pas migrée.
    Inclut également les données pour les graphiques (JSON).
    """
    stats = {
        'exercice_ouvert': None,
        'nb_exercices': 0,
        'nb_fournisseurs': 0,
        'nb_donateurs': 0,
        'nb_depots': 0,
        'nb_matieres': 0,
        'nb_categories': 0,
        'nb_achats': 0,
        'nb_dons': 0,
        'nb_prets': 0,
        'nb_mouvements': 0,
        'nb_lignes_stock': 0,
        # Données graphiques (JSON sérialisé)
        'chart_matieres_cat_json': '{"labels":[],"values":[]}',
        'chart_activite_json': '{"labels":[],"achats":[],"dons":[]}',
        'chart_mouvements_json': '{"labels":[],"values":[]}',
        'chart_stock_top_json': '{"labels":[],"values":[]}',
    }

    # ── Exercices ───────────────────────────────────────────
    try:
        Exercice = apps.get_model('core', 'Exercice')
        stats['exercice_ouvert'] = Exercice.objects.filter(statut='OUVERT').first()
        stats['nb_exercices'] = Exercice.objects.count()
    except Exception:
        pass

    # ── Référentiels ────────────────────────────────────────
    try:
        Fournisseur = apps.get_model('core', 'Fournisseur')
        Donateur = apps.get_model('core', 'Donateur')
        Depot = apps.get_model('core', 'Depot')
        stats['nb_fournisseurs'] = Fournisseur.objects.count()
        stats['nb_donateurs'] = Donateur.objects.count()
        stats['nb_depots'] = Depot.objects.filter(actif=True).count()
    except Exception:
        pass

    # ── Catalogue ───────────────────────────────────────────
    try:
        from django.db.models import Count as _Count
        Matiere = apps.get_model('catalog', 'Matiere')
        Categorie = apps.get_model('catalog', 'Categorie')
        stats['nb_matieres'] = Matiere.objects.filter(actif=True).count()
        stats['nb_categories'] = Categorie.objects.filter(actif=True).count()

        # Graphique : matières par catégorie (donut)
        # Matiere → sous_categorie → categorie
        cat_data = list(
            Matiere.objects.filter(actif=True)
            .values('sous_categorie__categorie__libelle')
            .annotate(n=_Count('id'))
            .order_by('-n')[:8]
        )
        if cat_data:
            stats['chart_matieres_cat_json'] = json.dumps({
                'labels': [x['sous_categorie__categorie__libelle'] or 'N/A' for x in cat_data],
                'values': [x['n'] for x in cat_data],
            })
    except Exception:
        pass

    # ── Achats / Dons / Prêts ───────────────────────────────
    try:
        from django.db.models import Count as _Count
        from django.db.models.functions import TruncMonth
        Achat = apps.get_model('purchasing', 'Achat')
        Don = apps.get_model('purchasing', 'Don')
        Pret = apps.get_model('purchasing', 'Pret')
        stats['nb_achats'] = Achat.objects.count()
        stats['nb_dons'] = Don.objects.count()
        stats['nb_prets'] = Pret.objects.count()

        # Graphique : activité mensuelle 6 derniers mois (bar chart)
        cutoff = (timezone.now() - timedelta(days=180)).date()
        achats_mois = {
            x['mois'].strftime('%m/%Y'): x['n']
            for x in Achat.objects
            .filter(date_achat__gte=cutoff)
            .annotate(mois=TruncMonth('date_achat'))
            .values('mois')
            .annotate(n=_Count('id'))
        }
        # Construire labels des 6 derniers mois
        labels = []
        for i in range(5, -1, -1):
            d = timezone.now().date().replace(day=1) - timedelta(days=i * 30)
            labels.append(d.strftime('%m/%Y'))
        # Déduplication de la liste labels (month boundaries)
        seen = set()
        unique_labels = []
        for lb in labels:
            if lb not in seen:
                seen.add(lb)
                unique_labels.append(lb)

        # Dons par mois
        try:
            don_date_field = 'date_don'
            Don.objects.values(don_date_field)  # test field
        except Exception:
            don_date_field = None
        dons_mois = {}
        if don_date_field:
            try:
                dons_mois = {
                    x['mois'].strftime('%m/%Y'): x['n']
                    for x in Don.objects
                    .filter(**{f'{don_date_field}__gte': cutoff})
                    .annotate(mois=TruncMonth(don_date_field))
                    .values('mois')
                    .annotate(n=_Count('id'))
                }
            except Exception:
                pass

        stats['chart_activite_json'] = json.dumps({
            'labels': unique_labels,
            'achats': [achats_mois.get(lb, 0) for lb in unique_labels],
            'dons':   [dons_mois.get(lb, 0) for lb in unique_labels],
        })
    except Exception:
        pass

    # ── Inventaire / Stock ──────────────────────────────────
    try:
        from django.db.models import Count as _Count, Sum
        MouvementStock = apps.get_model('inventory', 'MouvementStock')
        StockCourant = apps.get_model('inventory', 'StockCourant')
        stats['nb_mouvements'] = MouvementStock.objects.count()
        stats['nb_lignes_stock'] = StockCourant.objects.count()

        # Graphique : mouvements par type (donut)
        mv_types = list(
            MouvementStock.objects
            .values('type')
            .annotate(n=_Count('id'))
            .order_by('type')
        )
        type_labels = {'ENTREE': 'Entrées', 'SORTIE': 'Sorties', 'AJUSTEMENT': 'Ajustements', 'TRANSFERT': 'Transferts'}
        if mv_types:
            stats['chart_mouvements_json'] = json.dumps({
                'labels': [type_labels.get(x['type'], x['type']) for x in mv_types],
                'values': [x['n'] for x in mv_types],
            })

        # Graphique : top 8 matières par quantité en stock (bar horizontal)
        top_stock = list(
            StockCourant.objects
            .select_related('matiere')
            .order_by('-quantite')[:8]
        )
        if top_stock:
            stats['chart_stock_top_json'] = json.dumps({
                'labels': [str(x.matiere.code_court) if hasattr(x.matiere, 'code_court') else str(x.matiere) for x in top_stock],
                'values': [float(x.quantite) for x in top_stock],
            })
    except Exception:
        pass

    return stats
