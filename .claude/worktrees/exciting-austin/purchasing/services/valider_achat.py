# purchasing/services/valider_achat.py
#
# Ce fichier est intentionnellement vide.
#
# L'ancienne logique de validation (champs est_valide, etat, depot_reception_id)
# a été supprimée car elle référençait des champs qui n'existent plus dans le
# modèle Achat. La génération du code pièce est désormais gérée dans
# Achat.save() via core.models.FournisseurSequence.generate_code().
#
# Si une logique de validation explicite (statut brouillon → validé) est
# réintroduite, réécrire ce service depuis zéro en suivant les standards
# définis dans CLAUDE.md (section 5 — Services).
