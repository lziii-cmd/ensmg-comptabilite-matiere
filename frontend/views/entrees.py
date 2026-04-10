# frontend/views/entrees.py
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from .base import FrontendView


class DonsListView(FrontendView):
    template_name = 'v2/dons/list.html'
    active_page = 'dons'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from purchasing.models import Don
            qs = Don.objects.select_related('donateur', 'depot').order_by('-date_don')
            paginator = Paginator(qs, 20)
            page_obj = paginator.get_page(self.request.GET.get('page', 1))
            ctx['page_obj'] = page_obj
            ctx['dons'] = page_obj.object_list
        except Exception:
            ctx['dons'] = []
        return ctx


class DonDetailView(FrontendView):
    template_name = 'v2/dons/detail.html'
    active_page = 'dons'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from purchasing.models import Don
            don = get_object_or_404(Don, pk=self.kwargs['pk'])
            ctx['don'] = don
            ctx['lignes'] = don.lignes.select_related('matiere').all()
        except Exception:
            pass
        return ctx


class LegsListView(FrontendView):
    template_name = 'v2/legs/list.html'
    active_page = 'legs'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from purchasing.models import ExternalStockEntry
            qs = ExternalStockEntry.objects.select_related('depot').filter(
                source_type='LEGS'
            ).order_by('-date_entree')
            paginator = Paginator(qs, 20)
            page_obj = paginator.get_page(self.request.GET.get('page', 1))
            ctx['page_obj'] = page_obj
            ctx['legs'] = page_obj.object_list
        except Exception:
            ctx['legs'] = []
        return ctx


class LegsDetailView(FrontendView):
    template_name = 'v2/legs/detail.html'
    active_page = 'legs'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from purchasing.models import ExternalStockEntry
            leg = get_object_or_404(ExternalStockEntry, pk=self.kwargs['pk'])
            ctx['leg'] = leg
            # related_name on ExternalStockEntryLine is 'lines'
            ctx['lignes'] = leg.lines.select_related('matiere').all()
        except Exception:
            pass
        return ctx


class DotationsListView(FrontendView):
    template_name = 'v2/misc/dotations.html'
    active_page = 'dotations'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from purchasing.models import Dotation
            qs = Dotation.objects.select_related('depot').order_by('-date_dotation')
            paginator = Paginator(qs, 20)
            page_obj = paginator.get_page(self.request.GET.get('page', 1))
            ctx['page_obj'] = page_obj
            ctx['dotations'] = page_obj.object_list
        except Exception:
            ctx['dotations'] = []
        return ctx
