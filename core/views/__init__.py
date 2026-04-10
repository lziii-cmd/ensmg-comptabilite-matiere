# core/views/__init__.py
from .exercices import set_exercices_selection  # expose la vue au niveau du package
from .notifications import notifications_api  # noqa
__all__ = ["set_exercices_selection", "notifications_api"]