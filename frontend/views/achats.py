# frontend/views/achats.py
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from .base import FrontendView


class AchatsListView(FrontendView):
    template_name = 'v2/achats/list.html'
    active_page = 'achats'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from django.db.models import Sum, Count
            from django.utils import timezone
            from purchasing.models import Achat
            qs = Achat.objects.select_related('fournisseur', 'depot').order_by('-date_achat')
            q = self.request.GET.get('q', '')
            tva_filter = self.request.GET.get('tva', '')
            if q:
                qs = qs.filter(
                    fournisseur__raison_sociale__icontains=q
                ) | qs.filter(code__icontains=q)
            if tva_filter:
                qs = qs.filter(tva_active=True)

            # KPIs
            all_qs = Achat.objects.all()
            now = timezone.now()
            ctx['kpi_total'] = all_qs.count()
            ctx['kpi_tva'] = all_qs.filter(tva_active=True).count()
            total_ht = all_qs.aggregate(s=Sum('total_ht'))['s'] or 0
            ctx['kpi_total_ht'] = total_ht
            ctx['kpi_ce_mois'] = all_qs.filter(
                date_achat__year=now.year, date_achat__month=now.month
            ).count()

            paginator = Paginator(qs, self.paginate_by)  # 50 résultats par page (cf. CLAUDE.md §8)
            page = self.request.GET.get('page', 1)
            page_obj = paginator.get_page(page)
            ctx['page_obj'] = page_obj
            ctx['achats'] = page_obj.object_list
            ctx['q'] = q
            ctx['tva_filter'] = tva_filter
        except Exception:
            ctx['achats'] = []
            ctx['kpi_total'] = 0
            ctx['kpi_tva'] = 0
            ctx['kpi_total_ht'] = 0
            ctx['kpi_ce_mois'] = 0
            ctx['q'] = ''
        return ctx


class AchatDetailView(FrontendView):
    template_name = 'v2/achats/detail.html'
    active_page = 'achats'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from purchasing.models import Achat
            achat = get_object_or_404(Achat, pk=self.kwargs['pk'])
            ctx['achat'] = achat
            ctx['lignes'] = achat.lignes.select_related('matiere').all()
        except Exception:
            pass
        return ctx
