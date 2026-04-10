# purchasing/services/totaux_achat.py
#
# Ce fichier est intentionnellement vide.
#
# L'ancienne fonction recalcule_totaux() appelait achat.set_totaux() et
# référençait des champs (taux_tva, updated_at) qui n'existent plus sur Achat.
# Le recalcul des totaux est désormais géré dans Achat.recompute_totaux()
# appelé directement dans Achat.save().
#
# Ne pas importer ce fichier.
