# core/admin/filters.py
# (remplace intégralement ce fichier)
from django.contrib.admin import SimpleListFilter
from django.utils.translation import gettext_lazy as _
from core.models import Exercice
from core.utils.exercices import get_selected_exercice_ids

class ExerciceSelectionFilter(SimpleListFilter):
    """
    Filtre admin multi-exercices :
    - Propose la liste complète des exercices
    - Si aucun paramètre explicite, applique la sélection session (multi)
    - Si un exercice est choisi via le menu admin (paramètre), on garde le comportement standard
    """
    title = _("Exercice")
    parameter_name = "exercice__id__exact"

    def lookups(self, request, model_admin):
        return [(str(e.id), f"{e.code} ({e.statut})") for e in Exercice.objects.order_by("-annee")]

    def queryset(self, request, queryset):
        # Si l'utilisateur a explicitement choisi un exercice via le filtre, Django applique self.value()
        ex_id = self.value()
        if ex_id:
            return queryset.filter(exercice_id=ex_id)
        # Sinon : filtre selon la sélection multi-exercices stockée en session
        ids = get_selected_exercice_ids(request)
        if ids:
            return queryset.filter(exercice_id__in=ids)
        return queryset.none()
