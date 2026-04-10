# core/admin/user_admin.py
"""
Surcharge du UserAdmin Django pour y intégrer la vue détail ENSMG
(même pattern que AchatAdmin, DonAdmin, etc.).
"""
import logging

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from core.admin.detail_view_mixin import DetailViewMixin

logger = logging.getLogger(__name__)

# Retirer le UserAdmin par défaut de Django avant d'enregistrer le nôtre
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


class ENSMGUserAdmin(DetailViewMixin, BaseUserAdmin):
    """
    UserAdmin enrichi d'une vue détail read-only.
    Le clic dans la liste → /detail/  (Informations + boutons Modifier / Changer MDP).
    Le formulaire de modification reste accessible via le bouton "Modifier".
    """

    detail_fields_sections = [
        {
            "titre": "Identité",
            "fields": [
                ("Nom d'utilisateur",  "username"),
                ("Prénom",             "first_name"),
                ("Nom de famille",     "last_name"),
                ("Adresse e-mail",     "email"),
            ],
        },
        {
            "titre": "Statut & Permissions",
            "fields": [
                ("Actif",              lambda u: "✅ Oui" if u.is_active   else "❌ Non"),
                ("Staff",              lambda u: "✅ Oui" if u.is_staff    else "❌ Non"),
                ("Super-utilisateur",  lambda u: "✅ Oui" if u.is_superuser else "❌ Non"),
            ],
        },
        {
            "titre": "Dates",
            "fields": [
                ("Dernière connexion", lambda u: u.last_login.strftime("%d/%m/%Y %H:%M") if u.last_login else "—"),
                ("Membre depuis",      lambda u: u.date_joined.strftime("%d/%m/%Y") if u.date_joined else "—"),
            ],
        },
    ]

    list_per_page = 20


admin.site.register(User, ENSMGUserAdmin)
