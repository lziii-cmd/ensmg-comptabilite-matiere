# core/context_processors.py
from core.models import Exercice


def exercices_context(request):
    """
    Contexte admin :
      - exercices_all : tous les exercices (ouvert/clos) pour l'affichage
      - exercices_label : label informatif
      - exercices_selected_ids : sélection en session (sinon exercices courants par défaut)

    Protégé contre les erreurs si les migrations ne sont pas encore appliquées.
    """
    try:
        actifs = Exercice.courants()
        selected = request.session.get("exercices_selectionnes")
        if not selected:
            selected = list(actifs.values_list("id", flat=True))

        return {
            "exercices_all": Exercice.objects.only("id", "code", "statut", "annee").order_by("-annee"),
            "exercices_label": Exercice.courant_label(),
            "exercices_selected_ids": [str(i) for i in selected],
        }
    except Exception:
        # Table inexistante (migrations non encore appliquées) ou autre erreur DB
        return {
            "exercices_all": [],
            "exercices_label": "",
            "exercices_selected_ids": [],
        }
