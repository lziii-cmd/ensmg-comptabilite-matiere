# purchasing/admin/ligne_achat_inline.py

from django.contrib import admin
from purchasing.models import LigneAchat

class LigneAchatInline(admin.TabularInline):
    model = LigneAchat
    extra = 1
    fields = ("matiere", "quantite", "prix_unitaire", "total_ligne_ht", "appreciation")
    readonly_fields = ("total_ligne_ht",)
    autocomplete_fields = ("matiere",)

    class Media:
        js = ("purchasing/js/achat_inline.js",)  # calcul instantané + somme pied

