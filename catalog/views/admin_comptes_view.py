# catalog/views/admin_comptes_view.py
"""
Vue admin personnalisée : tableau de bord des 3 niveaux de comptes d'imputation.
Accessible via /admin/comptes-imputation/
"""
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.shortcuts import render

from catalog.models import ComptePrincipal, CompteDivisionnaire, SousCompte

PAGE_SIZE = 20


def _paginate(qs, request, param):
    """Retourne (page_obj, paginator) pour un queryset et un paramètre GET."""
    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get(param, 1))
    return page_obj, paginator


@staff_member_required
def comptes_dashboard(request):
    """Page admin : 3 cards cliquables avec pagination pour les comptes d'imputation."""

    # ── Querysets ────────────────────────────────────────────────────────────
    qs_principaux = ComptePrincipal.objects.order_by('code')
    qs_divisionnaires = CompteDivisionnaire.objects.select_related(
        'compte_principal'
    ).order_by('code')
    qs_sous = SousCompte.objects.select_related(
        'compte_divisionnaire__compte_principal'
    ).order_by('code')

    # ── Pagination indépendante par niveau ───────────────────────────────────
    page_principaux,    pag_principaux    = _paginate(qs_principaux,    request, 'p_page')
    page_divisionnaires, pag_divisionnaires = _paginate(qs_divisionnaires, request, 'd_page')
    page_sous,          pag_sous          = _paginate(qs_sous,          request, 's_page')

    context = {
        # Contexte admin complet (sidebar, breadcrumb, thème…)
        **admin.site.each_context(request),
        'title': "Comptes d'imputation",

        # Cards — compteurs globaux
        'nb_principaux':    qs_principaux.count(),
        'nb_divisionnaires': qs_divisionnaires.count(),
        'nb_sous_comptes':  qs_sous.count(),

        # Pages paginées
        'page_principaux':     page_principaux,
        'page_divisionnaires': page_divisionnaires,
        'page_sous':           page_sous,

        # Paramètres GET pour les liens de pagination
        'param_p': 'p_page',
        'param_d': 'd_page',
        'param_s': 's_page',

        # Quel panneau ouvrir par défaut (selon quel param est actif)
        'open_panel': (
            'principal'    if request.GET.get('p_page') else
            'divisionnaire' if request.GET.get('d_page') else
            'sous'         if request.GET.get('s_page') else
            None
        ),
    }
    return render(request, 'admin/catalog/comptes_dashboard.html', context)
