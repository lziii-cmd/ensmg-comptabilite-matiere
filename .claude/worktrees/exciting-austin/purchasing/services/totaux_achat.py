# purchasing/services/totaux_achat.py
from decimal import Decimal
from purchasing.models import Achat

def recalcule_totaux(achat: Achat) -> Achat:
    total_ht = sum((l.total_ligne_ht for l in achat.lignes.all()), Decimal("0.00"))
    achat.set_totaux(total_ht)
    achat.save(update_fields=["taux_tva", "total_ht", "total_tva", "total_ttc", "updated_at"])
    return achat
