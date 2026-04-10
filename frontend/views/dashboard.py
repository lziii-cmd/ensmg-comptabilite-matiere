# frontend/views/dashboard.py
from django.db.models import Count, Sum
from .base import FrontendView


class DashboardView(FrontendView):
    template_name = 'v2/dashboard.html'
    active_page = 'dashboard'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from core.models import Depot, Fournisseur, Exercice
            from inventory.models import StockCourant
            from catalog.models import Categorie, Matiere

            ctx['nb_fournisseurs'] = Fournisseur.objects.count()
            ctx['nb_depots'] = Depot.objects.count()
            ctx['nb_exercices'] = Exercice.objects.count()
            ctx['nb_lignes_stock'] = StockCourant.objects.count()
            ctx['categories'] = list(
                Categorie.objects.annotate(
                    nb_matieres=Count('sous_categories__matieres')
                ).values('code', 'libelle', 'nb_matieres')[:10]
            )
            ctx['top_matieres'] = list(
                StockCourant.objects.values(
                    'matiere__code_court', 'matiere__designation'
                ).annotate(total_qty=Sum('quantite')).order_by('-total_qty')[:8]
            )
        except Exception:
            ctx['nb_fournisseurs'] = 0
            ctx['nb_depots'] = 0
            ctx['nb_exercices'] = 0
            ctx['nb_lignes_stock'] = 0
            ctx['categories'] = []
            ctx['top_matieres'] = []
        return ctx
