# purchasing/admin/retour_admin.py
from django.contrib import admin
from core.admin.mixins import AgentRestrictedMixin
from core.admin.detail_view_mixin import DetailViewMixin
from purchasing.models import RetourFournisseur, LigneRetour

class LigneRetourInline(admin.TabularInline):
    model = LigneRetour
    extra = 1
    fields = ("matiere", "quantite", "ligne_achat_origine")

@admin.register(RetourFournisseur)
class RetourFournisseurAdmin(DetailViewMixin, AgentRestrictedMixin, admin.ModelAdmin):
    inlines = [LigneRetourInline]
    list_display = ("code_or_temp", "fournisseur", "date_retour", "depot")
    list_filter = ("date_retour", "fournisseur")
    search_fields = ("code", "fournisseur__raison_sociale", "fournisseur__code_prefix")
    exclude = ("code",)

    detail_fields_sections = [
        {
            "titre": "Informations du retour",
            "fields": [
                ("Code",          "code"),
                ("Fournisseur",   "fournisseur"),
                ("Date du retour",lambda o: o.date_retour.strftime("%d/%m/%Y") if o.date_retour else "—"),
                ("Dépôt",         "depot"),
            ],
        },
        {
            "titre": "Commentaire",
            "obs_field": "commentaire",
            "fields": [],
        },
    ]
    detail_inline_models = [
        {
            "titre": "Articles retournés",
            "qs": lambda obj: obj.lignes.select_related("matiere").all(),
            "colonnes": [
                {"label": "Désignation",        "accessor": lambda l: l.matiere,                                                          "css": "td-primary"},
                {"label": "Quantité retournée", "accessor": "quantite",                                                                         "css": "td-num center"},
                {"label": "Achat d'origine",    "accessor": lambda l: str(l.ligne_achat_origine) if l.ligne_achat_origine else "Retour global", "css": ""},
            ],
        }
    ]

    def code_or_temp(self, obj):
        return obj.code or "(en génération)"
    code_or_temp.short_description = "Code retour"
