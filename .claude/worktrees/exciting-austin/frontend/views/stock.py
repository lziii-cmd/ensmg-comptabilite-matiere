# frontend/views/stock.py
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from .base import FrontendView


class MouvementsListView(FrontendView):
    template_name = 'v2/mouvements/list.html'
    active_page = 'mouvements'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from inventory.models import MouvementStock
            qs = MouvementStock.objects.select_related(
                'matiere', 'depot', 'exercice'
            ).order_by('-date')
            paginator = Paginator(qs, 20)
            page_obj = paginator.get_page(self.request.GET.get('page', 1))
            ctx['page_obj'] = page_obj
            ctx['mouvements'] = page_obj.object_list
        except Exception:
            ctx['mouvements'] = []
        return ctx


class MouvementDetailView(FrontendView):
    template_name = 'v2/mouvements/detail.html'
    active_page = 'mouvements'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from inventory.models import MouvementStock
            mvt = get_object_or_404(MouvementStock, pk=self.kwargs['pk'])
            ctx['mouvement'] = mvt
        except Exception:
            pass
        return ctx


class StockCourantListView(FrontendView):
    template_name = 'v2/stock/courant.html'
    active_page = 'stock_courant'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from inventory.models import StockCourant
            qs = StockCourant.objects.select_related(
                'matiere', 'depot', 'exercice'
            ).order_by('matiere__code_court')
            paginator = Paginator(qs, 20)
            page_obj = paginator.get_page(self.request.GET.get('page', 1))
            ctx['page_obj'] = page_obj
            ctx['stocks'] = page_obj.object_list
        except Exception:
            ctx['stocks'] = []
        return ctx


class StockActuelListView(FrontendView):
    template_name = 'v2/stock/actuel.html'
    active_page = 'stock_actuel'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from inventory.models import StockCourant
            from django.db.models import Sum
            # Consolider par matière
            stocks = StockCourant.objects.values(
                'matiere__id', 'matiere__code_court', 'matiere__designation',
                'matiere__type_matiere', 'exercice__code', 'matiere__seuil_min'
            ).annotate(
                qty_totale=Sum('quantite'),
                valeur_totale=Sum('quantite')  # simplifié
            ).order_by('matiere__code_court')
            ctx['stocks'] = stocks
        except Exception:
            ctx['stocks'] = []
        return ctx


class SortiesStockListView(FrontendView):
    template_name = 'v2/stock/sorties.html'
    active_page = 'sorties_stock'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from inventory.models import OperationSortie
            qs = OperationSortie.objects.select_related('depot').order_by('-date_sortie')
            paginator = Paginator(qs, 20)
            page_obj = paginator.get_page(self.request.GET.get('page', 1))
            ctx['page_obj'] = page_obj
            ctx['sorties'] = page_obj.object_list
        except Exception:
            ctx['sorties'] = []
        return ctx


class TransfertsListView(FrontendView):
    template_name = 'v2/stock/transferts.html'
    active_page = 'transferts'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from inventory.models import OperationTransfert
            qs = OperationTransfert.objects.select_related(
                'depot_source', 'depot_destination'
            ).order_by('-date_transfert')
            paginator = Paginator(qs, 20)
            page_obj = paginator.get_page(self.request.GET.get('page', 1))
            ctx['page_obj'] = page_obj
            ctx['transferts'] = page_obj.object_list
        except Exception:
            ctx['transferts'] = []
        return ctx


class SortiesDefinitivesListView(FrontendView):
    template_name = 'v2/stock/sorties_definitives.html'
    active_page = 'sorties_definitives'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from inventory.models import OperationSortie
            qs = OperationSortie.objects.select_related('depot').exclude(
                type_sortie='REFORME_DESTRUCTION'
            ).order_by('-date_sortie')
            paginator = Paginator(qs, 20)
            page_obj = paginator.get_page(self.request.GET.get('page', 1))
            ctx['page_obj'] = page_obj
            ctx['sorties'] = page_obj.object_list
        except Exception:
            ctx['sorties'] = []
        return ctx


class ReformeListView(FrontendView):
    template_name = 'v2/stock/reforme.html'
    active_page = 'reforme'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from inventory.models import OperationSortie
            qs = OperationSortie.objects.select_related('depot').filter(
                type_sortie='REFORME_DESTRUCTION'
            ).order_by('-date_sortie')
            paginator = Paginator(qs, 20)
            page_obj = paginator.get_page(self.request.GET.get('page', 1))
            ctx['page_obj'] = page_obj
            ctx['sorties'] = page_obj.object_list
        except Exception:
            ctx['sorties'] = []
        return ctx
