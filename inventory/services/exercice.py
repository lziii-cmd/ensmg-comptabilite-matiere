# inventory/services/exercice.py
from django.utils import timezone
from django.apps import apps

def exercice_courant(date=None):
    """
    Retourne l'exercice en cours à la date donnée (ou à aujourd'hui si None).
    Si aucun exercice ne couvre cette date, renvoie None.
    """
    date = date or timezone.now().date()
    Exercice = apps.get_model("core", "Exercice")
    return (
        Exercice.objects.filter(date_debut__lte=date, date_fin__gte=date)
        .order_by("-date_debut")
        .first()
    )

def exercice_precedent(exercice):
    """
    Retourne l'exercice immédiatement précédent à celui fourni,
    c’est-à-dire celui dont la date_fin < date_debut du courant.
    """
    if not exercice:
        return None
    Exercice = apps.get_model("core", "Exercice")
    return (
        Exercice.objects.filter(date_fin__lt=exercice.date_debut)
        .order_by("-date_fin")
        .first()
    )
