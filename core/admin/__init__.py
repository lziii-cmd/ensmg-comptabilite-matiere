# Agrège toutes les déclarations admin modulaires
from .exercice_admin import *
from .sequence_admin import *
from .unite_admin import *
from .depot_admin import *
from .fournisseur_admin import *
from .donateur_admin import *
from .service_admin import *
from .external_source_admin import *
from .notification_admin import *
# audit_admin retiré — l'admin du journal est dans audit/admin/audit_entry_admin.py
from .pending_record_admin import *
from . import user_admin  # noqa: F401 — enregistrement du UserAdmin ENSMG

__all__ = [
    "ExerciceAdmin",
    "SequenceAdmin",
    "UniteAdmin",
    "DepotAdmin",
    "FournisseurAdmin",
    "DonateurAdmin",
    "ServiceAdmin",
    "ExternalSourceAdmin",
    "NotificationAdmin",
    "PendingRecordAdmin",
]
