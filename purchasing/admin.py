# purchasing/admin.py
# IMPORTANT : ce fichier est chargé automatiquement par Django.
# Il importe tous les sous-modules admin pour les enregistrer auprès de l'interface d'administration.
from django.contrib import admin

from .admin import achat_admin as _achat_admin                          # noqa: F401
from .admin import retour_admin as _retour_admin                        # noqa: F401
from .admin import don_admin as _don_admin                              # noqa: F401
from .admin import pret_admin as _pret_admin                            # noqa: F401
from .admin import retour_pret_admin as _retour_pret_admin              # noqa: F401
from .admin import external_stock_entry_admin as _ext_entry_admin       # noqa: F401
