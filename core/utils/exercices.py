# core/utils/exercices.py
from __future__ import annotations

from typing import Iterable, List
from django.http import HttpRequest
from django.db.models import QuerySet, Q
from core.models import Exercice

# Clef session unique pour mémoriser la sélection
SESSION_KEY = "exercices_selectionnes"


# ──────────────────────────────────────────────────────────────────────
# Sélection en session (lire / écrire) + hygiène d'IDs
# ──────────────────────────────────────────────────────────────────────
def _sanitize_ids(ids: Iterable[int] | Iterable[str]) -> List[int]:
    out: List[int] = []
    for v in ids or []:
        try:
            out.append(int(v))
        except (TypeError, ValueError):
            continue
    existing = set(Exercice.objects.filter(id__in=out).values_list("id", flat=True))
    return [i for i in out if i in existing]


def get_selected_exercice_ids(request: HttpRequest) -> list[int]:
    """
    IDs d'exercices choisis par l’utilisateur (session),
    ou à défaut les exercices actifs (Exercice.courants()).
    """
    ids = request.session.get(SESSION_KEY)
    if ids:
        clean = _sanitize_ids(ids)
        if clean:
            return clean
    return list(Exercice.courants().values_list("id", flat=True))


def set_selected_exercice_ids(request: HttpRequest, ids: Iterable[int] | Iterable[str]) -> list[int]:
    """
    Définit la sélection d'exercices en session et renvoie la liste retenue (nettoyée).
    Si la liste est vide/invalide, bascule sur Exercice.courants().
    """
    clean = _sanitize_ids(ids)
    if not clean:
        clean = list(Exercice.courants().values_list("id", flat=True))
    request.session[SESSION_KEY] = clean
    request.session.modified = True
    return clean


# ──────────────────────────────────────────────────────────────────────
# Filtrages
# ──────────────────────────────────────────────────────────────────────
def filter_qs_by_exercices(qs: QuerySet, request: HttpRequest, field_name: str = "exercice_id") -> QuerySet:
    """
    Filtre un QS sur un champ FK vers Exercice (ex: 'exercice_id' ou 'exercice__id').
    À utiliser pour les modèles qui ont une FK explicite.
    """
    ids = get_selected_exercice_ids(request)
    if not ids:
        return qs.none()
    return qs.filter(**{f"{field_name}__in": ids})


def filter_qs_by_exercices_dates(qs: QuerySet, request: HttpRequest, date_field: str = "date") -> QuerySet:
    """
    Filtre un QS SANS FK exercice, via un champ **date**.
    Construit un OR de fenêtres :
        (date_field ∈ [date_debut, date_fin]) pour chaque exercice sélectionné.
    """
    ids = get_selected_exercice_ids(request)
    if not ids:
        return qs.none()
    exos = list(Exercice.objects.filter(id__in=ids).values("date_debut", "date_fin"))
    if not exos:
        return qs.none()
    q = Q()
    for e in exos:
        q |= Q(**{f"{date_field}__gte": e["date_debut"], f"{date_field}__lte": e["date_fin"]})
    return qs.filter(q)


# ──────────────────────────────────────────────────────────────────────
# Contexte "clos"
# ──────────────────────────────────────────────────────────────────────
def selection_is_closed_only(request: HttpRequest) -> bool:
    """
    True si la sélection existe et que TOUS les exercices sélectionnés sont CLOS.
    Si aucune sélection: False (mode normal).
    """
    ids = get_selected_exercice_ids(request)
    if not ids:
        return False
    statuts = Exercice.objects.filter(id__in=ids).values_list("statut", flat=True)
    # bool(queryset) -> True s'il y a au moins 1 ligne
    return bool(statuts) and all(s == Exercice.Statut.CLOS for s in statuts)


def exercice_for_date(d):
    """
    Renvoie l'exercice couvrant une date (ou None).
    """
    if not d:
        return None
    return (
        Exercice.objects.filter(date_debut__lte=d, date_fin__gte=d)
        .order_by("-date_debut")
        .first()
    )


def get_open_exercices() -> QuerySet:
    """
    Returns all open exercices (statut='OUVERT').
    """
    return Exercice.objects.filter(statut=Exercice.Statut.OUVERT)


def get_selected_exercices(request: HttpRequest) -> QuerySet:
    """
    Returns a queryset of selected exercices (from session or current ones).
    """
    ids = get_selected_exercice_ids(request)
    return Exercice.objects.filter(id__in=ids)
