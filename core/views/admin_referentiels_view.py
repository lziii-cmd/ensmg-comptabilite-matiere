# core/views/admin_referentiels_view.py
"""
Vues admin personnalisées pour Services et Dépôts.
Accessibles via /admin/services/ et /admin/depots/
"""
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from core.models import Service, Depot


@staff_member_required
def services_dashboard(request):
    services = Service.objects.order_by('code')
    context = {
        **admin.site.each_context(request),
        'title': "Services",
        'services': services,
        'nb_services': services.count(),
    }
    return render(request, 'admin/core/services_dashboard.html', context)


@staff_member_required
def depots_dashboard(request):
    depots = Depot.objects.select_related('service').order_by('identifiant')
    bureaux = depots.filter(type_lieu='BUREAU')
    magasins = depots.filter(type_lieu='DEPOT')
    context = {
        **admin.site.each_context(request),
        'title': "Dépôts & Bureaux",
        'depots': depots,
        'bureaux': bureaux,
        'magasins': magasins,
        'nb_depots': depots.count(),
    }
    return render(request, 'admin/core/depots_dashboard.html', context)
