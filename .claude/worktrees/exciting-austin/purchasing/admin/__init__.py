# purchasing/admin/__init__.py
"""
Module d'administration pour l'application 'purchasing'.
Ce fichier centralise les imports des fichiers admin spécialisés :
 - achat_admin.py
 - ligne_achat_inline.py
"""

#from .achat_admin import AchatAdmin
from .achat_admin import *  # noqa

from .ligne_achat_inline import LigneAchatInline

from .don_admin import *    # ✅ ajoute ceci


from .pret_admin import *           # ✅ PretAdmin
from .retour_pret_admin import *    # ✅ RetourPretAdmin
from .retour_admin import *         # ✅ RetourFournisseurAdmin

# ensures admin modules are loaded when Django imports purchasing.admin
from .external_stock_entry_admin import ExternalStockEntryAdmin  # noqa: F401
from .legs_admin import LegsEntryAdmin                           # noqa: F401
from .dotation_admin import DotationAdmin                        # noqa: F401

__all__ = ["AchatAdmin", "LigneAchatInline", "LegsEntryAdmin", "DotationAdmin"]
