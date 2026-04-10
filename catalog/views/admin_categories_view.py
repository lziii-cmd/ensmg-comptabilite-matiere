# catalog/views/admin_categories_view.py
"""
Vues admin personnalisées : dashboards cards pour Catégories et Sous-catégories.
"""
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from catalog.models import Categorie, SousCategorie


@staff_member_required
def categories_dashboard(request):
    categories = Categorie.objects.prefetch_related('sous_categories').order_by('code')
    context = {
        **admin.site.each_context(request),
        'title': "Catégories",
        'categories': categories,
        'nb_categories': categories.count(),
    }
    return render(request, 'admin/catalog/categories_dashboard.html', context)


@staff_member_required
def sous_categories_dashboard(request):
    sous_cats = SousCategorie.objects.select_related('categorie').order_by('categorie__code', 'code')
    # Grouper par catégorie
    groupes = {}
    for sc in sous_cats:
        cat = sc.categorie
        if cat.pk not in groupes:
            groupes[cat.pk] = {'categorie': cat, 'items': []}
        groupes[cat.pk]['items'].append(sc)

    context = {
        **admin.site.each_context(request),
        'title': "Sous-catégories",
        'groupes': list(groupes.values()),
        'nb_sous_cats': sous_cats.count(),
    }
    return render(request, 'admin/catalog/sous_categories_dashboard.html', context)
