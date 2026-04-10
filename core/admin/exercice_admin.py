from django.contrib import admin
from django.utils.html import format_html
from datetime import date


from core.models import Exercice
from core.admin.detail_view_mixin import DetailViewMixin

@admin.register(Exercice)
class ExerciceAdmin(DetailViewMixin, admin.ModelAdmin):
    # 'est_courant' visible dans la liste, pas dans le formulaire
    list_display = ("code", "annee", "date_debut", "date_fin", "statut_badge", "est_courant")
    list_filter = ("statut",)
    search_fields = ("code", "annee")
    ordering = ("-annee",)

    # On masque 'code', 'date_debut', 'date_fin' dans le formulaire
    fields = ("annee", "statut")                 # champs visibles dans le form
    readonly_fields = ()                         # rien en readonly dans le form

    def statut_badge(self, obj):
        color = "#16a34a" if obj.statut == "OUVERT" else "#6b7280"
        return format_html('<span style="padding:2px 6px;border-radius:10px;color:white;background:{};">{}</span>', color, obj.statut)
    statut_badge.short_description = "Statut"

    def est_courant(self, obj):
        if not obj.date_debut or not obj.date_fin:
            return False
        return obj.date_debut <= date.today() <= obj.date_fin
    est_courant.boolean = True
    est_courant.short_description = "Courant ?"

    actions = ["clore_exercices", "ouvrir_exercice"]

    def clore_exercices(self, request, queryset):
        updated = queryset.update(statut="CLOS")
        self.message_user(request, f"{updated} exercice(s) clôturé(s).")
    clore_exercices.short_description = "Clore les exercices sélectionnés"

    def ouvrir_exercice(self, request, queryset):
        updated = 0
        for ex in queryset:
            ex.statut = "OUVERT"
            try:
                ex.save()
                updated += 1
            except Exception as e:
                self.message_user(request, f"Impossible d'ouvrir {ex.code}: {e}", level="error")
        if updated:
            self.message_user(request, f"{updated} exercice(s) ouvert(s).")
    ouvrir_exercice.short_description = "Ouvrir (au plus un) exercice"
