# frontend/views/catalog.py
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from .base import FrontendView


class CategoriesListView(FrontendView):
    template_name = 'v2/categories/list.html'
    active_page = 'categories'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from catalog.models import Categorie
            from django.db.models import Count
            cats = Categorie.objects.annotate(
                nb_matieres=Count('sous_categories__matieres')
            ).order_by('code')
            ctx['categories'] = cats
        except Exception:
            ctx['categories'] = []
        return ctx


class CategorieDetailView(FrontendView):
    template_name = 'v2/categories/detail.html'
    active_page = 'categories'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from catalog.models import Categorie, Matiere
            cat = get_object_or_404(Categorie, pk=self.kwargs['pk'])
            ctx['categorie'] = cat
            matieres_qs = Matiere.objects.filter(
                sous_categorie__categorie=cat
            ).select_related('sous_categorie', 'unite').order_by('code_court')
            ctx['matieres'] = matieres_qs
            # KPIs
            ctx['nb_matieres'] = matieres_qs.count()
            ctx['nb_matieres_actives'] = matieres_qs.filter(actif=True).count()
            ctx['nb_matieres_stockables'] = matieres_qs.filter(est_stocke=True).count()
            try:
                from catalog.models import SousCategorie
                ctx['nb_sous_categories'] = SousCategorie.objects.filter(categorie=cat).count()
            except Exception:
                ctx['nb_sous_categories'] = 0
        except Exception:
            ctx.setdefault('nb_matieres', 0)
            ctx.setdefault('nb_matieres_actives', 0)
            ctx.setdefault('nb_matieres_stockables', 0)
            ctx.setdefault('nb_sous_categories', 0)
        return ctx


class MatieresListView(FrontendView):
    template_name = 'v2/matieres/list.html'
    active_page = 'matieres'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from catalog.models import Matiere
            qs = Matiere.objects.select_related(
                'sous_categorie__categorie', 'unite'
            ).order_by('code_court')
            q = self.request.GET.get('q', '')
            type_m = self.request.GET.get('type', '')
            if q:
                qs = qs.filter(designation__icontains=q) | qs.filter(code_court__icontains=q)
            if type_m:
                qs = qs.filter(type_matiere=type_m)
            paginator = Paginator(qs, self.paginate_by)
            page_obj = paginator.get_page(self.request.GET.get('page', 1))
            ctx['page_obj'] = page_obj
            ctx['matieres'] = page_obj.object_list
            ctx['q'] = q
            ctx['type_filter'] = type_m
        except Exception:
            ctx['matieres'] = []
            ctx['q'] = ''
        return ctx


class MatiereDetailView(FrontendView):
    template_name = 'v2/matieres/detail.html'
    active_page = 'matieres'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            import json
            from django.db.models import Sum
            from catalog.models import Matiere
            matiere = get_object_or_404(Matiere, pk=self.kwargs['pk'])
            ctx['matiere'] = matiere

            # Stock courant
            from inventory.models import StockCourant
            stocks_qs = StockCourant.objects.filter(
                matiere=matiere
            ).select_related('depot', 'exercice').order_by('exercice__code', 'depot__code')
            ctx['stocks'] = stocks_qs

            # Totaux
            # Compute total_valeur via expression since 'valeur' is a model property
            from django.db.models import ExpressionWrapper, F
            from django.db.models import DecimalField as DjDecField
            valeur_expr = ExpressionWrapper(
                F('quantite') * F('cump'),
                output_field=DjDecField(max_digits=20, decimal_places=6)
            )
            totals = stocks_qs.aggregate(
                total_qte=Sum('quantite'),
                total_valeur=Sum(valeur_expr)
            )
            ctx['total_qte'] = totals['total_qte'] or 0
            ctx['total_valeur'] = totals['total_valeur'] or 0

            # CUMP moyen pondéré
            total_q = totals['total_qte'] or 0
            if total_q > 0:
                cump_pondere = sum(
                    (s.cump or 0) * (s.quantite or 0) for s in stocks_qs
                ) / total_q
                ctx['cump_moyen'] = round(cump_pondere, 2)
            else:
                ctx['cump_moyen'] = 0

            # Evolution stock (12 derniers mois via mouvements)
            try:
                from inventory.models import MouvementStock
                from django.utils import timezone
                import datetime
                now = timezone.now()
                mois_labels = []
                mois_data = []
                for i in range(11, -1, -1):
                    m = (now.month - i - 1) % 12 + 1
                    y = now.year - ((now.month - i - 1) // 12)
                    label = ['Jan','Fév','Mar','Avr','Mai','Juin','Juil','Août','Sep','Oct','Nov','Déc'][m-1]
                    mois_labels.append(f"{label} {y}")
                    # Somme des entrées ce mois (MouvementStock: type='ENTREE', date champ DateTimeField)
                    val = MouvementStock.objects.filter(
                        matiere=matiere,
                        date__year=y,
                        date__month=m,
                        type='ENTREE'
                    ).aggregate(s=Sum('quantite'))['s'] or 0
                    mois_data.append(float(val))
                ctx['evolution_labels'] = json.dumps(mois_labels)
                ctx['evolution_data'] = json.dumps(mois_data)
            except Exception:
                ctx['evolution_labels'] = json.dumps([])
                ctx['evolution_data'] = json.dumps([])

            # Prêts actifs pour cette matière
            try:
                from purchasing.models import LignePret
                ctx['prets_actifs'] = LignePret.objects.filter(
                    matiere=matiere,
                    pret__est_clos=False
                ).select_related('pret__service')[:10]
            except Exception:
                ctx['prets_actifs'] = []

        except Exception:
            ctx.setdefault('total_qte', 0)
            ctx.setdefault('total_valeur', 0)
            ctx.setdefault('cump_moyen', 0)
            ctx.setdefault('evolution_data', '[]')
            ctx.setdefault('evolution_labels', '[]')
            ctx.setdefault('prets_actifs', [])
        return ctx


class ComptesListView(FrontendView):
    template_name = 'v2/misc/comptes.html'
    active_page = 'comptes'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from catalog.models import ComptePrincipal, CompteDivisionnaire, SousCompte
            ctx['comptes_principaux'] = ComptePrincipal.objects.filter(actif=True).order_by('code')
            ctx['comptes_divisionnaires'] = CompteDivisionnaire.objects.select_related(
                'compte_principal'
            ).filter(actif=True).order_by('code')
            ctx['sous_comptes'] = SousCompte.objects.select_related(
                'compte_divisionnaire__compte_principal'
            ).filter(actif=True).order_by('code')
            ctx['nb_principaux'] = ctx['comptes_principaux'].count()
            ctx['nb_divisionnaires'] = ctx['comptes_divisionnaires'].count()
            ctx['nb_sous_comptes'] = ctx['sous_comptes'].count()
        except Exception:
            ctx['comptes_principaux'] = []
            ctx['comptes_divisionnaires'] = []
            ctx['sous_comptes'] = []
            ctx['nb_principaux'] = 0
            ctx['nb_divisionnaires'] = 0
            ctx['nb_sous_comptes'] = 0
        return ctx
