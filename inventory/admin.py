# inventory/admin.py
# Passerelle chargée automatiquement par Django.
# Importe tous les sous-modules admin pour les enregistrer.
from django.contrib import admin

from .admin import mouvement_stock_admin as _m1         # noqa: F401
from .admin import stock_initial_admin as _m2           # noqa: F401
from .admin import stock_courant_admin as _m3           # noqa: F401
from .admin import inventaire_admin as _m4              # noqa: F401
from .admin import operation_sortie_admin as _m5        # noqa: F401
from .admin import operation_transfert_admin as _m6     # noqa: F401
