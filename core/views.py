# core/views.py
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.http import HttpRequest, JsonResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from core.utils.exercices import set_selected_exercice_ids
from core.models import Exercice

@staff_member_required
@require_POST
def set_exercices_selection(request: HttpRequest):
    """
    Enregistre en session la sélection multi-exercices (ids[] en POST).
    Répond en JSON si appelé via fetch, sinon redirige vers la page précédente.
    """
    ids = request.POST.getlist("ids[]") or request.POST.getlist("ids")
    if ids is None:
        return HttpResponseBadRequest("Missing ids")
    selected = set_selected_exercice_ids(request, ids)
    labels = list(
        Exercice.objects.filter(id__in=selected)
        .order_by("-annee")
        .values_list("code", flat=True)
    )
    if request.headers.get("X-Requested-With") == "fetch":
        return JsonResponse({"ok": True, "selected": selected, "label": ", ".join(labels)})
    return redirect(request.META.get("HTTP_REFERER", "/admin/"))
