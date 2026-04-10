from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from catalog.models import Matiere
from purchasing.models import Achat

class MatiereDansLignesFilter(admin.SimpleListFilter):
    title = _("Matière (dans les lignes)")
    parameter_name = "matiere_id"

    def lookups(self, request, model_admin):
        # Pour éviter des menus trop longs, on limite à 50 matières les plus utilisées en lignes
        ids = (Achat.objects
               .filter(lignes__isnull=False)
               .values_list("lignes__matiere_id", flat=True)
               .distinct()[:50])
        qs = Matiere.objects.filter(id__in=list(ids)).order_by("designation")
        return [(m.id, m.designation) for m in qs]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(lignes__matiere_id=self.value()).distinct()
        return queryset
