# core/views/exercice_switch.py
from django.views.decorators.http import require_POST
from django.shortcuts import redirect
from django.contrib import messages

@require_POST
def switch_exercice(request):
    """
    Enregistre en session la liste des exercices choisis dans le sélecteur.
    """
    ids = request.POST.getlist("exercices")
    request.session["exercices_selectionnes"] = ids
    messages.success(request, "Contexte exercice mis à jour.")
    return redirect(request.META.get("HTTP_REFERER", "/admin/"))
