# audit/middleware.py
"""
Middleware d'audit.

Stocke la requête HTTP courante dans un thread-local afin que les signaux
Django (pre_save / post_save / post_delete) puissent retrouver l'utilisateur
connecté et son adresse IP sans avoir à les propager manuellement à travers
toute la chaîne d'appel.

Ajout dans settings :
    MIDDLEWARE = [
        ...
        'audit.middleware.AuditMiddleware',
    ]
"""
import threading
import logging

logger = logging.getLogger(__name__)

_local = threading.local()


class AuditMiddleware:
    """
    Insère la requête courante dans le thread-local à chaque appel HTTP,
    puis la retire proprement après la réponse (y compris en cas d'exception).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.request = request
        try:
            response = self.get_response(request)
        finally:
            # Nettoyage impératif : évite les fuites de contexte entre
            # requêtes réutilisant le même thread (serveurs comme gunicorn).
            _local.request = None
        return response


def get_current_request():
    """
    Retourne la requête HTTP du thread courant, ou None si hors contexte HTTP
    (commande management, tâche Celery, tests sans client, etc.).
    """
    return getattr(_local, 'request', None)


def get_client_ip(request=None):
    """
    Extrait l'IP réelle du client, en tenant compte des proxies inverses
    (en-tête X-Forwarded-For). Utilise la requête courante si non fournie.
    """
    if request is None:
        request = get_current_request()
    if request is None:
        return None
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        # Prend la première IP de la chaîne (IP du client original)
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
