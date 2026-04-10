# Source de vérité des types de pièces
PIECE_TYPES = (
    "ACH",  # Achat
    "ENT",  # Entrée (hors achat)
    "SOR",  # Sortie
    "TRA",  # Transfert
    "AJU",  # Ajustement
    "INV",  # Inventaire (document)
    "MAT",  # Matériel (fiche article)
    "PRJ",  # Projet
    "REF",  # Réforme
    "MNT",  # Maintenance
    # Optionnels si on sépare les “bons” comme entités distinctes
    "BE",   # Bon d'entrée
    "BS",   # Bon de sortie
    "BT",   # Bon de transfert
    "PV",   # Procès-verbal
)

# Pour les champs Django à choices=
PIECE_TYPE_CHOICES = tuple((t, t) for t in PIECE_TYPES)
