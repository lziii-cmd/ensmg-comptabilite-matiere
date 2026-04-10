# frontend/views/prets.py
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from .base import FrontendView


class PretsListView(FrontendView):
    template_name = 'v2/prets/list.html'
    active_page = 'prets'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from purchasing.models import Pret
            q = self.request.GET.get('q', '')
            statut_filter = self.request.GET.get('statut', '')
            qs = Pret.objects.select_related('service', 'depot').order_by('-date_pret')
            if q:
                qs = qs.filter(code__icontains=q) | qs.filter(service__libelle__icontains=q)
            if statut_filter == 'EN_COURS':
                qs = qs.filter(est_clos=False)
            elif statut_filter == 'CLOS':
                qs = qs.filter(est_clos=True)
            paginator = Paginator(qs, 20)
            page_obj = paginator.get_page(self.request.GET.get('page', 1))
            ctx['page_obj'] = page_obj
            ctx['prets'] = page_obj.object_list
            ctx['q'] = q
            ctx['statut_filter'] = statut_filter
        except Exception:
            ctx['prets'] = []
            ctx['q'] = ''
            ctx['statut_filter'] = ''
        return ctx


class PretDetailView(FrontendView):
    template_name = 'v2/prets/detail.html'
    active_page = 'prets'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from purchasing.models import Pret
            pret = get_object_or_404(Pret, pk=self.kwargs['pk'])
            ctx['pret'] = pret
            ctx['lignes'] = pret.lignes.select_related('matiere').all()
            ctx['retours'] = pret.retours.all()
        except Exception:
            pass
        return ctx


class RetourPretDetailView(FrontendView):
    template_name = 'v2/prets/retour_detail.html'
    active_page = 'prets'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from purchasing.models import RetourPret
            retour = get_object_or_404(RetourPret, pk=self.kwargs['pk'])
            ctx['retour'] = retour
            # related_name for LigneRetourPret is 'lignes_retour_pret'
            ctx['lignes'] = retour.lignes_retour_pret.select_related('matiere').all()
        except Exception:
            pass
        return ctx


class RetoursFournisseursListView(FrontendView):
    template_name = 'v2/misc/retours_fournisseurs.html'
    active_page = 'retours_fournisseurs'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['retours'] = []
        return ctx
